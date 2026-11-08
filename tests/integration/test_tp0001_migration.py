"""TP0001 migration acceptance tests (v3.0.1 Appendix F.2 / Gate A M0-C)."""

from __future__ import annotations

import asyncpg
import pytest

from tests.integration.alembic_runner import (
    upgrade_control_plane,
    upgrade_tenant_plane,
)
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]

EXPECTED_COLUMNS = {
    "tenant_id",
    "tenant_status",
    "timezone_name",
    "created_at_utc",
    "updated_at_utc",
}


async def _table_columns(conn: asyncpg.Connection, table: str) -> dict[str, dict]:
    rows = await conn.fetch(
        """
        SELECT column_name, data_type, udt_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
        """,
        table,
    )
    return {r["column_name"]: dict(r) for r in rows}


async def _public_tables(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        """
    )
    return {r["tablename"] for r in rows}


@pytest.mark.asyncio
async def test_tp0001_applies_to_cloud_tenant_and_local_hub(plane_topology) -> None:
    upgrade_tenant_plane(plane_topology.cloud_tenant.sqlalchemy_async_url())
    upgrade_tenant_plane(plane_topology.local_hub.sqlalchemy_async_url())

    for endpoint in (plane_topology.cloud_tenant, plane_topology.local_hub):
        # Connect as admin on the same cluster to inspect schema broadly
        admin = (
            plane_topology.cloud_admin
            if endpoint.database == "tenant_app"
            else plane_topology.local_admin
        )
        dsn = (
            f"postgresql://{admin.user}:{admin.password}"
            f"@{admin.host}:{admin.port}/{endpoint.database}"
        )
        conn = await asyncpg.connect(dsn)
        try:
            # btree_gist installed
            ext = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'"
            )
            assert ext == 1

            cols = await _table_columns(conn, "tenant_registry")
            assert set(cols) == EXPECTED_COLUMNS

            assert cols["tenant_id"]["udt_name"] == "uuid"
            assert cols["tenant_id"]["is_nullable"] == "NO"
            assert cols["tenant_id"]["column_default"] is None

            assert cols["tenant_status"]["udt_name"] == "varchar"
            assert cols["timezone_name"]["udt_name"] == "text"
            assert cols["created_at_utc"]["udt_name"] == "timestamptz"
            assert cols["updated_at_utc"]["udt_name"] == "timestamptz"

            # status CHECK constraint present
            check = await conn.fetchval(
                """
                SELECT pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = 'tenant_registry' AND c.contype = 'c'
                """
            )
            assert check is not None
            assert "ACTIVE" in check
            assert "SUSPENDED" in check
            assert "DELETING" in check
            assert "DELETED" in check

            # No extra application tables from F.2 beyond tenant_registry
            tables = await _public_tables(conn)
            app_tables = tables - {"alembic_version_tp"}
            assert app_tables == {"tenant_registry"}

            version = await conn.fetchval(
                "SELECT version_num FROM alembic_version_tp"
            )
            assert version == "tp0001"
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_tp0001_rejects_invalid_status(plane_topology) -> None:
    # Ensure migration applied (idempotent for already-migrated DBs in session)
    upgrade_tenant_plane(plane_topology.cloud_tenant.sqlalchemy_async_url())
    admin = plane_topology.cloud_admin
    dsn = (
        f"postgresql://{admin.user}:{admin.password}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    conn = await asyncpg.connect(dsn)
    try:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO tenant_registry (
                    tenant_id, tenant_status, timezone_name,
                    created_at_utc, updated_at_utc
                ) VALUES (
                    '01900000-0000-7000-8000-000000000001',
                    'INVALID',
                    'UTC',
                    NOW(),
                    NOW()
                )
                """
            )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_tp0001_does_not_mutate_control_plane_db(plane_topology) -> None:
    upgrade_control_plane(plane_topology.cloud_control.sqlalchemy_async_url())
    upgrade_tenant_plane(plane_topology.cloud_tenant.sqlalchemy_async_url())

    admin = plane_topology.cloud_admin
    cp_dsn = (
        f"postgresql://{admin.user}:{admin.password}"
        f"@{admin.host}:{admin.port}/control_plane"
    )
    conn = await asyncpg.connect(cp_dsn)
    try:
        tables = await _public_tables(conn)
        assert "tenant_registry" not in tables
        assert "alembic_version_tp" not in tables
        assert "alembic_version_cp" in tables
        # No invented CP business tables
        assert tables == {"alembic_version_cp"}
        version = await conn.fetchval("SELECT version_num FROM alembic_version_cp")
        assert version == "cp0000"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_separate_alembic_version_tables(plane_topology) -> None:
    upgrade_control_plane(plane_topology.cloud_control.sqlalchemy_async_url())
    upgrade_tenant_plane(plane_topology.cloud_tenant.sqlalchemy_async_url())

    admin = plane_topology.cloud_admin
    for db_name, expected_table, unexpected in (
        ("control_plane", "alembic_version_cp", "alembic_version_tp"),
        ("tenant_app", "alembic_version_tp", "alembic_version_cp"),
    ):
        dsn = (
            f"postgresql://{admin.user}:{admin.password}"
            f"@{admin.host}:{admin.port}/{db_name}"
        )
        conn = await asyncpg.connect(dsn)
        try:
            tables = await _public_tables(conn)
            assert expected_table in tables
            assert unexpected not in tables
        finally:
            await conn.close()
