"""Experiment-local Alembic env — synthetic namespace only.

Does NOT import or modify migrations/tenant_plane/env.py.
Version table: public.exp_f2b_alembic_version (not alembic_meta.alembic_version_tp).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
VERSION_TABLE = "exp_f2b_alembic_version"


def get_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("driver://"):
        url = os.environ.get("EXP_F2B_DATABASE_URL", "")
    if not url or url.startswith("driver://"):
        raise RuntimeError("EXP_F2B_DATABASE_URL / sqlalchemy.url required")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        # Prefer experiment migrator when role exists.
        try:
            connection.execute(text("SET ROLE exp_f2b_migrator"))
            connection.commit()
        except Exception:
            connection.rollback()
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
