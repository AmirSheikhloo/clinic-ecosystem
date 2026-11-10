"""Alembic config isolation and fixed migrator role proofs."""

from __future__ import annotations

import os
from urllib.parse import quote_plus

import asyncpg
import pytest

from tests.integration.alembic_runner import (
    ensure_control_plane_version_table,
    ensure_control_plane_version_table_async,
    upgrade_tenant_plane,
    upgrade_tenant_plane_async,
)
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


@pytest.mark.asyncio
async def test_env_var_cannot_override_effective_migration_role(plane_topology) -> None:
    """Poison TENANT_PLANE_SET_ROLE; ownership must remain db_migrator."""
    previous = os.environ.get("TENANT_PLANE_SET_ROLE")
    os.environ["TENANT_PLANE_SET_ROLE"] = "cp_db_migrator"
    try:
        await upgrade_tenant_plane_async(
            plane_topology.cloud_tenant.sqlalchemy_async_url()
        )
    finally:
        if previous is None:
            os.environ.pop("TENANT_PLANE_SET_ROLE", None)
        else:
            os.environ["TENANT_PLANE_SET_ROLE"] = previous

    admin = plane_topology.cloud_admin
    dsn = (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    conn = await asyncpg.connect(dsn)
    try:
        owner = await conn.fetchval(
            """
            SELECT tableowner FROM pg_tables
            WHERE schemaname = 'public' AND tablename = 'tenant_registry'
            """
        )
        assert owner == "db_migrator"
        ver_owner = await conn.fetchval(
            """
            SELECT tableowner FROM pg_tables
            WHERE schemaname = 'alembic_meta' AND tablename = 'alembic_version_tp'
            """
        )
        assert ver_owner == "db_migrator"
    finally:
        await conn.close()


def test_plane_configs_do_not_reuse_another_database_url(plane_topology) -> None:
    """Each Config carries its own sqlalchemy.url; env is not used as shared state."""
    poisoned = "postgresql+asyncpg://should-not-be-used:x@127.0.0.1:1/nope"
    previous_tp = os.environ.get("TENANT_PLANE_DATABASE_URL")
    previous_cp = os.environ.get("CONTROL_PLANE_DATABASE_URL")
    os.environ["TENANT_PLANE_DATABASE_URL"] = poisoned
    os.environ["CONTROL_PLANE_DATABASE_URL"] = poisoned
    try:
        # Explicit Config URLs must win over poisoned env fallbacks.
        upgrade_tenant_plane(plane_topology.cloud_tenant.sqlalchemy_async_url())
        upgrade_tenant_plane(plane_topology.local_hub.sqlalchemy_async_url())
        ensure_control_plane_version_table(
            plane_topology.cloud_control.sqlalchemy_async_url()
        )
    finally:
        if previous_tp is None:
            os.environ.pop("TENANT_PLANE_DATABASE_URL", None)
        else:
            os.environ["TENANT_PLANE_DATABASE_URL"] = previous_tp
        if previous_cp is None:
            os.environ.pop("CONTROL_PLANE_DATABASE_URL", None)
        else:
            os.environ["CONTROL_PLANE_DATABASE_URL"] = previous_cp


@pytest.mark.asyncio
async def test_bootstrap_alembic_meta_idempotent(plane_topology) -> None:
    """Re-applying schema privilege SQL keeps alembic_meta owner and denials."""
    from tests.integration.conftest import (
        CONTROL_SCHEMA_PRIVS_SQL,
        TENANT_SCHEMA_PRIVS_SQL,
        _apply_db_script,
    )

    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )
    # Second bootstrap pass (idempotent)
    await _apply_db_script(plane_topology.cloud_admin, "tenant_app", TENANT_SCHEMA_PRIVS_SQL)
    await _apply_db_script(
        plane_topology.cloud_admin, "control_plane", CONTROL_SCHEMA_PRIVS_SQL
    )

    admin = plane_topology.cloud_admin
    for database, owner, runtime in (
        ("tenant_app", "db_migrator", "db_app_runtime"),
        ("control_plane", "cp_db_migrator", "cp_db_app_runtime"),
    ):
        dsn = (
            f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
            f"@{admin.host}:{admin.port}/{database}"
        )
        conn = await asyncpg.connect(dsn)
        try:
            schema_owner = await conn.fetchval(
                """
                SELECT r.rolname FROM pg_namespace n
                JOIN pg_roles r ON r.oid = n.nspowner
                WHERE n.nspname = 'alembic_meta'
                """
            )
            assert schema_owner == owner
            assert not await conn.fetchval(
                "SELECT has_schema_privilege($1, 'alembic_meta', 'USAGE')",
                runtime,
            )
            # Existing version rows must remain for TP after re-bootstrap
            if database == "tenant_app":
                version = await conn.fetchval(
                    "SELECT version_num FROM alembic_meta.alembic_version_tp"
                )
                assert version == "tp0001"
        finally:
            await conn.close()
