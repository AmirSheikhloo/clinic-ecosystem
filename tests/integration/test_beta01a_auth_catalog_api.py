"""BETA-01A auth + catalog integration tests on disposable PostgreSQL 15.

Skipped when Docker is unavailable. Uses Testcontainers only — never a
persistent/remote/production database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.presentation.http.app import create_app
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.beta01a_seed import (
    deactivate_account,
    lock_account,
    seed_beta01a_auth_catalog,
)
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration


def _app_url(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql+asyncpg://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


def _runtime_role_dsn(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


async def _ensure_migrated(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())


def _build_client(plane_topology, seed):
    settings = load_auth_settings(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(seed.tenant_a_id),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "integration-test-signing-secret-32chars!!",
            "CLINIC_DATABASE_URL": _app_url(plane_topology),
            "CLINIC_ACCESS_TOKEN_TTL_SECONDS": "900",
        }
    )
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    return TestClient(app), settings, engine


@pytest.mark.asyncio
async def test_beta01a_login_me_catalog_and_isolation(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01a_auth_catalog(seed_conn)
    finally:
        await seed_conn.close()

    client, settings, engine = _build_client(plane_topology, seed)
    try:
        with client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            bad = client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.receptionist_login,
                    "password": "definitely-wrong-password",
                },
            )
            assert bad.status_code == 401
            assert bad.json()["detail"]["error"] == "invalid_credentials"

            ok = client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.receptionist_login,
                    "password": seed.receptionist_password,
                },
            )
            assert ok.status_code == 200
            token = ok.json()["access_token"]
            assert ok.json()["tenant_id"] == str(seed.tenant_a_id)
            assert seed.receptionist_password not in ok.text

            me = client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert me.status_code == 200
            assert me.json()["account_id"] == str(seed.receptionist_account_id)

            denied_missing = client.get("/api/v1/catalog/services")
            assert denied_missing.status_code == 401

            services = client.get(
                "/api/v1/catalog/services",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert services.status_code == 200
            items = services.json()["items"]
            ids = {item["id"] for item in items}
            assert str(seed.service_a_id) in ids
            assert str(seed.service_b_id) not in ids

            # Unauthorized role: can authenticate but cannot read catalog.
            unauth_login = client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.unauthorized_login,
                    "password": seed.unauthorized_password,
                },
            )
            assert unauth_login.status_code == 200
            unauth_token = unauth_login.json()["access_token"]
            forbidden = client.get(
                "/api/v1/catalog/services",
                headers={"Authorization": f"Bearer {unauth_token}"},
            )
            assert forbidden.status_code == 403

            # Forged/wrong-tenant token must not unlock tenant B data.
            forged, _ = issue_access_token(
                settings=settings,
                principal_id=seed.receptionist_account_id,
                tenant_id=seed.tenant_b_id,
            )
            forged_resp = client.get(
                "/api/v1/catalog/services",
                headers={"Authorization": f"Bearer {forged}"},
            )
            assert forged_resp.status_code == 401

            expired, _ = issue_access_token(
                settings=settings,
                principal_id=seed.receptionist_account_id,
                tenant_id=seed.tenant_a_id,
                now=datetime.now(timezone.utc) - timedelta(hours=3),
            )
            expired_resp = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired}"},
            )
            assert expired_resp.status_code == 401

            malformed = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
            assert malformed.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_beta01a_locked_and_inactive_accounts(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01a_auth_catalog(seed_conn)
        await lock_account(
            seed_conn,
            tenant_id=seed.tenant_a_id,
            account_id=seed.receptionist_account_id,
        )
    finally:
        await seed_conn.close()

    client, _, engine = _build_client(plane_topology, seed)
    try:
        with client:
            locked = client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.receptionist_login,
                    "password": seed.receptionist_password,
                },
            )
            assert locked.status_code == 401
            assert locked.json()["detail"]["error"] == "invalid_credentials"
    finally:
        await engine.dispose()

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed2 = await seed_beta01a_auth_catalog(seed_conn)
        await deactivate_account(
            seed_conn,
            tenant_id=seed2.tenant_a_id,
            account_id=seed2.receptionist_account_id,
        )
    finally:
        await seed_conn.close()

    client2, _, engine2 = _build_client(plane_topology, seed2)
    try:
        with client2:
            inactive = client2.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed2.receptionist_login,
                    "password": seed2.receptionist_password,
                },
            )
            assert inactive.status_code == 401
    finally:
        await engine2.dispose()


@pytest.mark.asyncio
async def test_beta01a_runtime_role_has_no_superuser_or_bypassrls(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    conn = await asyncpg.connect(_runtime_role_dsn(plane_topology))
    try:
        row = await conn.fetchrow(
            """
            SELECT rolsuper, rolbypassrls
            FROM pg_roles
            WHERE rolname = current_user
            """
        )
        assert row is not None
        assert row["rolsuper"] is False
        assert row["rolbypassrls"] is False
    finally:
        await conn.close()


def _migrator_url(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_migrator_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql+asyncpg://{quote_plus('tp_migrator_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


@pytest.mark.asyncio
async def test_beta01a_role_preflight_accepts_runtime_rejects_migrator(
    plane_topology,
) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    from clinic_ecosystem.infrastructure.auth.db_role_preflight import (
        UnsafeDatabaseRoleError,
        verify_runtime_db_role,
    )
    from clinic_ecosystem.infrastructure.auth.settings import AuthSettingsError

    runtime_engine = create_async_engine(_app_url(plane_topology), pool_size=1)
    migrator_engine = create_async_engine(_migrator_url(plane_topology), pool_size=1)
    try:
        snap = await verify_runtime_db_role(runtime_engine)
        assert snap.current_user == "tp_app_login"
        assert snap.rolsuper is False
        assert snap.rolbypassrls is False

        with pytest.raises(UnsafeDatabaseRoleError):
            await verify_runtime_db_role(migrator_engine)

        settings = load_auth_settings(
            {
                "CLINIC_ENV": "test",
                "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
                "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(uuid4()),
                "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "integration-test-signing-secret-32chars!!",
                "CLINIC_DATABASE_URL": _migrator_url(plane_topology),
            }
        )
        unsafe_app = create_app(
            settings=settings,
            engine=migrator_engine,
            create_engine_from_settings=False,
        )
        with pytest.raises(AuthSettingsError):
            with TestClient(unsafe_app):
                pass
    finally:
        await runtime_engine.dispose()
        await migrator_engine.dispose()


@pytest.mark.asyncio
async def test_beta01a_failed_login_lockout_is_atomic(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01a_auth_catalog(seed_conn)
    finally:
        await seed_conn.close()

    settings = load_auth_settings(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(seed.tenant_a_id),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "integration-test-signing-secret-32chars!!",
            "CLINIC_DATABASE_URL": _app_url(plane_topology),
            "CLINIC_MAX_FAILED_LOGIN_ATTEMPTS": "3",
            "CLINIC_LOCKOUT_MINUTES": "30",
        }
    )
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    try:
        with TestClient(app) as client:
            for _ in range(3):
                resp = client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_identifier": seed.receptionist_login,
                        "password": "wrong-password-for-lockout",
                    },
                )
                assert resp.status_code == 401
            locked = client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.receptionist_login,
                    "password": seed.receptionist_password,
                },
            )
            assert locked.status_code == 401

        conn = await asyncpg.connect(_runtime_role_dsn(plane_topology))
        try:
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, false)",
                str(seed.tenant_a_id),
            )
            row = await conn.fetchrow(
                """
                SELECT failed_login_attempts, locked_until_utc
                FROM user_accounts
                WHERE id = $1 AND tenant_id = $2
                """,
                seed.receptionist_account_id,
                seed.tenant_a_id,
            )
            assert row is not None
            assert int(row["failed_login_attempts"]) >= 3
            assert row["locked_until_utc"] is not None
        finally:
            await conn.close()
    finally:
        await engine.dispose()
