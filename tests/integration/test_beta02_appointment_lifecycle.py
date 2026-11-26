"""BETA-02 lifecycle: check-in, complete, no-show and list/upcoming reads."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.integration

_BASE = datetime(2031, 4, 1, 6, 0, tzinfo=timezone.utc)
_counter = {"n": 0}


def _slot():
    _counter["n"] += 1
    start = _BASE + timedelta(hours=_counter["n"] * 3)
    return start, start + timedelta(minutes=30)


def _book(ops, headers, start=None, end=None):
    seed = ops.seed.base
    if start is None:
        start, end = _slot()
    body = {
        "beneficiary_patient_id": str(seed.patient_a_id),
        "service_id": str(seed.service_a_id),
        "resource_ids": [str(seed.resource_a_id)],
        "start_at_utc": start.isoformat(),
        "end_at_utc": end.isoformat(),
    }
    return ops.client.post(
        "/api/v1/appointments",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json=body,
    )


def _create(ops, headers=None, start=None, end=None):
    headers = headers or ops.receptionist()
    res = _book(ops, headers, start=start, end=end)
    assert res.status_code == 200, res.text
    return res.json()["appointment_id"]


def _version(ops, headers, appt):
    return ops.client.get(f"/api/v1/appointments/{appt}", headers=headers).json()["aggregate_version"]


def _post(ops, headers, appt, action, version, key=None):
    return ops.client.post(
        f"/api/v1/appointments/{appt}/{action}",
        headers={
            **headers,
            "If-Match": f'"{version}"',
            "Idempotency-Key": key or str(uuid.uuid4()),
        },
        json={},
    )


def test_check_in_then_complete_updates_allocations_and_audit(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    version = _version(ops, rec, appt)

    checked = _post(ops, rec, appt, "check-in", version)
    assert checked.status_code == 200, checked.text
    assert checked.json()["status"] == "CHECKED_IN"
    detail = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    assert detail["status"] == "CHECKED_IN"
    assert {a["allocation_status"] for a in detail["allocations"]} == {"CHECKED_IN"}
    assert detail["can_complete"] and detail["can_cancel"] and not detail["can_check_in"]

    done = _post(ops, rec, appt, "complete", version + 1)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "COMPLETED"
    after = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    assert after["status"] == "COMPLETED"
    assert {a["allocation_status"] for a in after["allocations"]} == {"COMPLETED"}
    assert not after["can_complete"] and not after["can_cancel"]

    audit = ops.admin_query(
        "SELECT operation FROM audit_entries WHERE target_id = $1 "
        "AND operation = ANY($2::text[]) ORDER BY created_at_utc",
        uuid.UUID(appt),
        ["appointment.checked_in", "appointment.completed"],
    )
    assert [r["operation"] for r in audit] == [
        "appointment.checked_in",
        "appointment.completed",
    ]
    outbox = ops.admin_query(
        "SELECT message_type FROM outbox_messages WHERE payload_json->>'appointment_id' = $1 "
        "AND message_type = ANY($2::text[]) ORDER BY created_at_utc",
        appt,
        ["appointment.checked_in", "appointment.completed"],
    )
    assert [r["message_type"] for r in outbox] == [
        "appointment.checked_in",
        "appointment.completed",
    ]


def test_no_show_after_start_and_premature_rejected(ops) -> None:
    rec = ops.receptionist()
    future = _create(ops, rec)
    premature = _post(ops, rec, future, "no-show", _version(ops, rec, future))
    assert premature.status_code == 409
    assert premature.json()["error"] == "no_show_before_start"

    past_start = datetime.now(timezone.utc) - timedelta(hours=2)
    past_end = past_start + timedelta(minutes=30)
    past = _create(ops, rec, start=past_start, end=past_end)
    version = _version(ops, rec, past)
    ok = _post(ops, rec, past, "no-show", version)
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "NO_SHOW"
    detail = ops.client.get(f"/api/v1/appointments/{past}", headers=rec).json()
    assert detail["status"] == "NO_SHOW"
    assert {a["allocation_status"] for a in detail["allocations"]} == {"NO_SHOW"}
    audit = ops.admin_query(
        "SELECT count(*) AS n FROM audit_entries WHERE target_id = $1 "
        "AND operation = 'appointment.no_show'",
        uuid.UUID(past),
    )
    assert audit[0]["n"] == 1


def test_cancel_from_checked_in_releases_capacity(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    assert _post(ops, rec, appt, "check-in", _version(ops, rec, appt)).status_code == 200
    cancelled = ops.client.post(
        f"/api/v1/appointments/{appt}/cancel",
        headers={
            **rec,
            "If-Match": f'"{_version(ops, rec, appt)}"',
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"reason": "left early"},
    )
    assert cancelled.status_code == 200, cancelled.text
    detail = ops.client.get(f"/api/v1/appointments/{appt}", headers=rec).json()
    assert detail["status"] == "CANCELLED"
    assert {a["allocation_status"] for a in detail["allocations"]} == {"CANCELLED"}


def test_lifecycle_unauthorized_is_forbidden(ops) -> None:
    rec = ops.receptionist()
    appt = _create(ops, rec)
    version = _version(ops, rec, appt)
    for action in ("check-in", "complete", "no-show"):
        assert _post(ops, ops.unauthorized(), appt, action, version).status_code == 403
        assert _post(ops, ops.deputy(), appt, action, version).status_code == 403


def test_management_list_and_upcoming(ops) -> None:
    rec = ops.receptionist()
    past_start = datetime.now(timezone.utc) - timedelta(minutes=30)
    past = _create(ops, rec, start=past_start, end=past_start + timedelta(minutes=20))
    future_start = datetime.now(timezone.utc) + timedelta(hours=1)
    future = _create(ops, rec, start=future_start, end=future_start + timedelta(minutes=30))
    assert _post(ops, rec, future, "check-in", _version(ops, rec, future)).status_code == 200

    window_start = datetime.now(timezone.utc) - timedelta(days=1)
    window_end = datetime.now(timezone.utc) + timedelta(days=2)
    mgmt = ops.client.get(
        "/api/v1/appointments/management",
        headers=rec,
        params={
            "start_at_utc": window_start.isoformat(),
            "end_at_utc": window_end.isoformat(),
            "sort": "time",
            "limit": 50,
            "offset": 0,
        },
    )
    assert mgmt.status_code == 200, mgmt.text
    body = mgmt.json()
    ids = {i["appointment_id"] for i in body["items"]}
    assert past in ids and future in ids
    assert body["total"] >= 2
    assert "truncated" in body and body["offset"] == 0

    q = ops.client.get(
        "/api/v1/appointments/management",
        headers=rec,
        params={
            "start_at_utc": window_start.isoformat(),
            "end_at_utc": window_end.isoformat(),
            "q": "Alpha",
            "limit": 10,
        },
    )
    assert q.status_code == 200, q.text
    assert any(i["appointment_id"] in {past, future} for i in q.json()["items"])

    upcoming = ops.client.get(
        "/api/v1/appointments/upcoming",
        headers=rec,
        params={"limit": 20},
    )
    assert upcoming.status_code == 200, upcoming.text
    up_ids = [i["appointment_id"] for i in upcoming.json()["items"]]
    assert future in up_ids
    assert past not in up_ids  # end already passed
    assert all(i["status"] in {"CONFIRMED", "CHECKED_IN"} for i in upcoming.json()["items"])
    assert ops.client.get(
        "/api/v1/appointments/upcoming", headers=ops.unauthorized()
    ).status_code == 403
