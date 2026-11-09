"""Two-container PostgreSQL 15 topology for Gate A M0 integration tests.

Cloud container: control_plane + tenant_app logical databases.
Local Hub container: local_hub logical database.
Ephemeral credentials are created at runtime and discarded after the session.

Migration endpoints use actual plane migrator logins (tp_migrator_login /
local_migrator_login / cp_migrator_login). Admin endpoints are limited to
provisioning and independent inspection (Appendix E.1.10).
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import asyncpg
import pytest

from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "ops" / "db_bootstrap"
CLOUD_ROLES_SQL = (BOOTSTRAP / "cloud_roles.sql").read_text(encoding="utf-8")
LOCAL_HUB_ROLES_SQL = (BOOTSTRAP / "local_hub_roles.sql").read_text(encoding="utf-8")
TENANT_SCHEMA_PRIVS_SQL = (BOOTSTRAP / "tenant_plane_schema_privileges.sql").read_text(
    encoding="utf-8"
)
CONTROL_SCHEMA_PRIVS_SQL = (
    BOOTSTRAP / "control_plane_schema_privileges.sql"
).read_text(encoding="utf-8")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires Docker and PostgreSQL Testcontainers",
    )


@dataclass(frozen=True)
class DbEndpoint:
    host: str
    port: int
    user: str
    password: str
    database: str

    def asyncpg_dsn(self) -> str:
        return (
            f"postgresql://{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def sqlalchemy_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class PlaneTopology:
    """Migration endpoints use plane migrator logins; admins for inspection only."""

    cloud_control: DbEndpoint
    cloud_tenant: DbEndpoint
    local_hub: DbEndpoint
    cloud_admin: DbEndpoint
    local_admin: DbEndpoint
    passwords: dict[str, str]


def _split_sql_statements(script: str) -> list[str]:
    """Split SQL on statement-ending semicolons outside dollar-quoted bodies."""
    statements: list[str] = []
    buf: list[str] = []
    in_dollar = False
    for line in script.splitlines():
        if "$$" in line:
            for _ in range(line.count("$$")):
                in_dollar = not in_dollar
        buf.append(line)
        if not in_dollar and line.rstrip().endswith(";"):
            statements.append("\n".join(buf))
            buf = []
    trailing = "\n".join(buf).strip()
    if trailing:
        statements.append(trailing)
    return statements


async def _exec_script(conn: asyncpg.Connection, script: str) -> None:
    for stmt in _split_sql_statements(script):
        body = stmt.strip()
        if body:
            await conn.execute(body)


async def _create_database(admin_dsn: str, db_name: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def _set_role_password(
    conn: asyncpg.Connection, role: str, password: str
) -> None:
    quoted = await conn.fetchval("SELECT quote_literal($1)", password)
    await conn.execute(f"ALTER ROLE {role} PASSWORD {quoted}")


async def _assert_server_is_postgres_15(admin_dsn: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        version = await conn.fetchval("SHOW server_version")
        assert version is not None
        assert str(version).startswith("15."), (
            f"Testcontainers must provide PostgreSQL 15.x, got {version!r}"
        )
    finally:
        await conn.close()


async def _apply_db_script(admin: DbEndpoint, database: str, script: str) -> None:
    dsn = (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/{database}"
    )
    conn = await asyncpg.connect(dsn)
    try:
        await _exec_script(conn, script)
    finally:
        await conn.close()


async def _bootstrap_cloud(admin: DbEndpoint, passwords: dict[str, str]) -> None:
    admin_dsn = admin.asyncpg_dsn()
    await _assert_server_is_postgres_15(admin_dsn)
    await _create_database(admin_dsn, "control_plane")
    await _create_database(admin_dsn, "tenant_app")

    conn = await asyncpg.connect(admin_dsn)
    try:
        await _exec_script(conn, CLOUD_ROLES_SQL)
        for role, pwd in passwords.items():
            if role.startswith(("tp_", "cp_")):
                await _set_role_password(conn, role, pwd)
    finally:
        await conn.close()

    await _apply_db_script(admin, "tenant_app", TENANT_SCHEMA_PRIVS_SQL)
    await _apply_db_script(admin, "control_plane", CONTROL_SCHEMA_PRIVS_SQL)


async def _bootstrap_local(admin: DbEndpoint, passwords: dict[str, str]) -> None:
    admin_dsn = admin.asyncpg_dsn()
    await _assert_server_is_postgres_15(admin_dsn)
    await _create_database(admin_dsn, "local_hub")
    conn = await asyncpg.connect(admin_dsn)
    try:
        await _exec_script(conn, LOCAL_HUB_ROLES_SQL)
        for role, pwd in passwords.items():
            if role.startswith("local_"):
                await _set_role_password(conn, role, pwd)
    finally:
        await conn.close()

    await _apply_db_script(admin, "local_hub", TENANT_SCHEMA_PRIVS_SQL)


@pytest.fixture(scope="session")
def plane_topology():
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)

    from testcontainers.postgres import PostgresContainer

    passwords = {
        "tp_migrator_login": secrets.token_urlsafe(24),
        "tp_app_login": secrets.token_urlsafe(24),
        "cp_migrator_login": secrets.token_urlsafe(24),
        "cp_app_login": secrets.token_urlsafe(24),
        "local_migrator_login": secrets.token_urlsafe(24),
        "local_app_login": secrets.token_urlsafe(24),
    }

    cloud = PostgresContainer("postgres:15")
    local = PostgresContainer("postgres:15")
    cloud.start()
    local.start()

    try:
        cloud_admin = DbEndpoint(
            host=cloud.get_container_host_ip(),
            port=int(cloud.get_exposed_port(5432)),
            user=cloud.username,
            password=cloud.password,
            database=cloud.dbname,
        )
        local_admin = DbEndpoint(
            host=local.get_container_host_ip(),
            port=int(local.get_exposed_port(5432)),
            user=local.username,
            password=local.password,
            database=local.dbname,
        )

        asyncio.run(_bootstrap_cloud(cloud_admin, passwords))
        asyncio.run(_bootstrap_local(local_admin, passwords))

        yield PlaneTopology(
            cloud_control=DbEndpoint(
                host=cloud_admin.host,
                port=cloud_admin.port,
                user="cp_migrator_login",
                password=passwords["cp_migrator_login"],
                database="control_plane",
            ),
            cloud_tenant=DbEndpoint(
                host=cloud_admin.host,
                port=cloud_admin.port,
                user="tp_migrator_login",
                password=passwords["tp_migrator_login"],
                database="tenant_app",
            ),
            local_hub=DbEndpoint(
                host=local_admin.host,
                port=local_admin.port,
                user="local_migrator_login",
                password=passwords["local_migrator_login"],
                database="local_hub",
            ),
            cloud_admin=DbEndpoint(
                host=cloud_admin.host,
                port=cloud_admin.port,
                user=cloud_admin.user,
                password=cloud_admin.password,
                database="postgres",
            ),
            local_admin=DbEndpoint(
                host=local_admin.host,
                port=local_admin.port,
                user=local_admin.user,
                password=local_admin.password,
                database="postgres",
            ),
            passwords=passwords,
        )
    finally:
        cloud.stop()
        local.stop()
