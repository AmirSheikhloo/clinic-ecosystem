"""Direct/transitive membership and SET ROLE proofs (Appendix E.1.3 / E.1.4 / E.1.10)."""

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


def _local_dsn(plane_topology, user: str) -> str:
    pwd = plane_topology.passwords[user]
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{plane_topology.local_admin.host}:{plane_topology.local_admin.port}"
        f"/local_hub"
    )


async def _pg_has_role(
    conn: asyncpg.Connection, member: str, role: str, mode: str = "MEMBER"
) -> bool:
    return bool(await conn.fetchval("SELECT pg_has_role($1, $2, $3)", member, role, mode))


@pytest.mark.asyncio
async def test_cloud_runtime_membership_direct_and_transitive(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        # Direct/transitive via pg_has_role MEMBER (includes inheritance)
        assert await _pg_has_role(conn, "tp_app_login", "db_app_runtime")
        assert not await _pg_has_role(conn, "tp_app_login", "db_migrator")
        assert not await _pg_has_role(conn, "tp_app_login", "cp_db_migrator")
        assert not await _pg_has_role(conn, "tp_app_login", "cp_db_app_runtime")

        assert await _pg_has_role(conn, "cp_app_login", "cp_db_app_runtime")
        assert not await _pg_has_role(conn, "cp_app_login", "cp_db_migrator")
        assert not await _pg_has_role(conn, "cp_app_login", "db_migrator")
        assert not await _pg_has_role(conn, "cp_app_login", "db_app_runtime")

        assert await _pg_has_role(conn, "tp_migrator_login", "db_migrator")
        assert not await _pg_has_role(conn, "tp_migrator_login", "db_app_runtime")
        assert not await _pg_has_role(conn, "tp_migrator_login", "cp_db_migrator")

        assert await _pg_has_role(conn, "cp_migrator_login", "cp_db_migrator")
        assert not await _pg_has_role(conn, "cp_migrator_login", "cp_db_app_runtime")
        assert not await _pg_has_role(conn, "cp_migrator_login", "db_migrator")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_local_hub_runtime_membership(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.local_admin.asyncpg_dsn())
    try:
        assert await _pg_has_role(conn, "local_app_login", "db_app_runtime")
        assert not await _pg_has_role(conn, "local_app_login", "db_migrator")
        assert await _pg_has_role(conn, "local_migrator_login", "db_migrator")
        assert not await _pg_has_role(conn, "local_migrator_login", "db_app_runtime")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_runtime_cannot_set_role_to_migrator_or_other_plane(
    plane_topology,
) -> None:
    # Tenant runtime
    conn = await asyncpg.connect(_cloud_dsn(plane_topology, "tp_app_login", "tenant_app"))
    try:
        await conn.execute("RESET ROLE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_migrator")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_app_runtime")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_migrator")
        # Own runtime role is allowed
        await conn.execute("SET ROLE db_app_runtime")
        assert await conn.fetchval("SELECT current_user") == "db_app_runtime"
    finally:
        await conn.close()

    # Control runtime
    conn = await asyncpg.connect(
        _cloud_dsn(plane_topology, "cp_app_login", "control_plane")
    )
    try:
        await conn.execute("RESET ROLE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_migrator")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_app_runtime")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_migrator")
        await conn.execute("SET ROLE cp_db_app_runtime")
        assert await conn.fetchval("SELECT current_user") == "cp_db_app_runtime"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_migrator_logins_assume_only_own_migrator_role(plane_topology) -> None:
    conn = await asyncpg.connect(
        _cloud_dsn(plane_topology, "tp_migrator_login", "tenant_app")
    )
    try:
        assert await conn.fetchval("SELECT session_user") == "tp_migrator_login"
        assert await conn.fetchval("SELECT current_user") == "tp_migrator_login"
        await conn.execute("SET ROLE db_migrator")
        assert await conn.fetchval("SELECT current_user") == "db_migrator"
        await conn.execute("RESET ROLE")
        assert await conn.fetchval("SELECT current_user") == "tp_migrator_login"
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_migrator")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_app_runtime")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_app_runtime")
    finally:
        await conn.close()

    conn = await asyncpg.connect(
        _cloud_dsn(plane_topology, "cp_migrator_login", "control_plane")
    )
    try:
        assert await conn.fetchval("SELECT session_user") == "cp_migrator_login"
        await conn.execute("SET ROLE cp_db_migrator")
        assert await conn.fetchval("SELECT current_user") == "cp_db_migrator"
        await conn.execute("RESET ROLE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_migrator")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE cp_db_app_runtime")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_local_hub_set_role_boundaries(plane_topology) -> None:
    conn = await asyncpg.connect(_local_dsn(plane_topology, "local_app_login"))
    try:
        await conn.execute("RESET ROLE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_migrator")
        await conn.execute("SET ROLE db_app_runtime")
        assert await conn.fetchval("SELECT current_user") == "db_app_runtime"
    finally:
        await conn.close()

    conn = await asyncpg.connect(_local_dsn(plane_topology, "local_migrator_login"))
    try:
        assert await conn.fetchval("SELECT session_user") == "local_migrator_login"
        assert await conn.fetchval("SELECT current_user") == "local_migrator_login"
        await conn.execute("SET ROLE db_migrator")
        assert await conn.fetchval("SELECT current_user") == "db_migrator"
        await conn.execute("RESET ROLE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("SET ROLE db_app_runtime")
    finally:
        await conn.close()
