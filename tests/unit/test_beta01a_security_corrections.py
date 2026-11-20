"""Unit coverage for BETA-01A targeted security corrections (no Docker)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.db_role_preflight import (
    RuntimeRoleSnapshot,
    UnsafeDatabaseRoleError,
    evaluate_runtime_role,
)
from clinic_ecosystem.infrastructure.auth.settings import (
    AuthSettingsError,
    load_auth_settings,
    require_token_tenant_matches_realm,
    require_usable_auth_realm,
)
from clinic_ecosystem.infrastructure.persistence.user_accounts import (
    SqlUserAccountRepository,
)
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.presentation.http.dependencies import get_uow


def _settings(**overrides: str):
    tenant = overrides.pop("_tenant", None) or str(uuid4())
    env = {
        "CLINIC_ENV": "test",
        "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
        "CLINIC_BETA_AUTH_REALM_TENANT_ID": tenant,
        "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "unit-test-signing-secret-32b-min!!",
        "CLINIC_DATABASE_URL": "postgresql+asyncpg://unused:unused@127.0.0.1/tenant_app",
    }
    env.update(overrides)
    return load_auth_settings(env), env["CLINIC_BETA_AUTH_REALM_TENANT_ID"]


def _app(settings):
    engine = MagicMock(name="async_engine")
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    return app


def test_lockout_thresholds_must_be_positive_and_bounded() -> None:
    with pytest.raises(AuthSettingsError):
        load_auth_settings(
            {
                "CLINIC_ENV": "test",
                "CLINIC_MAX_FAILED_LOGIN_ATTEMPTS": "0",
                "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "x" * 32,
            }
        )
    with pytest.raises(AuthSettingsError):
        load_auth_settings(
            {
                "CLINIC_ENV": "test",
                "CLINIC_LOCKOUT_MINUTES": "0",
                "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "x" * 32,
            }
        )
    with pytest.raises(AuthSettingsError):
        load_auth_settings(
            {
                "CLINIC_ENV": "test",
                "CLINIC_MAX_FAILED_LOGIN_ATTEMPTS": "99",
                "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "x" * 32,
            }
        )


def test_token_tenant_must_match_realm() -> None:
    settings, realm = _settings()
    require_token_tenant_matches_realm(settings, __import__("uuid").UUID(realm))
    with pytest.raises(AuthSettingsError):
        require_token_tenant_matches_realm(settings, uuid4())


def test_protected_route_rejects_when_realm_disabled() -> None:
    settings, tenant = _settings(CLINIC_BETA_AUTH_REALM_ENABLED="0")
    assert settings.auth_realm_enabled is False
    with pytest.raises(AuthSettingsError):
        require_usable_auth_realm(settings)

    app = _app(settings)
    # Token is cryptographically valid; realm gate must still fail closed.
    token, _ = issue_access_token(
        settings=settings,
        principal_id=uuid4(),
        tenant_id=__import__("uuid").UUID(tenant),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "auth_realm_unavailable"


def test_protected_route_rejects_production_env_even_with_valid_token() -> None:
    tenant = str(uuid4())
    settings = load_auth_settings(
        {
            "CLINIC_ENV": "production",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": tenant,
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "unit-test-signing-secret-32b-min!!",
            "CLINIC_DATABASE_URL": "postgresql+asyncpg://unused:unused@127.0.0.1/tenant_app",
        }
    )
    app = _app(settings)
    token, _ = issue_access_token(
        settings=settings,
        principal_id=uuid4(),
        tenant_id=__import__("uuid").UUID(tenant),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "auth_realm_unavailable"


def test_protected_route_rejects_valid_token_for_different_tenant() -> None:
    settings, realm = _settings()
    app = _app(settings)
    other_tenant = uuid4()
    token, _ = issue_access_token(
        settings=settings,
        principal_id=uuid4(),
        tenant_id=other_tenant,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"


def test_evaluate_runtime_role_accepts_tp_app_login_only() -> None:
    evaluate_runtime_role(
        RuntimeRoleSnapshot(
            current_user="tp_app_login",
            session_user="tp_app_login",
            rolsuper=False,
            rolbypassrls=False,
            rolname="tp_app_login",
        )
    )
    with pytest.raises(UnsafeDatabaseRoleError):
        evaluate_runtime_role(
            RuntimeRoleSnapshot(
                current_user="tp_migrator_login",
                session_user="tp_migrator_login",
                rolsuper=False,
                rolbypassrls=False,
                rolname="tp_migrator_login",
            )
        )
    with pytest.raises(UnsafeDatabaseRoleError):
        evaluate_runtime_role(
            RuntimeRoleSnapshot(
                current_user="tp_app_login",
                session_user="tp_app_login",
                rolsuper=True,
                rolbypassrls=False,
                rolname="tp_app_login",
            )
        )
    with pytest.raises(UnsafeDatabaseRoleError):
        evaluate_runtime_role(
            RuntimeRoleSnapshot(
                current_user="tp_app_login",
                session_user="tp_app_login",
                rolsuper=False,
                rolbypassrls=True,
                rolname="tp_app_login",
            )
        )


@pytest.mark.asyncio
async def test_record_failed_login_uses_atomic_update_sql() -> None:
    session = MagicMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "person_id": uuid4(),
        "login_identifier": "a@test",
        "normalized_login_identifier": "a@test",
        "password_hash_argon2id": "$argon2id$x",
        "is_active": True,
        "failed_login_attempts": 3,
        "locked_until_utc": None,
    }
    session.execute = AsyncMock(return_value=result)
    repo = SqlUserAccountRepository(session)
    await repo.record_failed_login(
        tenant_id=uuid4(),
        account_id=uuid4(),
        max_failed_attempts=5,
        lockout_minutes=15,
        now=datetime.now(timezone.utc),
    )
    assert session.execute.await_count == 1
    sql = str(session.execute.await_args.args[0])
    assert "failed_login_attempts + 1" in sql
    assert "RETURNING" in sql
    assert "SELECT" not in sql.split("UPDATE", 1)[0]  # no preceding read in this method
