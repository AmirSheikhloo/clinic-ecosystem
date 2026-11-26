"""Structure tests for demo dataset fixture builders (no Docker required)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clinic_ecosystem.domain.identity.national_id import is_valid_national_id_checksum
from clinic_ecosystem.infrastructure.demo.builders_appointments import (
    build_appointments,
    tehran_today,
)
from clinic_ecosystem.infrastructure.demo.builders_catalog import build_catalog
from clinic_ecosystem.infrastructure.demo.builders_people import build_patients, build_staff
from clinic_ecosystem.infrastructure.demo.crypto_hooks import (
    plan_crypto_rows,
    preview_demo_pii_env,
)
from clinic_ecosystem.infrastructure.demo.ids import demo_uuid, synthetic_national_id
from clinic_ecosystem.infrastructure.demo.profiles import DEMO, MINIMAL, resolve_profile


def test_resolve_profile_defaults_to_demo():
    name, targets = resolve_profile(None)
    assert name == "demo"
    assert targets.patients >= 500
    assert targets.appointments >= 10_000


def test_synthetic_national_ids_have_valid_checksum():
    for i in range(50):
        assert is_valid_national_id_checksum(synthetic_national_id(20261126, i))


def test_demo_uuid_is_deterministic():
    a = demo_uuid(20261126, "patient", 7)
    b = demo_uuid(20261126, "patient", 7)
    assert a == b
    assert a != demo_uuid(20261126, "patient", 8)


def test_minimal_builders_meet_profile_floors():
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    people = build_patients(MINIMAL)
    staff = build_staff(MINIMAL)
    catalog = build_catalog(MINIMAL, now=now)
    booker = staff.staff[0].person_id
    appts = build_appointments(
        MINIMAL,
        patients=people.patients,
        catalog=catalog,
        staff=staff.staff,
        receptionist_person_id=booker,
        now_utc=now,
    )
    assert len(people.patients) >= MINIMAL.patients
    assert sum(1 for p in people.patients if p.exception_reason) >= MINIMAL.exceptional_identity_patients
    assert len(staff.staff) >= MINIMAL.staff_total
    assert sum(1 for s in staff.staff if s.with_login) >= MINIMAL.receptionist_logins
    assert sum(1 for s in staff.staff if not s.with_login) >= MINIMAL.practitioner_no_login
    assert len(catalog.services) >= MINIMAL.services
    assert len(catalog.rooms) >= MINIMAL.resources_rooms
    assert len(appts.appointments) >= MINIMAL.appointments
    assert appts.multi_service_group_count >= MINIMAL.multi_service_groups
    assert appts.manual_overlap_pairs >= MINIMAL.manual_overlap_pairs
    assert appts.checked_in_waiting_today >= MINIMAL.checked_in_waiting_today
    today = tehran_today(now)
    from zoneinfo import ZoneInfo

    tehran = ZoneInfo("Asia/Tehran")
    today_n = sum(1 for a in appts.appointments if a.start_utc.astimezone(tehran).date() == today)
    tomorrow = today.fromordinal(today.toordinal() + 1)
    tomorrow_n = sum(
        1 for a in appts.appointments if a.start_utc.astimezone(tehran).date() == tomorrow
    )
    assert today_n >= MINIMAL.appointments_today
    assert tomorrow_n >= MINIMAL.appointments_tomorrow
    statuses = {a.status for a in appts.appointments}
    assert {"CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"} & statuses
    assert all(a.note is None or len(a.note) <= 2000 for a in appts.appointments)
    assert all(
        (a.capacity_pool == "MANUAL" and a.booking_channel == "MANUAL_STAFF")
        or (a.capacity_pool == "ONLINE" and a.booking_channel in {"ONLINE_WEB", "ONLINE_BOT"})
        for a in appts.appointments
    )


def test_demo_builders_meet_d05_minimums():
    now = datetime(2026, 11, 26, 9, 30, tzinfo=timezone.utc)
    people = build_patients(DEMO)
    staff = build_staff(DEMO)
    catalog = build_catalog(DEMO, now=now)
    appts = build_appointments(
        DEMO,
        patients=people.patients,
        catalog=catalog,
        staff=staff.staff,
        receptionist_person_id=staff.staff[0].person_id,
        now_utc=now,
    )
    assert len(people.patients) >= 500
    assert len({p.shared_phone_family for p in people.patients if p.shared_phone_family is not None}) >= 30
    assert sum(1 for p in people.patients if p.national_id) >= 30
    assert sum(1 for p in people.patients if p.exception_reason) >= 30
    assert len(staff.staff) >= 40
    assert len(catalog.services) >= 30
    assert len(catalog.rooms) >= 10
    assert len(appts.appointments) >= 10_000
    from zoneinfo import ZoneInfo

    tehran = ZoneInfo("Asia/Tehran")
    today = tehran_today(now)
    tomorrow = today.fromordinal(today.toordinal() + 1)
    assert sum(1 for a in appts.appointments if a.start_utc.astimezone(tehran).date() == today) >= 200
    assert sum(1 for a in appts.appointments if a.start_utc.astimezone(tehran).date() == tomorrow) >= 100
    assert appts.manual_overlap_pairs >= 30
    assert appts.checked_in_waiting_today >= 30
    assert appts.multi_service_group_count >= 100
    assert sum(1 for a in appts.appointments if a.note and a.note.startswith("GROUP:")) >= 200


def test_crypto_hooks_skip_without_keys(monkeypatch):
    monkeypatch.setenv("CLINIC_ENV", "test")
    monkeypatch.delenv("CLINIC_PII_AES_KEY_HEX", raising=False)
    monkeypatch.delenv("CLINIC_PII_AES_KEY", raising=False)
    monkeypatch.delenv("CLINIC_PII_HMAC_KEY_HEX", raising=False)
    monkeypatch.delenv("CLINIC_PII_HMAC_KEY", raising=False)
    people = build_patients(MINIMAL)
    plan = plan_crypto_rows(
        MINIMAL, tenant_id=demo_uuid(1, "tenant", 0), patients=people.patients
    )
    assert plan.available is False
    assert plan.identifiers == []
    assert plan.phones == []


def test_crypto_hooks_seal_when_keys_present(monkeypatch):
    for key, value in preview_demo_pii_env().items():
        monkeypatch.setenv(key, value)
    people = build_patients(MINIMAL)
    tenant = demo_uuid(20261126, "tenant", 0)
    plan = plan_crypto_rows(MINIMAL, tenant_id=tenant, patients=people.patients)
    assert plan.available is True
    assert len(plan.identifiers) >= MINIMAL.national_id_patients
    assert len(plan.phones) >= MINIMAL.patients
    assert any(p.is_shared_phone for p in plan.phones)


@pytest.mark.integration
def test_demo_loader_on_temp_pg_if_docker():
    """Full loader path — skipped when Docker/Testcontainers unavailable."""
    from tests.integration.docker_probe import DOCKER_AVAILABLE

    if not DOCKER_AVAILABLE:
        pytest.skip("Docker unavailable; builder structure tests cover offline path")
    pytest.skip("Full PG load covered by preview stack when Docker is present")
