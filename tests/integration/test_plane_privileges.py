"""Schema/object privilege checks (Appendix E.1.4–E.1.5 / E.1.10)."""

from __future__ import annotations

from urllib.parse import quote_plus

import asyncpg
import pytest

from tests.integration.alembic_runner import upgrade_tenant_plane_async
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


@pytest.mark.asyncio
async def test_runtime_roles_lack_dangerous_attributes(plane_topology) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb
            FROM pg_roles
            WHERE rolname IN (
              'db_app_runtime', 'cp_db_app_runtime',
              'tp_app_login', 'cp_app_login',
              'local_app_login'
            )
            """
        )
        by_name = {r["rolname"]: r for r in rows}
        # local_app_login lives on the other cluster — check cloud ones here
        for name in (
            "db_app_runtime",
            "cp_db_app_runtime",
            "tp_app_login",
            "cp_app_login",
        ):
            role = by_name[name]
            assert role["rolsuper"] is False
            assert role["rolbypassrls"] is False
            assert role["rolcreaterole"] is False
    finally:
        await conn.close()

    local = await asyncpg.connect(plane_topology.local_admin.asyncpg_dsn())
    try:
        role = await local.fetchrow(
            """
            SELECT rolsuper, rolbypassrls, rolcreaterole
            FROM pg_roles WHERE rolname = 'local_app_login'
            """
        )
        assert role is not None
        assert role["rolsuper"] is False
        assert role["rolbypassrls"] is False
        assert role["rolcreaterole"] is False
    finally:
        await local.close()


@pytest.mark.asyncio
async def test_runtime_schema_and_table_privileges_after_tp0001(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())

    admin = plane_topology.cloud_admin
    dsn = (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    conn = await asyncpg.connect(dsn)
    try:
        assert await conn.fetchval(
            "SELECT has_schema_privilege('db_app_runtime', 'public', 'USAGE')"
        )
        assert not await conn.fetchval(
            "SELECT has_schema_privilege('db_app_runtime', 'public', 'CREATE')"
        )
        for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert await conn.fetchval(
                "SELECT has_table_privilege('db_app_runtime', 'tenant_registry', $1)",
                priv,
            ), priv
        assert not await conn.fetchval(
            "SELECT has_table_privilege('db_app_runtime', 'tenant_registry', 'TRUNCATE')"
        )
        # Runtime must not own tenant tables
        owner = await conn.fetchval(
            """
            SELECT tableowner FROM pg_tables
            WHERE schemaname = 'public' AND tablename = 'tenant_registry'
            """
        )
        assert owner == "db_migrator"
        assert owner != "db_app_runtime"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_runtime_login_cannot_ddl_or_truncate(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    conn = await asyncpg.connect(_cloud_dsn(plane_topology, "tp_app_login", "tenant_app"))
    try:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("CREATE TABLE runtime_forbidden (id int)")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("TRUNCATE tenant_registry")
        # DML is allowed
        await conn.execute(
            """
            INSERT INTO tenant_registry (
              tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
            ) VALUES (
              '01900000-0000-7000-8000-0000000000aa',
              'ACTIVE', 'UTC', NOW(), NOW()
            )
            """
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_default_privileges_do_not_grant_public_or_other_plane(
    plane_topology,
) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    admin = plane_topology.cloud_admin
    dsn = (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    conn = await asyncpg.connect(dsn)
    try:
        # PUBLIC must not receive table privileges via default grants
        assert not await conn.fetchval(
            "SELECT has_table_privilege('public', 'tenant_registry', 'SELECT')"
        )
        # Other plane runtime must not receive Tenant Plane table grants
        assert not await conn.fetchval(
            "SELECT has_table_privilege('cp_db_app_runtime', 'tenant_registry', 'SELECT')"
        )
    finally:
        await conn.close()
