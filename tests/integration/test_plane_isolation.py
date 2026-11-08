"""Plane isolation negative tests (v3.0.1 Appendix E.1 / clause 744)."""

from __future__ import annotations

import asyncpg
import pytest

from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


async def _try_connect(dsn: str) -> Exception | None:
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:  # noqa: BLE001 — assert denial shape
        return exc
    else:
        await conn.close()
        return None


@pytest.mark.asyncio
async def test_tenant_login_cannot_connect_to_control_plane(plane_topology) -> None:
    pwd = plane_topology.passwords["tp_app_login"]
    dsn = (
        f"postgresql://tp_app_login:{pwd}"
        f"@{plane_topology.cloud_admin.host}:{plane_topology.cloud_admin.port}"
        f"/control_plane"
    )
    err = await _try_connect(dsn)
    assert err is not None, "Tenant Plane login must not CONNECT to control_plane"


@pytest.mark.asyncio
async def test_control_login_cannot_connect_to_tenant_app(plane_topology) -> None:
    pwd = plane_topology.passwords["cp_app_login"]
    dsn = (
        f"postgresql://cp_app_login:{pwd}"
        f"@{plane_topology.cloud_admin.host}:{plane_topology.cloud_admin.port}"
        f"/tenant_app"
    )
    err = await _try_connect(dsn)
    assert err is not None, "Control Plane login must not CONNECT to tenant_app"


@pytest.mark.asyncio
async def test_same_plane_connect_allowed(plane_topology) -> None:
    tp_pwd = plane_topology.passwords["tp_app_login"]
    cp_pwd = plane_topology.passwords["cp_app_login"]
    tp_dsn = (
        f"postgresql://tp_app_login:{tp_pwd}"
        f"@{plane_topology.cloud_admin.host}:{plane_topology.cloud_admin.port}"
        f"/tenant_app"
    )
    cp_dsn = (
        f"postgresql://cp_app_login:{cp_pwd}"
        f"@{plane_topology.cloud_admin.host}:{plane_topology.cloud_admin.port}"
        f"/control_plane"
    )
    assert await _try_connect(tp_dsn) is None
    assert await _try_connect(cp_dsn) is None


@pytest.mark.asyncio
async def test_runtime_not_member_of_migrator(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT r.rolname AS member, g.rolname AS granted
            FROM pg_auth_members m
            JOIN pg_roles r ON r.oid = m.member
            JOIN pg_roles g ON g.oid = m.roleid
            WHERE r.rolname IN ('tp_app_login', 'cp_app_login')
            """
        )
        memberships = {(r["member"], r["granted"]) for r in rows}
        assert ("tp_app_login", "db_migrator") not in memberships
        assert ("tp_app_login", "cp_db_migrator") not in memberships
        assert ("tp_app_login", "cp_db_app_runtime") not in memberships
        assert ("cp_app_login", "cp_db_migrator") not in memberships
        assert ("cp_app_login", "db_migrator") not in memberships
        assert ("cp_app_login", "db_app_runtime") not in memberships
        assert ("tp_app_login", "db_app_runtime") in memberships
        assert ("cp_app_login", "cp_db_app_runtime") in memberships
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_public_connect_revoked_on_cloud_databases(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        for db_name in ("control_plane", "tenant_app"):
            has_connect = await conn.fetchval(
                """
                SELECT has_database_privilege('public', $1, 'CONNECT')
                """,
                db_name,
            )
            has_temp = await conn.fetchval(
                """
                SELECT has_database_privilege('public', $1, 'TEMPORARY')
                """,
                db_name,
            )
            assert has_connect is False, f"PUBLIC CONNECT must be revoked on {db_name}"
            assert has_temp is False, f"PUBLIC TEMPORARY must be revoked on {db_name}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_local_hub_reuses_tenant_group_role_names(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.local_admin.asyncpg_dsn())
    try:
        roles = {
            r["rolname"]
            for r in await conn.fetch(
                "SELECT rolname FROM pg_roles WHERE rolname IN "
                "('db_migrator', 'db_app_runtime', 'local_migrator_login', 'local_app_login')"
            )
        }
        assert roles == {
            "db_migrator",
            "db_app_runtime",
            "local_migrator_login",
            "local_app_login",
        }
    finally:
        await conn.close()
