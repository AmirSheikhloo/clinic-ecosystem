"""Helpers to invoke plane-specific Alembic operations from tests."""

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
    os.environ[env_var] = database_url
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _upgrade(script_location: Path, env_var: str, database_url: str, revision: str) -> None:
    cfg = _config(script_location, database_url, env_var)
    command.upgrade(cfg, revision)


def upgrade_tenant_plane(database_url: str, revision: str = "head") -> None:
    """Run Tenant Plane migrations. Safe from sync contexts only."""
    _upgrade(TENANT_PLANE_DIR, "TENANT_PLANE_DATABASE_URL", database_url, revision)


def ensure_control_plane_version_table(database_url: str) -> None:
    """Initialize CP Alembic version tracking without inventing CP0001 DDL.

    Appendix E.3: a no-op technical baseline revision is optional only if
    required by tooling. Alembic's ``ensure_version`` creates the version
    table without a fabricated migration revision.
    """
    cfg = _config(CONTROL_PLANE_DIR, database_url, "CONTROL_PLANE_DATABASE_URL")
    command.ensure_version(cfg)


async def upgrade_tenant_plane_async(
    database_url: str, revision: str = "head"
) -> None:
    await asyncio.to_thread(upgrade_tenant_plane, database_url, revision)


async def ensure_control_plane_version_table_async(database_url: str) -> None:
    await asyncio.to_thread(ensure_control_plane_version_table, database_url)


# Back-compat alias used by older call sites during remediation.
async def upgrade_control_plane_async(database_url: str, revision: str = "head") -> None:
    del revision  # CP has no business revisions in M0.
    await ensure_control_plane_version_table_async(database_url)
