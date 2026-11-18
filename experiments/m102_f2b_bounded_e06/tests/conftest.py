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
    bootstrap_roles,
    dsn_for_db,
    ensure_databases,
    migrator_url,
    require_pg15,
)


@pytest.fixture(scope="session")
def pg_proof() -> dict:
    dsn = admin_dsn_from_env()
    ensure_databases(dsn)
    proof = require_pg15(dsn)
    bootstrap_roles(dsn)
    # also bootstrap roles on sibling DBs
    for name in ("exp_e03", "exp_e03_cloud", "exp_e03_local"):
        bootstrap_roles(dsn_for_db(dsn, name))
    return proof


@pytest.fixture(scope="session")
def admin_dsn(pg_proof: dict) -> str:
    _ = pg_proof
    return dsn_for_db(admin_dsn_from_env(), "exp_e03")


@pytest.fixture(scope="session")
def db_url(admin_dsn: str) -> str:
    url = migrator_url(admin_dsn)
    os.environ["EXP_E06_DATABASE_URL"] = url
    return url


@pytest.fixture(scope="session")
def cloud_admin(pg_proof: dict) -> str:
    _ = pg_proof
    return dsn_for_db(admin_dsn_from_env(), "exp_e03_cloud")


@pytest.fixture(scope="session")
def local_admin(pg_proof: dict) -> str:
    _ = pg_proof
    return dsn_for_db(admin_dsn_from_env(), "exp_e03_local")
