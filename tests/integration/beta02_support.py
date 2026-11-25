"""Shared harness for BETA-02 operations API integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote_plus

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.presentation.http.app import create_app
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.beta02_seed import (
    DEPUTY_PASSWORD, MANAGER_PASSWORD, OWNER_PASSWORD, Beta02Seed, seed_beta02_operations,
)
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON


@dataclass
class OpsStack:
    client: TestClient
    seed: Beta02Seed
    topology: object

    def login(self, login: str, password: str) -> dict[str, str]:
        res = self.client.post(
            "/api/v1/auth/login", json={"login_identifier": login, "password": password}
        )
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    def owner(self) -> dict[str, str]:
        return self.login(self.seed.owner_login, OWNER_PASSWORD)

    def manager(self) -> dict[str, str]:
        return self.login(self.seed.manager_login, MANAGER_PASSWORD)

    def deputy(self) -> dict[str, str]:
        return self.login(self.seed.deputy_login, DEPUTY_PASSWORD)

    def receptionist(self) -> dict[str, str]:
        base = self.seed.base
        return self.login(base.receptionist_login, base.receptionist_password)

    def unauthorized(self) -> dict[str, str]:
        base = self.seed.base
        return self.login(base.unauthorized_login, base.unauthorized_password)

    def admin_query(self, sql: str, *args):
        """Run a read-only query as the migrator with the realm tenant bound."""
        async def _run():
            conn = await asyncpg.connect(self.topology.cloud_tenant.asyncpg_dsn())
            try:
                await conn.execute("SET ROLE db_migrator")
                await conn.execute(
                    "SELECT set_config('app.current_tenant_id', $1, false)",
                    str(self.seed.base.tenant_a_id),
                )
                return await conn.fetch(sql, *args)
            finally:
                await conn.close()
        return asyncio.run(_run())


def _app_url(topology) -> str:
    pwd = topology.passwords["tp_app_login"]
    ep = topology.cloud_tenant
    return f"postgresql+asyncpg://{quote_plus('tp_app_login')}:{quote_plus(pwd)}@{ep.host}:{ep.port}/tenant_app"


def make_ops_stack(plane_topology) -> Iterator[OpsStack]:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)

    async def _prepare() -> Beta02Seed:
        await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
        conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
        try:
            return await seed_beta02_operations(conn)
        finally:
            await conn.close()

    seed = asyncio.run(_prepare())
    settings = load_auth_settings(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(seed.base.tenant_a_id),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "integration-test-signing-secret-32chars!!",
            "CLINIC_DATABASE_URL": _app_url(plane_topology),
            "CLINIC_ACCESS_TOKEN_TTL_SECONDS": "900",
        }
    )
    engine = create_async_engine(_app_url(plane_topology), pool_size=10)
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    with TestClient(app) as client:
        yield OpsStack(client=client, seed=seed, topology=plane_topology)
