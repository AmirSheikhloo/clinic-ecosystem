"""Task 34 R2 dashboard backend contracts (practitioner, online metrics, review, job_title)."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from clinic_ecosystem.application.auth.service import AuthService
from clinic_ecosystem.infrastructure.auth.access_tokens import issue_access_token
from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
from clinic_ecosystem.infrastructure.demo.builders_appointments import build_appointments
from clinic_ecosystem.infrastructure.demo.builders_catalog import build_catalog
from clinic_ecosystem.infrastructure.demo.builders_people import build_patients, build_staff
from clinic_ecosystem.infrastructure.demo.profiles import MINIMAL
from clinic_ecosystem.infrastructure.persistence.user_accounts import UserAccountRecord
from clinic_ecosystem.presentation.http.app import create_app
from clinic_ecosystem.presentation.http.dependencies import get_auth_service, get_uow
from clinic_ecosystem.presentation.http.overview import FINANCIAL_STATUS_FA


ROOT = Path(__file__).resolve().parents[2]


def _queries_source() -> str:
    return (
        ROOT
        / "src/clinic_ecosystem/infrastructure/persistence/overview_queries.py"
    ).read_text(encoding="utf-8")


def _overview_source() -> str:
    return (
        ROOT / "src/clinic_ecosystem/presentation/http/overview.py"
    ).read_text(encoding="utf-8")


def test_practitioner_name_sql_requires_practitioner_type() -> None:
    src = _queries_source()
    assert "resource_type = 'PRACTITIONER'" in src
    assert "AS practitioner_name" in src
    # overview must not fall back to resource_names[0]
    overview = _overview_source()
    assert 'resources[0] if resources else None' not in overview
    assert 'r.get("practitioner_name")' in overview


def test_online_metric_predicates_use_created_at_and_exclude_holds() -> None:
    src = _queries_source()
    assert "online_bookings_today" in src
    assert "online_unreviewed_count" in src
    assert "a.created_at_utc >= :s" in src
    assert "a.booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')" in src
    assert "a.status = 'CONFIRMED'" in src
    assert "online_booking_reviews" in src
    # Online confirmed counts must not include hold statuses.
    online_block = src[src.index("online_bookings_today") :]
    assert "PENDING_PAYMENT_HOLD" not in online_block
    assert "EXPIRED_HOLD" not in online_block


def test_dashboard_day_allows_online_metric_and_filters() -> None:
    src = _overview_source()
    assert '"online"' in src or "'online'" in src
    assert "online_review" in src
    assert "booking_channel" in src
    assert "DAY_METRICS" in src


def test_financial_persian_labels_code_and_label() -> None:
    assert FINANCIAL_STATUS_FA["UNPAID"] == "پرداخت‌نشده"
    assert FINANCIAL_STATUS_FA["PARTIAL"] == "پرداخت جزئی"
    assert FINANCIAL_STATUS_FA["PAID"] == "تسویه‌شده"
    overview = _overview_source()
    assert "financial_status_code" in overview
    assert "financial_status_label" in overview


def test_builders_drop_family_surnames_and_seed_online_bot_job_titles() -> None:
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    people = build_patients(MINIMAL)
    staff = build_staff(MINIMAL)
    catalog = build_catalog(MINIMAL, now=now)
    appts = build_appointments(
        MINIMAL,
        patients=people.patients,
        catalog=catalog,
        staff=staff.staff,
        receptionist_person_id=staff.staff[0].person_id,
        now_utc=now,
    )
    assert all(not p.last_name.startswith("خانواده") for p in people.persons)
    assert any(s.job_title for s in staff.staff)
    assert any(a.booking_channel == "ONLINE_BOT" for a in appts.appointments)
    assert any(a.booking_channel == "ONLINE_WEB" for a in appts.appointments)
    assert any(a.practitioner_resource_id for a in appts.appointments)


@pytest.mark.asyncio
async def test_review_upsert_idempotent() -> None:
    from clinic_ecosystem.infrastructure.persistence.dashboard_ops import SqlDashboardOps

    session = MagicMock()
    ops = SqlDashboardOps(session)
    tenant_id = uuid4()
    appt_id = uuid4()
    reviewer = uuid4()
    review_id = uuid4()
    now = datetime.now(timezone.utc)

    existing = {
        "id": review_id,
        "appointment_id": appt_id,
        "reviewed_by_user_id": reviewer,
        "reviewed_at_utc": now,
        "note": None,
    }
    ops.get_review = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    row, created = await ops.upsert_review(
        tenant_id=tenant_id,
        appointment_id=appt_id,
        reviewer_user_id=reviewer,
        now=now,
    )
    assert created is False
    assert row["id"] == review_id
    session.execute.assert_not_called()


def test_me_includes_job_title(monkeypatch) -> None:
    from clinic_ecosystem.presentation.http import auth as auth_mod

    class _FakePerms:
        def __init__(self, session):
            pass

        async def effective_permissions(self, **kwargs):
            return {"BETA01B_APPOINTMENTS_LIST"}

        async def governance_roles(self, **kwargs):
            return {"CLINIC_OWNER"}

    class _FakeAdmin:
        def __init__(self, session):
            pass

        async def person_display(self, **kwargs):
            return ("رضا", "مالکی")

        async def staff_job_title(self, **kwargs):
            return "مالک کلینیک"

    monkeypatch.setattr(auth_mod, "SqlPermissionService", _FakePerms)
    monkeypatch.setattr(auth_mod, "SqlAccessAdmin", _FakeAdmin)

    tenant_id = uuid4()
    account_id = uuid4()
    settings = load_auth_settings(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(tenant_id),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "unit-test-signing-secret-32b-min!!",
            "CLINIC_DATABASE_URL": "postgresql+asyncpg://unused:unused@127.0.0.1/tenant_app",
        }
    )
    engine = MagicMock(name="async_engine")
    app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
    account = UserAccountRecord(
        id=account_id,
        tenant_id=tenant_id,
        person_id=uuid4(),
        login_identifier="owner@beta02.test",
        normalized_login_identifier="owner@beta02.test",
        password_hash_argon2id="$argon2id$v=19$m=65536,t=3,p=2$unittest",
        is_active=True,
        failed_login_attempts=0,
        locked_until_utc=None,
    )
    token, claims = issue_access_token(
        settings=settings, principal_id=account_id, tenant_id=tenant_id
    )
    mock_auth = MagicMock(spec=AuthService)
    mock_auth.load_active_account = AsyncMock(return_value=account)

    async def _uow_dep():
        yield MagicMock()

    app.dependency_overrides[get_uow] = _uow_dep
    app.dependency_overrides[get_auth_service] = lambda: mock_auth

    with TestClient(app) as client:
        me = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert me.status_code == 200
    body = me.json()
    assert body["first_name"] == "رضا"
    assert body["job_title"] == "مالک کلینیک"


def test_dashboard_r2_sql_and_apply_hook_present() -> None:
    sql = (
        ROOT
        / "docs/validation/d010/d09_extracted/proposed_dashboard_r2.sql"
    ).read_text(encoding="utf-8")
    assert "ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS job_title" in sql
    assert "online_booking_reviews" in sql
    assert "clinic_staff_notifications" in sql
    assert "clinic_notification_reads" in sql
    apply_src = (
        ROOT / "src/clinic_ecosystem/infrastructure/ops_schema/apply.py"
    ).read_text(encoding="utf-8")
    assert "apply_dashboard_r2_schema" in apply_src
    tree = ast.parse(apply_src)
    names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "apply_dashboard_r2_schema" in names


def test_preview_runtime_dir_used() -> None:
    src = (ROOT / "scripts/start_preview_stack.py").read_text(encoding="utf-8")
    assert "artifact_dir=runtime" in src
    assert "legacy" not in src
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "P03_HANDOFF/beta_panel_preview/runtime/" in gitignore
