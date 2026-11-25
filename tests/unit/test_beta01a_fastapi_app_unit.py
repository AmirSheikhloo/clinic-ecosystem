"""FastAPI unit tests with dependency overrides (no PostgreSQL / Docker)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from clinic_ecosystem.application.auth.exceptions import InvalidCredentials
from clinic_ecosystem.application.auth.service import AuthService, LoginResult
from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.infrastructure.persistence.services_catalog import ServiceCatalogItem
from clinic_ecosystem.infrastructure.persistence.user_accounts import UserAccountRecord
from clinic_ecosystem.presentation.http import catalog as catalog_mod
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_auth_service,
    get_authenticated_principal,
    get_uow,
)


def _settings(tenant_id=None):
    tid = tenant_id or uuid4()
    return load_auth_settings(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(tid),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "unit-test-signing-secret-32b-min!!",
            "CLINIC_DATABASE_URL": "postgresql+asyncpg://unused:unused@127.0.0.1/tenant_app",
        }
    )


def _account(*, tenant_id, account_id, login="receptionist@beta01a.test"):
    return UserAccountRecord(
        id=account_id,
        tenant_id=tenant_id,
        person_id=uuid4(),
        login_identifier=login,
        normalized_login_identifier=login,
        password_hash_argon2id="$argon2id$v=19$m=65536,t=3,p=2$unittest",
        is_active=True,
        failed_login_attempts=0,
        locked_until_utc=None,
    )


@pytest.fixture
def app_and_settings():
    tenant_id = uuid4()
    settings = _settings(tenant_id)
    engine = MagicMock(name="async_engine")
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    return app, settings, tenant_id


def test_health_endpoint(app_and_settings) -> None:
    app, _, _ = app_and_settings

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success_and_me(app_and_settings, monkeypatch) -> None:
    from clinic_ecosystem.presentation.http import auth as auth_mod

    class _FakePerms:
        def __init__(self, session):
            pass

        async def effective_permissions(self, **kwargs):
            return {"BETA02_STAFF_VIEW", "BETA01B_PATIENTS_SEARCH"}

        async def governance_roles(self, **kwargs):
            return {"RECEPTIONIST"}

    class _FakeAdmin:
        def __init__(self, session):
            pass

        async def person_display(self, **kwargs):
            return ("Rita", "Reception")

    monkeypatch.setattr(auth_mod, "SqlPermissionService", _FakePerms)
    monkeypatch.setattr(auth_mod, "SqlAccessAdmin", _FakeAdmin)
    app, settings, tenant_id = app_and_settings
    account_id = uuid4()
    account = _account(tenant_id=tenant_id, account_id=account_id)
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )

    mock_auth = MagicMock(spec=AuthService)
    mock_auth.login = AsyncMock(
        return_value=LoginResult(
            access_token=token,
            token_type="Bearer",
            expires_in=settings.access_token_ttl_seconds,
            claims=claims,
            account=account,
        )
    )
    mock_auth.load_active_account = AsyncMock(return_value=account)

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    app.dependency_overrides[get_auth_service] = lambda: mock_auth

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"login_identifier": account.login_identifier, "password": "secret"},
        )
        assert login.status_code == 200
        body = login.json()
        assert body["access_token"] == token
        assert body["account_id"] == str(account_id)
        assert body["tenant_id"] == str(tenant_id)
        assert "password" not in body

        me = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 200
        assert me.json()["login_identifier"] == account.login_identifier
        assert me.json()["permissions"] == ["BETA01B_PATIENTS_SEARCH", "BETA02_STAFF_VIEW"]
        assert me.json()["governance_roles"] == ["RECEPTIONIST"]
        assert me.json()["first_name"] == "Rita"


def test_login_invalid_credentials_generic(app_and_settings) -> None:
    app, _, _ = app_and_settings
    mock_auth = MagicMock(spec=AuthService)
    mock_auth.login = AsyncMock(side_effect=InvalidCredentials())

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    app.dependency_overrides[get_auth_service] = lambda: mock_auth

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"login_identifier": "x@test", "password": "bad"},
        )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"


def test_protected_routes_reject_missing_auth(app_and_settings) -> None:
    app, _, _ = app_and_settings

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    with TestClient(app) as client:
        me = client.get("/api/v1/auth/me")
        services = client.get("/api/v1/catalog/services")
    assert me.status_code == 401
    assert services.status_code == 401


def test_expired_token_rejected_on_me(app_and_settings) -> None:
    app, settings, tenant_id = app_and_settings
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token, _ = issue_access_token(
        settings=settings,
        principal_id=uuid4(),
        tenant_id=tenant_id,
        now=past,
    )

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"


def test_catalog_requires_permission(app_and_settings) -> None:
    app, settings, tenant_id = app_and_settings
    account_id = uuid4()
    account = _account(tenant_id=tenant_id, account_id=account_id)
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )
    principal = AuthenticatedPrincipal(claims=claims, account=account)

    async def _principal():
        return principal

    async def _uow_dep():
        yield MagicMock()

    async def deny_permission(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "permission_denied", "message": "Permission denied"},
        )

    original = catalog_mod.require_permission
    catalog_mod.require_permission = deny_permission
    app.dependency_overrides[get_authenticated_principal] = _principal
    app.dependency_overrides[get_uow] = _uow_dep
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/catalog/services",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "permission_denied"
    finally:
        catalog_mod.require_permission = original


def test_catalog_lists_tenant_items(app_and_settings) -> None:
    app, settings, tenant_id = app_and_settings
    account_id = uuid4()
    account = _account(tenant_id=tenant_id, account_id=account_id)
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )
    principal = AuthenticatedPrincipal(claims=claims, account=account)
    service_id = uuid4()

    async def _principal():
        return principal

    async def _uow_dep():
        yield MagicMock()

    async def allow_permission(*args, **kwargs):
        return None

    class FakeRepo:
        def __init__(self, session) -> None:
            pass

        async def list_active_services(self, *, tenant_id):
            assert tenant_id == principal.claims.tenant_id
            return [
                ServiceCatalogItem(
                    id=service_id,
                    service_code="CONSULT",
                    service_name="Consultation",
                    default_duration_minutes=30,
                    default_price_irr=1000,
                    is_active=True,
                )
            ]

    original_perm = catalog_mod.require_permission
    original_repo = catalog_mod.SqlServicesCatalogRepository
    catalog_mod.require_permission = allow_permission
    catalog_mod.SqlServicesCatalogRepository = FakeRepo
    app.dependency_overrides[get_authenticated_principal] = _principal
    app.dependency_overrides[get_uow] = _uow_dep
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/catalog/services",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["id"] == str(service_id)
        assert payload["items"][0]["service_name"] == "Consultation"
    finally:
        catalog_mod.require_permission = original_perm
        catalog_mod.SqlServicesCatalogRepository = original_repo
