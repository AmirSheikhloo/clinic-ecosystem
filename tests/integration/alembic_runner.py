"""Helpers to invoke plane-specific Alembic upgrades from tests."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANT_PLANE_DIR = REPO_ROOT / "migrations" / "tenant_plane"
CONTROL_PLANE_DIR = REPO_ROOT / "migrations" / "control_plane"


def _config(script_location: Path, database_url: str, env_var: str) -> Config:
    ini = script_location / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(script_location))
    # env.py prefers the environment variable; set both for clarity.
    os.environ[env_var] = database_url
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _upgrade(script_location: Path, env_var: str, database_url: str, revision: str) -> None:
    cfg = _config(script_location, database_url, env_var)
    command.upgrade(cfg, revision)


def upgrade_tenant_plane(database_url: str, revision: str = "head") -> None:
    """Run Tenant Plane migrations. Safe from sync contexts only.

    Prefer :func:`upgrade_tenant_plane_async` from async pytest tests so
    Alembic's ``asyncio.run`` does not nest inside a running event loop.
    """
    _upgrade(TENANT_PLANE_DIR, "TENANT_PLANE_DATABASE_URL", database_url, revision)


def upgrade_control_plane(database_url: str, revision: str = "head") -> None:
    """Run Control Plane migrations. Safe from sync contexts only."""
    _upgrade(CONTROL_PLANE_DIR, "CONTROL_PLANE_DATABASE_URL", database_url, revision)


async def upgrade_tenant_plane_async(
    database_url: str, revision: str = "head"
) -> None:
    await asyncio.to_thread(upgrade_tenant_plane, database_url, revision)


async def upgrade_control_plane_async(
    database_url: str, revision: str = "head"
) -> None:
    await asyncio.to_thread(upgrade_control_plane, database_url, revision)
