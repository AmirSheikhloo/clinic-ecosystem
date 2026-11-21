"""Unit tests for service-requirements existence checks and search escaping."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.infrastructure.persistence.patients import SqlPatientRepository
from clinic_ecosystem.infrastructure.persistence.services_catalog import ServiceCatalogItem
from clinic_ecosystem.infrastructure.persistence.user_accounts import UserAccountRecord
from clinic_ecosystem.presentation.http import resources as resources_mod
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
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


@pytest.fixture
def app_principal():
    tenant_id = uuid4()
    settings = _settings(tenant_id)
    account_id = uuid4()
    account = UserAccountRecord(
        id=account_id,
        tenant_id=tenant_id,
        person_id=uuid4(),
        login_identifier="r@test",
        normalized_login_identifier="r@test",
        password_hash_argon2id="$argon2id$v=19$m=65536,t=3,p=2$unittest",
        is_active=True,
        failed_login_attempts=0,
        locked_until_utc=None,
    )
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )
    engine = MagicMock(name="async_engine")
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    principal = AuthenticatedPrincipal(claims=claims, account=account)

    async def _uow_dep():
        uow = MagicMock()
        uow.session = MagicMock()
        yield uow

    async def _principal_dep():
        return principal

    app.dependency_overrides[get_uow] = _uow_dep
    app.dependency_overrides[get_authenticated_principal] = _principal_dep
    return app, principal, token


@pytest.mark.asyncio
async def test_requirements_missing_service_404(app_principal, monkeypatch) -> None:
    app, _, token = app_principal

    async def allow(*args, **kwargs):
        return None

    monkeypatch.setattr(resources_mod, "require_permission", allow)
    monkeypatch.setattr(
        resources_mod.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=None),
    )
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/catalog/services/{uuid4()}/resource-requirements",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "service_not_found"


@pytest.mark.asyncio
async def test_requirements_inactive_service_400(app_principal, monkeypatch) -> None:
    app, _, token = app_principal
    sid = uuid4()

    async def allow(*args, **kwargs):
        return None

    monkeypatch.setattr(resources_mod, "require_permission", allow)
    monkeypatch.setattr(
        resources_mod.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(
            return_value=ServiceCatalogItem(
                id=sid,
                service_code="X",
                service_name="Inactive",
                default_duration_minutes=30,
                default_price_irr=1,
                is_active=False,
            )
        ),
    )
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/catalog/services/{sid}/resource-requirements",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "service_inactive"


@pytest.mark.asyncio
async def test_requirements_empty_list_for_active_service(app_principal, monkeypatch) -> None:
    app, _, token = app_principal
    sid = uuid4()

    async def allow(*args, **kwargs):
        return None

    monkeypatch.setattr(resources_mod, "require_permission", allow)
    monkeypatch.setattr(
        resources_mod.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(
            return_value=ServiceCatalogItem(
                id=sid,
                service_code="X",
                service_name="Active",
                default_duration_minutes=30,
                default_price_irr=1,
                is_active=True,
            )
        ),
    )
    monkeypatch.setattr(
        resources_mod.SqlResourcesCatalogRepository,
        "list_requirements_for_service",
        AsyncMock(return_value=[]),
    )
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/catalog/services/{sid}/resource-requirements",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_search_escapes_like_metacharacters() -> None:
    # Ensure the SQL text includes ESCAPE and the bound pattern escapes % _
    captured: dict = {}

    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class FakeSession:
        async def execute(self, statement, params):
            captured["sql"] = str(statement)
            captured["params"] = params
            return FakeResult()

    repo = SqlPatientRepository(FakeSession())  # type: ignore[arg-type]
    await repo.search_by_name(tenant_id=uuid4(), query="100%_sure")
    assert "ESCAPE" in captured["sql"].upper()
    assert captured["params"]["pattern"] == r"%100\%\_sure%"
