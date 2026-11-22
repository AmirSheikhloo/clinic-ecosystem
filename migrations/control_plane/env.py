"""Control Plane Alembic environment (asyncpg).

Initialized for version tracking only in M0 — no CP0001 business DDL.
Version table alembic_version_cp lives in private schema alembic_meta.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
VERSION_TABLE = "alembic_version_cp"
VERSION_TABLE_SCHEMA = "alembic_meta"
MIGRATOR_ROLE = "cp_db_migrator"


def _is_placeholder_url(url: str | None) -> bool:
    return not url or url.startswith("driver://")


def get_url() -> str:
    """Prefer an explicitly configured non-placeholder sqlalchemy.url."""
    ini_url = config.get_main_option("sqlalchemy.url")
    if not _is_placeholder_url(ini_url):
        url = ini_url
    else:
        url = os.environ.get("CONTROL_PLANE_DATABASE_URL")
    if _is_placeholder_url(url):
        raise RuntimeError(
            "Configure sqlalchemy.url or CONTROL_PLANE_DATABASE_URL to a "
            "PostgreSQL URL (postgresql+asyncpg://...)."
        )
    assert url is not None
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        version_table_schema=VERSION_TABLE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        version_table_schema=VERSION_TABLE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            role_set = False
            primary_error: BaseException | None = None
            try:
                await connection.execute(text(f'SET ROLE "{MIGRATOR_ROLE}"'))
                role_set = True
                await connection.run_sync(do_run_migrations)
                await connection.commit()
            except BaseException as exc:
                primary_error = exc
                raise
            finally:
                try:
                    # First clear SQLSTATE 25P02 on the SAME connection.
                    await connection.rollback()
                    if role_set:
                        await connection.execute(text("RESET ROLE"))
                        await connection.commit()
                except Exception:
                    if primary_error is None:
                        # Cleanup failure on an otherwise successful migration
                        # must abort and never be represented as success.
                        raise
                    import logging
                    logging.getLogger(__name__).exception(
                        "migrator connection cleanup failed after primary error"
                    )
                    # Preserve the original migration/permission exception.
                    # NullPool discards this connection on context exit.
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
