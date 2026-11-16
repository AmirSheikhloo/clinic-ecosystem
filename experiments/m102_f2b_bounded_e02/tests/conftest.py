"""Experiment-local pytest fixtures — disposable PG15 only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP_ROOT))

from harness.bootstrap import (  # noqa: E402
    admin_dsn_from_env,
    bootstrap_roles_and_rls,
    migrator_url,
    require_pg15,
)


@pytest.fixture(scope="session")
def pg_proof() -> str:
    dsn = admin_dsn_from_env()
    return require_pg15(dsn)


@pytest.fixture(scope="session")
def admin_dsn(pg_proof: str) -> str:
    _ = pg_proof
    dsn = admin_dsn_from_env()
    bootstrap_roles_and_rls(dsn)
    return dsn


@pytest.fixture(scope="session")
def db_url(admin_dsn: str) -> str:
    _ = admin_dsn
    url = migrator_url()
    os.environ["EXP_F2B_DATABASE_URL"] = url
    return url
