"""Helpers to invoke plane-specific Alembic upgrades from tests."""

from __future__ import annotations

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


def upgrade_tenant_plane(database_url: str, revision: str = "head") -> None:
    cfg = _config(TENANT_PLANE_DIR, database_url, "TENANT_PLANE_DATABASE_URL")
    command.upgrade(cfg, revision)


def upgrade_control_plane(database_url: str, revision: str = "head") -> None:
    cfg = _config(CONTROL_PLANE_DIR, database_url, "CONTROL_PLANE_DATABASE_URL")
    command.upgrade(cfg, revision)
