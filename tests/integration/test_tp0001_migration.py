"""TP0001 migration acceptance tests (v3.0.1 Appendix F.2 / E.2 / Gate A M0-C).

Migrations run as actual tp_migrator_login / local_migrator_login identities
(assuming only db_migrator). Admin connections are used for inspection only.
Alembic version tables live in schema alembic_meta.
"""

from __future__ import annotations

from urllib.parse import quote_plus

import asyncpg
import pytest

from tests.integration.alembic_runner import (
    ensure_control_plane_version_table_async,
    upgrade_tenant_plane_async,
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
ALEMBIC_META = "alembic_meta"


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


async def _admin_db_dsn(plane_topology, *, cloud: bool, database: str) -> str:
    admin = plane_topology.cloud_admin if cloud else plane_topology.local_admin
    return (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/{database}"
    )


async def _assert_postgres_15(conn: asyncpg.Connection) -> None:
    version = await conn.fetchval("SHOW server_version")
    assert version is not None
    assert str(version).startswith("15."), f"expected PostgreSQL 15.x, got {version!r}"


@pytest.mark.asyncio
async def test_tp0001_applies_to_cloud_tenant_and_local_hub(plane_topology) -> None:
    assert plane_topology.cloud_tenant.user == "tp_migrator_login"
    assert plane_topology.local_hub.user == "local_migrator_login"

    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())

    for cloud, database in ((True, "tenant_app"), (False, "local_hub")):
        conn = await asyncpg.connect(
            await _admin_db_dsn(plane_topology, cloud=cloud, database=database)
        )
        try:
            await _assert_postgres_15(conn)

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

            # TP0001 root remains; later revisions may add more public tables.
            # Alembic version table stays in alembic_meta (never public).
            public_tables = await _public_tables(conn)
            assert "tenant_registry" in public_tables
            assert (
                await conn.fetchval(
                    """
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = $1 AND tablename = 'alembic_version_tp'
                    """,
                    ALEMBIC_META,
                )
                == 1
            )
            version = await conn.fetchval(
                f'SELECT version_num FROM "{ALEMBIC_META}".alembic_version_tp'
            )
            assert version is not None
            assert str(version).startswith("tp000"), version
            # Lineage must include TP0001; head may be later (M1+).
            assert version in {
                "tp0001",
                "tp0002",
                "tp0003",
                "tp0004",
                "tp0005",
                "tp0006",
                "tp0007",
            }
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_tp0001_objects_owned_by_db_migrator(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())

    for cloud, database in ((True, "tenant_app"), (False, "local_hub")):
        conn = await asyncpg.connect(
            await _admin_db_dsn(plane_topology, cloud=cloud, database=database)
        )
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
                WHERE schemaname = $1 AND tablename = 'alembic_version_tp'
                """,
                ALEMBIC_META,
            )
            assert ver_owner == "db_migrator"
            ext_owner = await conn.fetchval(
                """
                SELECT r.rolname
                FROM pg_extension e
                JOIN pg_roles r ON r.oid = e.extowner
                WHERE e.extname = 'btree_gist'
                """
            )
            assert ext_owner == "db_migrator"
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_tp0001_rejects_invalid_status_cloud_and_local(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())

    for cloud, database in ((True, "tenant_app"), (False, "local_hub")):
        conn = await asyncpg.connect(
            await _admin_db_dsn(plane_topology, cloud=cloud, database=database)
        )
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
    assert plane_topology.cloud_control.user == "cp_migrator_login"
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())

    conn = await asyncpg.connect(
        await _admin_db_dsn(plane_topology, cloud=True, database="control_plane")
    )
    try:
        await _assert_postgres_15(conn)
        assert await _public_tables(conn) == set()
        assert "tenant_registry" not in await _public_tables(conn)
        assert (
            await conn.fetchval(
                """
                SELECT 1 FROM pg_tables
                WHERE schemaname = $1 AND tablename = 'alembic_version_cp'
                """,
                ALEMBIC_META,
            )
            == 1
        )
        assert (
            await conn.fetchval(
                """
                SELECT 1 FROM pg_tables
                WHERE schemaname = $1 AND tablename = 'alembic_version_tp'
                """,
                ALEMBIC_META,
            )
            is None
        )
        row_count = await conn.fetchval(
            f'SELECT COUNT(*) FROM "{ALEMBIC_META}".alembic_version_cp'
        )
        assert row_count == 0
        owner = await conn.fetchval(
            """
            SELECT tableowner FROM pg_tables
            WHERE schemaname = $1 AND tablename = 'alembic_version_cp'
            """,
            ALEMBIC_META,
        )
        assert owner == "cp_db_migrator"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_separate_alembic_version_tables(plane_topology) -> None:
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())

    for db_name, expected_table, unexpected in (
        ("control_plane", "alembic_version_cp", "alembic_version_tp"),
        ("tenant_app", "alembic_version_tp", "alembic_version_cp"),
    ):
        conn = await asyncpg.connect(
            await _admin_db_dsn(plane_topology, cloud=True, database=db_name)
        )
        try:
            assert (
                await conn.fetchval(
                    """
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = $1 AND tablename = $2
                    """,
                    ALEMBIC_META,
                    expected_table,
                )
                == 1
            )
            assert (
                await conn.fetchval(
                    """
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = $1 AND tablename = $2
                    """,
                    ALEMBIC_META,
                    unexpected,
                )
                is None
            )
            # Must not exist in public
            assert (
                await conn.fetchval(
                    """
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = 'public' AND tablename = $1
                    """,
                    expected_table,
                )
                is None
            )
        finally:
            await conn.close()
