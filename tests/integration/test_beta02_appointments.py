"""BETA-02 Workstream D: calendar, details, cancel and reschedule."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.integration

_BASE = datetime(2031, 3, 1, 6, 0, tzinfo=timezone.utc)
_counter = {"n": 0}


def _slot():
    _counter["n"] += 1
    start = _BASE + timedelta(hours=_counter["n"] * 3)
    return start, start + timedelta(minutes=30)


def _book(ops, headers, start=None, end=None, **extra):
    seed = ops.seed.base
    if start is None:
        start, end = _slot()
    body = {
        "beneficiary_patient_id": str(seed.patient_a_id),
        "service_id": str(seed.service_a_id),
        "resource_ids": [str(seed.resource_a_id)],
        "start_at_utc": start.isoformat(), "end_at_utc": end.isoformat(),
    } | extra
    return ops.client.post("/api/v1/appointments",
                           headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json=body)


def _create(ops, headers=None):
    headers = headers or ops.receptionist()
    res = _book(ops, headers)
    assert res.status_code == 200, res.text
    return res.json()["appointment_id"]


def _cancel(ops, headers, appt, version, key=None, reason=None):
    return ops.client.post(
        f"/api/v1/appointments/{appt}/cancel",
        headers={**headers, "If-Match": f'"{version}"', "Idempotency-Key": key or str(uuid.uuid4())},
        json={"reason": reason} if reason else {})


def test_calendar_filters_bounds_and_permissions(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    _create(ops, rec)
    start = _BASE.isoformat()
    end = (_BASE + timedelta(days=30)).isoformat()
    seed = ops.seed.base
    res = ops.client.get("/api/v1/appointments/calendar", headers=rec, params={
        "start_at_utc": start, "end_at_utc": end, "resource_id": str(seed.resource_a_id),
        "service_id": str(seed.service_a_id), "status": "CONFIRMED"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert any(i["appointment_id"] == appt for i in body["items"])
    assert all(i["status"] == "CONFIRMED" and "Room Alpha" in i["resource_names"] for i in body["items"])
    other = ops.client.get("/api/v1/appointments/calendar", headers=rec, params={
        "start_at_utc": start, "end_at_utc": end, "resource_id": str(seed.resource_a2_id)})
    assert other.json()["items"] == []
    assert ops.client.get("/api/v1/appointments/calendar", headers=rec, params={
        "start_at_utc": start, "end_at_utc": (_BASE + timedelta(days=60)).isoformat()}).status_code == 400
    assert ops.client.get("/api/v1/appointments/calendar", headers=rec, params={
        "start_at_utc": start, "end_at_utc": end, "status": "BOGUS"}).status_code == 400
    trunc = ops.client.get("/api/v1/appointments/calendar", headers=rec, params={
        "start_at_utc": start, "end_at_utc": end, "limit": 1}).json()
    assert len(trunc["items"]) == 1 and trunc["truncated"] is True
    assert ops.client.get("/api/v1/appointments/calendar", headers=ops.unauthorized(), params={
        "start_at_utc": start, "end_at_utc": end}).status_code == 403


def test_details_include_allocations_versions_and_hide_cross_tenant(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    res = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec)
    assert res.status_code == 200
    body = res.json()
    assert res.headers["ETag"] == f'"{body["aggregate_version"]}"'
    assert body["allocations"][0]["resource_name"] == "Room Alpha"
    assert body["can_cancel"] and body["can_reschedule"]
    assert ops.client.get(f"/api/v1/appointments/{uuid.uuid4()}", headers=rec).status_code == 404
    assert ops.client.get(f"/api/v1/appointments/{appt}", headers=ops.unauthorized()).status_code == 403


def test_cancel_lifecycle_idempotency_versions_and_audit(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    version = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()["aggregate_version"]

    missing = ops.client.post(f"/api/v1/appointments/{appt}/cancel",
                              headers={**rec, "Idempotency-Key": str(uuid.uuid4())}, json={})
    assert missing.status_code == 428
    nokey = ops.client.post(f"/api/v1/appointments/{appt}/cancel",
                            headers={**rec, "If-Match": f'"{version}"'}, json={})
    assert nokey.status_code == 400
    stale = _cancel(ops, rec, appt, version + 5)
    assert stale.status_code == 412 and stale.json()["current_version"] == version

    key = str(uuid.uuid4())
    ok = _cancel(ops, rec, appt, version, key=key, reason="Patient called")
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "CANCELLED" and ok.json()["aggregate_version"] == version + 1
    replay = _cancel(ops, rec, appt, version, key=key, reason="Patient called")
    assert replay.status_code == 200 and replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == ok.json()
    reuse = _cancel(ops, rec, appt, version, key=key, reason="different")
    assert reuse.status_code == 409 and reuse.json()["error"] == "idempotency_key_reuse"
    again = _cancel(ops, rec, appt, version + 1)
    assert again.status_code == 409 and again.json()["error"] == "invalid_status_transition"

    detail = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    assert detail["status"] == "CANCELLED" and not detail["can_cancel"]
    assert {a["allocation_status"] for a in detail["allocations"]} == {"CANCELLED"}
    audit = ops.admin_query(
        "SELECT operation, details_json->>'reason' AS reason FROM audit_entries WHERE target_id = $1 "
        "AND operation = 'appointment.cancelled'", uuid.UUID(appt))
    assert len(audit) == 1 and audit[0]["reason"] == "Patient called"
    outbox = ops.admin_query(
        "SELECT count(*) AS n FROM outbox_messages WHERE message_type = 'appointment.cancelled' "
        "AND payload_json->>'appointment_id' = $1", appt)
    assert outbox[0]["n"] == 1

    # the freed slot can be booked again without an overlap acknowledgement
    start = datetime.fromisoformat(detail["scheduled_start_at_utc"])
    rebook = _book(ops, rec, start, start + timedelta(minutes=30))
    assert rebook.status_code == 200, rebook.text


def test_cancel_permission_and_cross_tenant(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    assert _cancel(ops, ops.unauthorized(), appt, 1).status_code == 403
    assert _cancel(ops, ops.deputy(), appt, 1).status_code == 403
    assert _cancel(ops, rec, str(uuid.uuid4()), 1).status_code == 404


def test_concurrent_cancels_only_one_wins(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    version = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()["aggregate_version"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: _cancel(ops, rec, appt, version), range(4)))
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1, codes
    assert set(codes) - {200} <= {409, 412}
    audit = ops.admin_query("SELECT count(*) AS n FROM audit_entries WHERE target_id = $1 "
                            "AND operation = 'appointment.cancelled'", uuid.UUID(appt))
    assert audit[0]["n"] == 1


def _resched(ops, headers, appt, version, start, end, key=None, **extra):
    return ops.client.post(
        f"/api/v1/appointments/{appt}/reschedule",
        headers={**headers, "If-Match": f'"{version}"', "Idempotency-Key": key or str(uuid.uuid4())},
        json={"start_at_utc": start.isoformat(), "end_at_utc": end.isoformat()} | extra)


def test_reschedule_moves_allocations_and_audits(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    detail = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    version = detail["aggregate_version"]
    new_start = datetime.fromisoformat(detail["scheduled_start_at_utc"]) + timedelta(days=2)
    new_end = new_start + timedelta(minutes=45)

    assert _resched(ops, rec, appt, version + 3, new_start, new_end).status_code == 412
    same = _resched(ops, rec, appt, version, datetime.fromisoformat(detail["scheduled_start_at_utc"]),
                    datetime.fromisoformat(detail["scheduled_end_at_utc"]))
    assert same.status_code == 400 and same.json()["error"] == "no_change"
    bad = _resched(ops, rec, appt, version, new_end, new_start)
    assert bad.status_code == 400

    key = str(uuid.uuid4())
    ok = _resched(ops, rec, appt, version, new_start, new_end, key=key)
    assert ok.status_code == 200, ok.text
    assert ok.json()["aggregate_version"] == version + 1
    replay = _resched(ops, rec, appt, version, new_start, new_end, key=key)
    assert replay.status_code == 200 and replay.headers["Idempotent-Replay"] == "true"
    after = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    assert datetime.fromisoformat(after["scheduled_start_at_utc"]) == new_start
    slots = ops.admin_query(
        "SELECT lower(time_slot) AS lo, upper(time_slot) AS hi FROM appointment_resource_allocations "
        "WHERE appointment_id = $1", uuid.UUID(appt))
    assert slots[0]["lo"] == new_start and slots[0]["hi"] == new_end
    audit = ops.admin_query("SELECT operation FROM audit_entries WHERE target_id = $1 "
                            "AND operation = 'appointment.rescheduled'", uuid.UUID(appt))
    assert len(audit) == 1


def test_reschedule_overlap_requires_acknowledgement_and_permission(ops) -> None:
    rec = ops.receptionist()
    first = _create(ops, rec)
    first_detail = ops.client.get(f"/api/v1/appointments/{first}", headers=rec).json()
    second = _create(ops, rec)
    second_detail = ops.client.get(f"/api/v1/appointments/{second}", headers=rec).json()
    target_start = datetime.fromisoformat(first_detail["scheduled_start_at_utc"]) + timedelta(minutes=10)
    target_end = target_start + timedelta(minutes=30)
    version = second_detail["aggregate_version"]

    needs_ack = _resched(ops, rec, second, version, target_start, target_end)
    assert needs_ack.status_code == 409
    body = needs_ack.json()
    assert body["error"] == "manual_overlap_acknowledgement_required"
    assert [c["appointment_id"] for c in body["conflicts"]] == [first]
    wrong_ids = _resched(ops, rec, second, version, target_start, target_end,
                         acknowledge_overlap=True, acknowledged_conflict_ids=[str(uuid.uuid4())])
    assert wrong_ids.status_code == 409
    acked = _resched(ops, rec, second, version, target_start, target_end,
                     acknowledge_overlap=True, acknowledged_conflict_ids=[first])
    assert acked.status_code == 200, acked.text
    snap = ops.admin_query("SELECT details_json FROM audit_entries WHERE target_id = $1 "
                           "AND operation = 'ALLOW_MANUAL_OVERBOOKING'", uuid.UUID(second))
    assert len(snap) == 1

    # a principal without the overbooking permission never learns conflict names
    third = _create(ops, rec)
    third_detail = ops.client.get(f"/api/v1/appointments/{third}", headers=rec).json()
    seed = ops.seed
    owner = ops.owner()
    role = ops.client.post("/api/v1/access/roles", headers=owner, json={
        "role_code": "RESCHEDULE_ONLY", "role_name": "Reschedule without overbooking",
        "permissions": ["BETA02_APPOINTMENTS_RESCHEDULE"]}).json()["role_id"]
    assert ops.client.put(f"/api/v1/access/accounts/{seed.target_account_id}/roles", headers=owner,
                          json={"role_ids": [role]}).status_code == 200
    probe = ops.login(seed.target_login, "Beta02-Target-Test-Only!!")
    denied = _resched(ops, probe, third, third_detail["aggregate_version"], target_start, target_end)
    assert denied.status_code == 403 and denied.json()["error"] == "permission_denied"
    assert "conflicts" not in denied.json()


def test_non_confirmed_or_online_appointments_cannot_be_changed(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    version = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()["aggregate_version"]
    assert _cancel(ops, rec, appt, version).status_code == 200
    start, end = _slot()
    res = _resched(ops, rec, appt, version + 1, start, end)
    assert res.status_code == 409 and res.json()["error"] == "invalid_status_transition"
