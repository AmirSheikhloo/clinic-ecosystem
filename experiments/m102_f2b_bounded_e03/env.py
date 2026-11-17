"""E0.3 experiment Alembic env — fail-closed SET ROLE (A01 corrective).

Does NOT import or modify migrations/tenant_plane/env.py.
Version table: public.exp_e03_alembic_version.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = None
VERSION_TABLE = "exp_e03_alembic_version"
REQUIRED_ROLE = "exp_e03_migrator"


def get_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("driver://"):
        url = os.environ.get("EXP_E03_DATABASE_URL", "")
    if not url or url.startswith("driver://"):
        raise RuntimeError("EXP_E03_DATABASE_URL / sqlalchemy.url required")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _assert_restricted_migrator(connection) -> dict:
    """Fail closed: no DDL/stamp without exact restricted role identity."""
    row = connection.execute(
        text(
            """
            SELECT current_user, session_user,
                   EXISTS (
                     SELECT 1 FROM pg_roles
                     WHERE rolname = current_user AND rolsuper
                   ) AS is_super,
                   EXISTS (
                     SELECT 1 FROM pg_roles
                     WHERE rolname = current_user AND rolbypassrls
                   ) AS bypass_rls
            """
        )
    ).mappings().one()
    info = dict(row)
    if info["current_user"] != REQUIRED_ROLE:
        raise RuntimeError(
            f"STOP_SECURITY: current_user={info['current_user']!r} "
            f"!= required {REQUIRED_ROLE!r}; refusing DDL/stamp"
        )
    if info["is_super"] or info["bypass_rls"]:
        raise RuntimeError(
            f"STOP_SECURITY: privileged migrator identity {info}; refusing DDL/stamp"
        )
    return info


def run_migrations_offline() -> None:
    raise RuntimeError("E0.3 offline migrations are not authorized")


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        # Fail-closed SET ROLE — no catch-and-continue (A01).
        try:
            connection.execute(text(f"SET ROLE {REQUIRED_ROLE}"))
            connection.commit()
        except Exception as exc:
            connection.rollback()
            raise RuntimeError(
                f"STOP_SECURITY: SET ROLE {REQUIRED_ROLE} failed; "
                f"no fallback to privileged identity: {exc}"
            ) from exc
        _assert_restricted_migrator(connection)
        context.configure(
            connection=connection,
            version_table=VERSION_TABLE,
            version_table_schema="public",
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
