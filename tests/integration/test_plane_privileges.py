"""Schema/object privilege checks (Appendix E.1.4–E.1.5 / E.1.10)."""

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

ALEMBIC_META = "alembic_meta"


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


async def _admin_dsn(plane_topology, *, cloud: bool, database: str) -> str:
    admin = plane_topology.cloud_admin if cloud else plane_topology.local_admin
    return (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/{database}"
    )


@pytest.mark.asyncio
async def test_all_role_identities_lack_dangerous_attributes(plane_topology) -> None:
    """All 12 identities: 8 cloud + 4 local hub."""
    cloud_roles = (
        "db_migrator",
        "db_app_runtime",
        "cp_db_migrator",
        "cp_db_app_runtime",
        "tp_migrator_login",
        "tp_app_login",
        "cp_migrator_login",
        "cp_app_login",
    )
    local_roles = (
        "db_migrator",
        "db_app_runtime",
        "local_migrator_login",
        "local_app_login",
    )
    expected_login = {
        "db_migrator": False,
        "db_app_runtime": False,
        "cp_db_migrator": False,
        "cp_db_app_runtime": False,
        "tp_migrator_login": True,
        "tp_app_login": True,
        "cp_migrator_login": True,
        "cp_app_login": True,
        "local_migrator_login": True,
        "local_app_login": True,
    }

    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb,
                   rolreplication, rolcanlogin
            FROM pg_roles WHERE rolname = ANY($1::text[])
            """,
            list(cloud_roles),
        )
        by_name = {r["rolname"]: r for r in rows}
        assert set(by_name) == set(cloud_roles)
        for name, role in by_name.items():
            assert role["rolsuper"] is False, name
            assert role["rolbypassrls"] is False, name
            assert role["rolcreaterole"] is False, name
            assert role["rolcreatedb"] is False, name
            assert role["rolreplication"] is False, name
            assert role["rolcanlogin"] is expected_login[name], name
    finally:
        await conn.close()

    local = await asyncpg.connect(plane_topology.local_admin.asyncpg_dsn())
    try:
        rows = await local.fetch(
            """
            SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb,
                   rolreplication, rolcanlogin
            FROM pg_roles WHERE rolname = ANY($1::text[])
            """,
            list(local_roles),
        )
        by_name = {r["rolname"]: r for r in rows}
        assert set(by_name) == set(local_roles)
        for name, role in by_name.items():
            assert role["rolsuper"] is False, name
            assert role["rolbypassrls"] is False, name
            assert role["rolcreaterole"] is False, name
            assert role["rolcreatedb"] is False, name
            assert role["rolreplication"] is False, name
            assert role["rolcanlogin"] is expected_login[name], name
    finally:
        await local.close()


@pytest.mark.asyncio
async def test_runtime_schema_and_table_privileges_after_tp0001(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())

    for cloud, database in ((True, "tenant_app"), (False, "local_hub")):
        conn = await asyncpg.connect(
            await _admin_dsn(plane_topology, cloud=cloud, database=database)
        )
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
            owner = await conn.fetchval(
                """
                SELECT tableowner FROM pg_tables
                WHERE schemaname = 'public' AND tablename = 'tenant_registry'
                """
            )
            assert owner == "db_migrator"
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_runtime_login_cannot_ddl_or_truncate_and_dml_rolls_back(
    plane_topology,
) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    conn = await asyncpg.connect(_cloud_dsn(plane_topology, "tp_app_login", "tenant_app"))
    try:
        # Privilege denials outside the DML transaction: a failed statement would
        # abort a shared transaction and block later INSERT/ROLLBACK proofs.
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("CREATE TABLE runtime_forbidden (id int)")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("TRUNCATE tenant_registry")

        tx = conn.transaction()
        await tx.start()
        try:
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
            await tx.rollback()
    finally:
        await conn.close()

    # No residual row
    admin = await asyncpg.connect(
        await _admin_dsn(plane_topology, cloud=True, database="tenant_app")
    )
    try:
        count = await admin.fetchval(
            "SELECT COUNT(*) FROM tenant_registry WHERE tenant_id = $1",
            "01900000-0000-7000-8000-0000000000aa",
        )
        assert count == 0
    finally:
        await admin.close()


@pytest.mark.asyncio
async def test_default_privileges_do_not_grant_public_or_other_plane(
    plane_topology,
) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    conn = await asyncpg.connect(
        await _admin_dsn(plane_topology, cloud=True, database="tenant_app")
    )
    try:
        assert not await conn.fetchval(
            "SELECT has_table_privilege('public', 'tenant_registry', 'SELECT')"
        )
        assert not await conn.fetchval(
            "SELECT has_table_privilege('cp_db_app_runtime', 'tenant_registry', 'SELECT')"
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_alembic_meta_isolated_from_runtime_all_databases(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )

    cases = (
        (True, "tenant_app", "db_migrator", "db_app_runtime", "alembic_version_tp", "tp_app_login"),
        (False, "local_hub", "db_migrator", "db_app_runtime", "alembic_version_tp", "local_app_login"),
        (True, "control_plane", "cp_db_migrator", "cp_db_app_runtime", "alembic_version_cp", "cp_app_login"),
    )
    for cloud, database, owner, runtime, version_table, runtime_login in cases:
        conn = await asyncpg.connect(
            await _admin_dsn(plane_topology, cloud=cloud, database=database)
        )
        try:
            schema_owner = await conn.fetchval(
                """
                SELECT r.rolname
                FROM pg_namespace n
                JOIN pg_roles r ON r.oid = n.nspowner
                WHERE n.nspname = $1
                """,
                ALEMBIC_META,
            )
            assert schema_owner == owner
            assert not await conn.fetchval(
                "SELECT has_schema_privilege($1, $2, 'USAGE')",
                runtime,
                ALEMBIC_META,
            )
            assert not await conn.fetchval(
                "SELECT has_schema_privilege($1, $2, 'CREATE')",
                runtime,
                ALEMBIC_META,
            )
            assert not await conn.fetchval(
                "SELECT has_schema_privilege('public', $1, 'USAGE')",
                ALEMBIC_META,
            )
            # Catalog: no DML for runtime on version table
            fq = f'"{ALEMBIC_META}".{version_table}'
            for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                assert not await conn.fetchval(
                    "SELECT has_table_privilege($1, $2, $3)",
                    runtime,
                    fq,
                    priv,
                ), (database, priv)
            ver_owner = await conn.fetchval(
                """
                SELECT tableowner FROM pg_tables
                WHERE schemaname = $1 AND tablename = $2
                """,
                ALEMBIC_META,
                version_table,
            )
            assert ver_owner == owner
        finally:
            await conn.close()

        # Actual negative access as runtime login
        if cloud:
            dsn = _cloud_dsn(plane_topology, runtime_login, database)
        else:
            dsn = _local_dsn(plane_topology, runtime_login)
        rconn = await asyncpg.connect(dsn)
        try:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await rconn.fetchval(
                    f'SELECT COUNT(*) FROM "{ALEMBIC_META}".{version_table}'
                )
        finally:
            await rconn.close()


@pytest.mark.asyncio
async def test_control_plane_runtime_cannot_create_and_default_acls(
    plane_topology,
) -> None:
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )
    # Runtime cannot CREATE
    rconn = await asyncpg.connect(
        _cloud_dsn(plane_topology, "cp_app_login", "control_plane")
    )
    try:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await rconn.execute("CREATE TABLE cp_runtime_forbidden (id int)")
    finally:
        await rconn.close()

    # Disposable table under cp_db_migrator verifies public default ACLs, then removed
    admin = await asyncpg.connect(
        await _admin_dsn(plane_topology, cloud=True, database="control_plane")
    )
    try:
        await admin.execute("SET ROLE cp_db_migrator")
        await admin.execute(
            "CREATE TABLE public._m0_cp_acl_probe (id int PRIMARY KEY)"
        )
        await admin.execute("RESET ROLE")
        assert await admin.fetchval(
            "SELECT has_table_privilege('cp_db_app_runtime', 'public._m0_cp_acl_probe', 'SELECT')"
        )
        assert await admin.fetchval(
            "SELECT has_table_privilege('cp_db_app_runtime', 'public._m0_cp_acl_probe', 'INSERT')"
        )
        assert not await admin.fetchval(
            "SELECT has_table_privilege('cp_db_app_runtime', 'public._m0_cp_acl_probe', 'TRUNCATE')"
        )
        assert not await admin.fetchval(
            "SELECT has_table_privilege('public', 'public._m0_cp_acl_probe', 'SELECT')"
        )
    finally:
        await admin.execute("DROP TABLE IF EXISTS public._m0_cp_acl_probe")
        await admin.close()


@pytest.mark.asyncio
async def test_cp_migrator_lacks_create_on_control_plane_database(
    plane_topology,
) -> None:
    conn = await asyncpg.connect(plane_topology.cloud_admin.asyncpg_dsn())
    try:
        assert not await conn.fetchval(
            "SELECT has_database_privilege('cp_db_migrator', 'control_plane', 'CREATE')"
        )
        assert not await conn.fetchval(
            "SELECT has_database_privilege('cp_migrator_login', 'control_plane', 'CREATE')"
        )
        assert not await conn.fetchval(
            "SELECT has_database_privilege('public', 'control_plane', 'CREATE')"
        )
        # Tenant still has CREATE for btree_gist
        assert await conn.fetchval(
            "SELECT has_database_privilege('db_migrator', 'tenant_app', 'CREATE')"
        )
    finally:
        await conn.close()
