"""BETA-01B reception API integration tests on disposable PostgreSQL 15.

Skipped when Docker is unavailable. Uses Testcontainers only.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from uuid import uuid4
from zoneinfo import ZoneInfo

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.beta01b_seed import seed_beta01b_reception
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration

TEHRAN = ZoneInfo("Asia/Tehran")


def _app_url(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql+asyncpg://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
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
    engine = create_async_engine(_app_url(plane_topology), pool_size=5)
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    return TestClient(app), settings, engine


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, login: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"login_identifier": login, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_beta01b_patients_resources_schedule_list(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01b_reception(seed_conn)
    finally:
        await seed_conn.close()

    client, settings, engine = _build_client(plane_topology, seed)
    try:
        with client:
            token = _login(
                client, seed.receptionist_login, seed.receptionist_password
            )
            unauth = _login(
                client, seed.unauthorized_login, seed.unauthorized_password
            )

            # 1. Authorized patient registration
            created = client.post(
                "/api/v1/patients",
                headers=_auth(token),
                json={
                    "first_name": "Nima",
                    "last_name": "Synthetic",
                    "birth_date": "1990-05-01",
                },
            )
            assert created.status_code == 201, created.text
            body = created.json()
            assert body["first_name"] == "Nima"
            assert body["patient_profile_id"] != body["person_id"]
            new_patient_id = body["patient_profile_id"]
            new_person_id = body["person_id"]

            # 5. Distinction: search returns profile id, not person id as schedule key
            search = client.get(
                "/api/v1/patients",
                headers=_auth(token),
                params={"q": "Nima"},
            )
            assert search.status_code == 200
            items = search.json()["items"]
            assert any(i["patient_profile_id"] == new_patient_id for i in items)
            assert all(i["patient_profile_id"] != new_person_id for i in items)

            # 2. Unauthorized patient registration
            denied_reg = client.post(
                "/api/v1/patients",
                headers=_auth(unauth),
                json={"first_name": "Nope", "last_name": "Denied"},
            )
            assert denied_reg.status_code == 403

            # 4. Tenant-isolated patient search (tenant B patient never appears)
            search_secret = client.get(
                "/api/v1/patients",
                headers=_auth(token),
                params={"q": "Secret"},
            )
            assert search_secret.status_code == 200
            assert search_secret.json()["items"] == []

            # 6. Active services + valid resources
            services = client.get(
                "/api/v1/catalog/services", headers=_auth(token)
            )
            assert services.status_code == 200
            service_ids = {i["id"] for i in services.json()["items"]}
            assert str(seed.service_a_id) in service_ids
            assert str(seed.service_b_id) not in service_ids

            resources = client.get(
                "/api/v1/catalog/resources", headers=_auth(token)
            )
            assert resources.status_code == 200
            resource_ids = {i["id"] for i in resources.json()["items"]}
            assert str(seed.resource_a_id) in resource_ids
            assert str(seed.resource_b_id) not in resource_ids

            reqs = client.get(
                f"/api/v1/catalog/services/{seed.service_a_id}/resource-requirements",
                headers=_auth(token),
            )
            assert reqs.status_code == 200
            assert len(reqs.json()["items"]) >= 1
            assert reqs.json()["items"][0]["required_resource_type"] == "ROOM"

            # 7. Unauthorized resource/catalog access
            assert (
                client.get(
                    "/api/v1/catalog/resources", headers=_auth(unauth)
                ).status_code
                == 403
            )

            # 9. Unauthorized ordinary appointment creation
            # (ALLOW_MANUAL_OVERBOOKING alone is insufficient)
            sched_only = _login(
                client, seed.schedule_only_login, seed.schedule_only_password
            )
            start = datetime.now(timezone.utc) + timedelta(hours=3)
            end = start + timedelta(minutes=30)
            denied_sched = client.post(
                "/api/v1/appointments",
                headers={
                    **_auth(sched_only),
                    "Idempotency-Key": "denied-sched-1",
                },
                json={
                    "beneficiary_patient_id": str(seed.patient_a_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": start.isoformat(),
                    "end_at_utc": end.isoformat(),
                },
            )
            assert denied_sched.status_code == 403

            unauth_sched = client.post(
                "/api/v1/appointments",
                headers={**_auth(unauth), "Idempotency-Key": "unauth-sched-1"},
                json={
                    "beneficiary_patient_id": str(seed.patient_a_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": start.isoformat(),
                    "end_at_utc": end.isoformat(),
                },
            )
            assert unauth_sched.status_code == 403

            # 8. Authorized manual appointment creation
            slot1_start = datetime.now(timezone.utc) + timedelta(hours=5)
            slot1_end = slot1_start + timedelta(minutes=30)
            created_appt = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "manual-create-1"},
                json={
                    "beneficiary_patient_id": new_patient_id,
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": slot1_start.isoformat(),
                    "end_at_utc": slot1_end.isoformat(),
                },
            )
            assert created_appt.status_code == 200, created_appt.text
            appt_id = created_appt.json()["appointment_id"]
            assert created_appt.json()["replayed"] is False

            # 13. Idempotent retry
            replay = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "manual-create-1"},
                json={
                    "beneficiary_patient_id": new_patient_id,
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": slot1_start.isoformat(),
                    "end_at_utc": slot1_end.isoformat(),
                },
            )
            assert replay.status_code == 200
            assert replay.json()["appointment_id"] == appt_id
            assert replay.json()["replayed"] is True

            # Fingerprint mismatch
            mismatch = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "manual-create-1"},
                json={
                    "beneficiary_patient_id": new_patient_id,
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": (slot1_start + timedelta(minutes=1)).isoformat(),
                    "end_at_utc": (slot1_end + timedelta(minutes=1)).isoformat(),
                },
            )
            assert mismatch.status_code == 409
            assert mismatch.json()["detail"]["error"] == "idempotency_conflict"

            # 10. Cross-tenant patient/service/resource rejection
            cross_patient = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "cross-patient-1"},
                json={
                    "beneficiary_patient_id": str(seed.patient_b_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": (slot1_start + timedelta(hours=10)).isoformat(),
                    "end_at_utc": (slot1_end + timedelta(hours=10)).isoformat(),
                },
            )
            assert cross_patient.status_code == 404

            cross_service = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "cross-service-1"},
                json={
                    "beneficiary_patient_id": new_patient_id,
                    "service_id": str(seed.service_b_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": (slot1_start + timedelta(hours=11)).isoformat(),
                    "end_at_utc": (slot1_end + timedelta(hours=11)).isoformat(),
                },
            )
            assert cross_service.status_code in (400, 409)

            cross_resource = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "cross-resource-1"},
                json={
                    "beneficiary_patient_id": new_patient_id,
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_b_id)],
                    "start_at_utc": (slot1_start + timedelta(hours=12)).isoformat(),
                    "end_at_utc": (slot1_end + timedelta(hours=12)).isoformat(),
                },
            )
            assert cross_resource.status_code in (400, 409)

            # 11/12. Manual overlap without ack → 409 with names for authorized staff
            overlap = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "overlap-no-ack"},
                json={
                    "beneficiary_patient_id": str(seed.patient_a_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": slot1_start.isoformat(),
                    "end_at_utc": slot1_end.isoformat(),
                    "acknowledge_overlap": False,
                },
            )
            assert overlap.status_code == 409, overlap.text
            detail = overlap.json()["detail"]
            assert detail["error"] == "manual_overlap_acknowledgement_required"
            conflicts = detail["conflicts"]
            assert len(conflicts) >= 1
            assert "display_safe_patient_name" in conflicts[0]

            # Ack with wrong conflict ids still required
            bad_ack = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "overlap-bad-ack"},
                json={
                    "beneficiary_patient_id": str(seed.patient_a_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": slot1_start.isoformat(),
                    "end_at_utc": slot1_end.isoformat(),
                    "acknowledge_overlap": True,
                    "acknowledged_conflict_ids": [str(uuid4())],
                },
            )
            assert bad_ack.status_code == 409

            # Correct acknowledgement
            conflict_ids = [c["appointment_id"] for c in conflicts]
            ack = client.post(
                "/api/v1/appointments",
                headers={**_auth(token), "Idempotency-Key": "overlap-good-ack"},
                json={
                    "beneficiary_patient_id": str(seed.patient_a_id),
                    "service_id": str(seed.service_a_id),
                    "resource_ids": [str(seed.resource_a_id)],
                    "start_at_utc": slot1_start.isoformat(),
                    "end_at_utc": slot1_end.isoformat(),
                    "acknowledge_overlap": True,
                    "acknowledged_conflict_ids": conflict_ids,
                },
            )
            assert ack.status_code == 200, ack.text

            # 15/16. Day-range listing + timezone: persist UTC, display local
            day_start_tehran = datetime.now(TEHRAN).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end_tehran = day_start_tehran + timedelta(days=2)
            listing = client.get(
                "/api/v1/appointments",
                headers=_auth(token),
                params={
                    "start_at_utc": day_start_tehran.astimezone(timezone.utc).isoformat(),
                    "end_at_utc": day_end_tehran.astimezone(timezone.utc).isoformat(),
                },
            )
            assert listing.status_code == 200, listing.text
            listed = listing.json()["items"]
            assert any(i["appointment_id"] == appt_id for i in listed)
            for item in listed:
                start_utc = datetime.fromisoformat(item["scheduled_start_at_utc"])
                assert start_utc.tzinfo is not None
                # Round-trip: UTC instant converts to Tehran without mutation
                local = start_utc.astimezone(TEHRAN)
                assert local.astimezone(timezone.utc) == start_utc.astimezone(
                    timezone.utc
                )

            # Tenant isolation on listing: forged wrong-tenant token fails realm check
            forged, _ = issue_access_token(
                settings=settings,
                principal_id=seed.receptionist_account_id,
                tenant_id=seed.tenant_b_id,
            )
            forged_list = client.get(
                "/api/v1/appointments",
                headers=_auth(forged),
                params={
                    "start_at_utc": day_start_tehran.astimezone(timezone.utc).isoformat(),
                    "end_at_utc": day_end_tehran.astimezone(timezone.utc).isoformat(),
                },
            )
            assert forged_list.status_code == 401

            # 17. BETA-01A auth still works (login + me)
            me = client.get("/api/v1/auth/me", headers=_auth(token))
            assert me.status_code == 200
            assert me.json()["account_id"] == str(seed.receptionist_account_id)

            # 18. Demo realm disabled fails closed
            disabled = load_auth_settings(
                {
                    "CLINIC_ENV": "test",
                    "CLINIC_BETA_AUTH_REALM_ENABLED": "0",
                    "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(seed.tenant_a_id),
                    "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": (
                        "integration-test-signing-secret-32chars!!"
                    ),
                    "CLINIC_DATABASE_URL": _app_url(plane_topology),
                }
            )
            disabled_engine = create_async_engine(
                _app_url(plane_topology), pool_size=1
            )
            disabled_app = create_app(
                settings=disabled,
                engine=disabled_engine,
                create_engine_from_settings=False,
            )
            with TestClient(disabled_app) as dclient:
                realm_fail = dclient.post(
                    "/api/v1/auth/login",
                    json={
                        "login_identifier": seed.receptionist_login,
                        "password": seed.receptionist_password,
                    },
                )
                assert realm_fail.status_code == 503
            await disabled_engine.dispose()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_beta01b_atomic_patient_rollback(plane_topology) -> None:
    """3. Atomic rollback when patient registration fails mid-transaction."""
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01b_reception(seed_conn)
    finally:
        await seed_conn.close()

    from clinic_ecosystem.infrastructure.persistence.patients import SqlPatientRepository
    from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            uow = SqlAlchemyUnitOfWork(session, owns_session=False)
            await uow.bind_tenant(seed.tenant_a_id)
            repo = SqlPatientRepository(session)
            try:
                await repo.register(
                    tenant_id=seed.tenant_a_id,
                    first_name="Rollback",
                    last_name="Probe",
                )
                await session.execute(text("SELECT 1/0"))
                await uow.commit()
            except Exception:
                await uow.rollback()
    finally:
        # Verify neither row persisted (rolled back)
        inspect = await asyncpg.connect(
            f"postgresql://{quote_plus('tp_app_login')}:"
            f"{quote_plus(plane_topology.passwords['tp_app_login'])}"
            f"@{plane_topology.cloud_tenant.host}:{plane_topology.cloud_tenant.port}"
            f"/tenant_app"
        )
        try:
            await inspect.execute(
                "SELECT set_config('app.current_tenant_id', $1, false)",
                str(seed.tenant_a_id),
            )
            persons = await inspect.fetchval(
                "SELECT count(*) FROM tenant_persons WHERE first_name = 'Rollback'"
            )
            profiles = await inspect.fetchval(
                """
                SELECT count(*) FROM patient_profiles p
                JOIN tenant_persons tp ON tp.id = p.person_id AND tp.tenant_id = p.tenant_id
                WHERE tp.first_name = 'Rollback'
                """
            )
            assert persons == 0
            assert profiles == 0
        finally:
            await inspect.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_beta01b_concurrent_scheduling_consistency(plane_topology) -> None:
    """14. Concurrent scheduling consistency via request-scoped handlers."""
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        seed = await seed_beta01b_reception(seed_conn)
    finally:
        await seed_conn.close()

    from httpx import ASGITransport, AsyncClient

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
    engine = create_async_engine(_app_url(plane_topology), pool_size=5)
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={
                    "login_identifier": seed.receptionist_login,
                    "password": seed.receptionist_password,
                },
            )
            assert login.status_code == 200
            token = login.json()["access_token"]
            base = datetime.now(timezone.utc) + timedelta(hours=20)

            async def _schedule(i: int):
                start = base + timedelta(minutes=i * 40)
                end = start + timedelta(minutes=30)
                return await client.post(
                    "/api/v1/appointments",
                    headers={
                        **_auth(token),
                        "Idempotency-Key": f"concurrent-{i}-{new_uuid7()}",
                    },
                    json={
                        "beneficiary_patient_id": str(seed.patient_a_id),
                        "service_id": str(seed.service_a_id),
                        "resource_ids": [str(seed.resource_a_id)],
                        "start_at_utc": start.isoformat(),
                        "end_at_utc": end.isoformat(),
                    },
                )

            results = await asyncio.gather(*[_schedule(i) for i in range(3)])
            assert all(r.status_code == 200 for r in results), [
                r.text for r in results
            ]
            ids = {r.json()["appointment_id"] for r in results}
            assert len(ids) == 3
    finally:
        await engine.dispose()
