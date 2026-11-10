"""Plane isolation negative tests (v3.0.1 Appendix E.1.3 / E.1.6 / E.1.10)."""

from __future__ import annotations

from urllib.parse import quote_plus

import asyncpg
import pytest

from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


def _cloud_dsn(plane_topology, user: str, database: str) -> str:
    pwd = plane_topology.passwords[user]
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{plane_topology.cloud_admin.host}:{plane_topology.cloud_admin.port}"
        f"/{database}"
    )


def _local_dsn(plane_topology, user: str, database: str = "local_hub") -> str:
    pwd = plane_topology.passwords[user]
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{plane_topology.local_admin.host}:{plane_topology.local_admin.port}"
        f"/{database}"
    )


async def _try_connect(dsn: str) -> Exception | None:
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:  # noqa: BLE001 — assert denial shape
        return exc
    else:
        await conn.close()
        return None


# --- Previously passing CONNECT tests (retained) ---


@pytest.mark.asyncio
async def test_tenant_login_cannot_connect_to_control_plane(plane_topology) -> None:
    err = await _try_connect(_cloud_dsn(plane_topology, "tp_app_login", "control_plane"))
    assert err is not None, "Tenant Plane login must not CONNECT to control_plane"


@pytest.mark.asyncio
async def test_control_login_cannot_connect_to_tenant_app(plane_topology) -> None:
    err = await _try_connect(_cloud_dsn(plane_topology, "cp_app_login", "tenant_app"))
    assert err is not None, "Control Plane login must not CONNECT to tenant_app"


@pytest.mark.asyncio
async def test_same_plane_connect_allowed(plane_topology) -> None:
    assert (
        await _try_connect(_cloud_dsn(plane_topology, "tp_app_login", "tenant_app"))
        is None
    )
    assert (
        await _try_connect(_cloud_dsn(plane_topology, "cp_app_login", "control_plane"))
        is None
    )


@pytest.mark.asyncio
async def test_public_connect_revoked_on_cloud_databases(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        for db_name in ("control_plane", "tenant_app"):
            has_connect = await conn.fetchval(
                "SELECT has_database_privilege('public', $1, 'CONNECT')",
                db_name,
            )
            has_temp = await conn.fetchval(
                "SELECT has_database_privilege('public', $1, 'TEMPORARY')",
                db_name,
            )
            assert has_connect is False, f"PUBLIC CONNECT must be revoked on {db_name}"
            assert has_temp is False, f"PUBLIC TEMPORARY must be revoked on {db_name}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_public_connect_revoked_on_local_hub(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.local_admin.asyncpg_dsn())
    try:
        assert (
            await conn.fetchval(
                "SELECT has_database_privilege('public', 'local_hub', 'CONNECT')"
            )
            is False
        )
        assert (
            await conn.fetchval(
                "SELECT has_database_privilege('public', 'local_hub', 'TEMPORARY')"
            )
            is False
        )
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


# --- New: migrator cross-plane CONNECT denials ---


@pytest.mark.asyncio
async def test_tenant_migrator_cannot_connect_to_control_plane(plane_topology) -> None:
    err = await _try_connect(
        _cloud_dsn(plane_topology, "tp_migrator_login", "control_plane")
    )
    assert err is not None


@pytest.mark.asyncio
async def test_control_migrator_cannot_connect_to_tenant_app(plane_topology) -> None:
    err = await _try_connect(
        _cloud_dsn(plane_topology, "cp_migrator_login", "tenant_app")
    )
    assert err is not None


@pytest.mark.asyncio
async def test_plane_logins_connect_only_to_assigned_databases(plane_topology) -> None:
    allowed = [
        ("tp_app_login", "tenant_app"),
        ("tp_migrator_login", "tenant_app"),
        ("cp_app_login", "control_plane"),
        ("cp_migrator_login", "control_plane"),
    ]
    denied = [
        ("tp_app_login", "control_plane"),
        ("tp_migrator_login", "control_plane"),
        ("cp_app_login", "tenant_app"),
        ("cp_migrator_login", "tenant_app"),
    ]
    for user, db in allowed:
        assert await _try_connect(_cloud_dsn(plane_topology, user, db)) is None, (
            f"{user} must CONNECT to {db}"
        )
    for user, db in denied:
        assert await _try_connect(_cloud_dsn(plane_topology, user, db)) is not None, (
            f"{user} must not CONNECT to {db}"
        )


@pytest.mark.asyncio
async def test_local_hub_logins_can_connect(plane_topology) -> None:
    assert await _try_connect(_local_dsn(plane_topology, "local_app_login")) is None
    assert await _try_connect(_local_dsn(plane_topology, "local_migrator_login")) is None
