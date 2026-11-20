"""BETA-01B HTTP unit tests with dependency overrides (no PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.infrastructure.persistence.appointment_queries import (
    AppointmentListItem,
)
from clinic_ecosystem.infrastructure.persistence.patients import PatientRecord
from clinic_ecosystem.infrastructure.persistence.resources_catalog import (
    ResourceRecord,
    ServiceRequirementRecord,
)
from clinic_ecosystem.infrastructure.persistence.user_accounts import UserAccountRecord
from clinic_ecosystem.presentation.http import appointments as appointments_mod
from clinic_ecosystem.presentation.http import patients as patients_mod
from clinic_ecosystem.presentation.http import resources as resources_mod
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_engine,
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


def _account(*, tenant_id, account_id):
    return UserAccountRecord(
        id=account_id,
        tenant_id=tenant_id,
        person_id=uuid4(),
        login_identifier="receptionist@beta01b.test",
        normalized_login_identifier="receptionist@beta01b.test",
        password_hash_argon2id="$argon2id$v=19$m=65536,t=3,p=2$unittest",
        is_active=True,
        failed_login_attempts=0,
        locked_until_utc=None,
    )


@pytest.fixture
def app_principal():
    tenant_id = uuid4()
    settings = _settings(tenant_id)
    account_id = uuid4()
    account = _account(tenant_id=tenant_id, account_id=account_id)
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )
    engine = MagicMock(name="async_engine")
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    principal = AuthenticatedPrincipal(claims=claims, account=account)

    async def _uow_dep():
        uow = MagicMock()
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        uow.session = MagicMock()
        yield uow

    async def _principal_dep():
        return principal

    app.dependency_overrides[get_uow] = _uow_dep
    app.dependency_overrides[get_authenticated_principal] = _principal_dep
    app.dependency_overrides[get_engine] = lambda: engine
    return app, principal, token


def test_patient_register_requires_permission(app_principal) -> None:
    app, _, token = app_principal

    async def deny(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "permission_denied", "message": "Permission denied"},
        )

    original = patients_mod.require_permission
    patients_mod.require_permission = deny
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/patients",
                headers={"Authorization": f"Bearer {token}"},
                json={"first_name": "A", "last_name": "B"},
            )
        assert response.status_code == 403
    finally:
        patients_mod.require_permission = original


def test_patient_register_success(app_principal) -> None:
    app, principal, token = app_principal
    patient_id = uuid4()
    person_id = uuid4()

    async def allow(*args, **kwargs):
        return None

    class FakeRepo:
        def __init__(self, session):
            pass

        async def register(self, **kwargs):
            return PatientRecord(
                patient_profile_id=patient_id,
                person_id=person_id,
                tenant_id=principal.claims.tenant_id,
                first_name=kwargs["first_name"],
                last_name=kwargs["last_name"],
                birth_date=kwargs.get("birth_date"),
                is_active=True,
            )

    original_perm = patients_mod.require_permission
    original_repo = patients_mod.SqlPatientRepository
    patients_mod.require_permission = allow
    patients_mod.SqlPatientRepository = FakeRepo
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/patients",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "first_name": "Nima",
                    "last_name": "Test",
                    "birth_date": "1991-01-02",
                },
            )
        assert response.status_code == 201
        body = response.json()
        assert body["patient_profile_id"] == str(patient_id)
        assert body["person_id"] == str(person_id)
        assert body["patient_profile_id"] != body["person_id"]
        assert body["birth_date"] == "1991-01-02"
    finally:
        patients_mod.require_permission = original_perm
        patients_mod.SqlPatientRepository = original_repo


def test_resources_list_success(app_principal) -> None:
    app, _, token = app_principal
    rid = uuid4()

    async def allow(*args, **kwargs):
        return None

    class FakeRepo:
        def __init__(self, session):
            pass

        async def list_active_resources(self, **kwargs):
            return [
                ResourceRecord(
                    id=rid,
                    resource_type="ROOM",
                    resource_name="Room 1",
                    is_active=True,
                )
            ]

        async def list_requirements_for_service(self, **kwargs):
            return [
                ServiceRequirementRecord(
                    id=uuid4(),
                    service_id=kwargs["service_id"],
                    requirement_group="primary",
                    required_resource_type="ROOM",
                    specific_resource_id=None,
                    quantity_required=1,
                )
            ]

    original_perm = resources_mod.require_permission
    original_repo = resources_mod.SqlResourcesCatalogRepository
    resources_mod.require_permission = allow
    resources_mod.SqlResourcesCatalogRepository = FakeRepo
    try:
        with TestClient(app) as client:
            resources = client.get(
                "/api/v1/catalog/resources",
                headers={"Authorization": f"Bearer {token}"},
            )
            reqs = client.get(
                f"/api/v1/catalog/services/{uuid4()}/resource-requirements",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resources.status_code == 200
        assert resources.json()["items"][0]["id"] == str(rid)
        assert reqs.status_code == 200
        assert reqs.json()["items"][0]["required_resource_type"] == "ROOM"
    finally:
        resources_mod.require_permission = original_perm
        resources_mod.SqlResourcesCatalogRepository = original_repo


def test_appointment_list_success(app_principal) -> None:
    app, principal, token = app_principal
    appt_id = uuid4()
    start = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 20, 8, 30, tzinfo=timezone.utc)

    async def allow(*args, **kwargs):
        return None

    class FakeRepo:
        def __init__(self, session):
            pass

        async def list_in_range(self, **kwargs):
            return [
                AppointmentListItem(
                    appointment_id=appt_id,
                    patient_profile_id=uuid4(),
                    patient_first_name="Pat",
                    patient_last_name="Alpha",
                    service_id=uuid4(),
                    service_name="Consult",
                    status="CONFIRMED",
                    booking_channel="MANUAL_STAFF",
                    capacity_pool="MANUAL",
                    scheduled_start_at_utc=start,
                    scheduled_end_at_utc=end,
                )
            ]

    original_perm = appointments_mod.require_permission
    original_repo = appointments_mod.SqlAppointmentQueryRepository
    appointments_mod.require_permission = allow
    appointments_mod.SqlAppointmentQueryRepository = FakeRepo
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/appointments",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "start_at_utc": "2026-11-20T00:00:00+00:00",
                    "end_at_utc": "2026-11-21T00:00:00+00:00",
                },
            )
        assert response.status_code == 200
        assert response.json()["items"][0]["appointment_id"] == str(appt_id)
    finally:
        appointments_mod.require_permission = original_perm
        appointments_mod.SqlAppointmentQueryRepository = original_repo


def test_schedule_rejects_non_manual_channel(app_principal) -> None:
    app, _, token = app_principal

    async def allow(*args, **kwargs):
        return None

    original = appointments_mod.require_permission
    appointments_mod.require_permission = allow
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/appointments",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": "x",
                },
                json={
                    "beneficiary_patient_id": str(uuid4()),
                    "service_id": str(uuid4()),
                    "resource_ids": [str(uuid4())],
                    "start_at_utc": "2026-11-20T10:00:00+00:00",
                    "end_at_utc": "2026-11-20T10:30:00+00:00",
                    "booking_channel": "ONLINE_WEB",
                    "capacity_pool": "ONLINE",
                },
            )
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "invalid_booking_mode"
    finally:
        appointments_mod.require_permission = original
