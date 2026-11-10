"""Helpers to invoke plane-specific Alembic operations from tests.

Configs are isolated: sqlalchemy.url is set on the Config object only.
Environment variables are not mutated (avoids cross-test URL pollution).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANT_PLANE_DIR = REPO_ROOT / "migrations" / "tenant_plane"
CONTROL_PLANE_DIR = REPO_ROOT / "migrations" / "control_plane"


def _config(script_location: Path, database_url: str) -> Config:
    ini = script_location / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(script_location))
    # Explicit non-placeholder URL takes precedence in env.py get_url().
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def upgrade_tenant_plane(database_url: str, revision: str = "head") -> None:
    """Run Tenant Plane migrations. Safe from sync contexts only."""
    cfg = _config(TENANT_PLANE_DIR, database_url)
    command.upgrade(cfg, revision)


def ensure_control_plane_version_table(database_url: str) -> None:
    """Initialize CP Alembic version tracking without inventing CP0001 DDL."""
    cfg = _config(CONTROL_PLANE_DIR, database_url)
    command.ensure_version(cfg)


async def upgrade_tenant_plane_async(
    database_url: str, revision: str = "head"
) -> None:
    await asyncio.to_thread(upgrade_tenant_plane, database_url, revision)


async def ensure_control_plane_version_table_async(database_url: str) -> None:
    await asyncio.to_thread(ensure_control_plane_version_table, database_url)
