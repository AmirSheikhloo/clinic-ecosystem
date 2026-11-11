"""RFC 8785 JCS fingerprint contract tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import rfc8785

from clinic_ecosystem.application.scheduling.fingerprint import (
    fingerprint_from_schedule_fields,
    fingerprint_schedule_request,
)


def test_object_key_ordering_independent_of_insertion() -> None:
    a = fingerprint_schedule_request({"b": 1, "a": 2})
    b = fingerprint_schedule_request({"a": 2, "b": 1})
    assert a == b
    assert rfc8785.dumps({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_unicode_handling() -> None:
    left = fingerprint_schedule_request({"note": "بیمار"})
    right = fingerprint_schedule_request({"note": "بیمار"})
    assert left == right
    assert left != fingerprint_schedule_request({"note": "patient"})


def test_nested_objects_and_arrays() -> None:
    body = {
        "outer": {"z": [3, 2, 1], "a": {"k": "v"}},
        "arr": [{"b": 1}, {"a": 2}],
    }
    assert fingerprint_schedule_request(body) == fingerprint_schedule_request(
        {"arr": [{"b": 1}, {"a": 2}], "outer": {"a": {"k": "v"}, "z": [3, 2, 1]}}
    )


def test_numeric_edge_cases_supported_by_jcs() -> None:
    import pytest
    from rfc8785 import IntegerDomainError

    # Equivalent integers within the safe JSON integer domain match.
    assert fingerprint_schedule_request({"n": 1}) == fingerprint_schedule_request({"n": 1})
    assert fingerprint_schedule_request({"n": 1}) != fingerprint_schedule_request({"n": 2})
    safe = 2**53 - 1
    assert fingerprint_schedule_request({"n": safe}) == fingerprint_schedule_request({"n": safe})
    # RFC 8785 rejects integers outside the IEEE-754 safe integer domain.
    with pytest.raises(IntegerDomainError):
        fingerprint_schedule_request({"n": 2**53})


def test_equivalent_schedule_fields_same_fingerprint() -> None:
    u1 = UUID("01900000-0000-7000-8000-000000000001")
    u2 = UUID("01900000-0000-7000-8000-000000000002")
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    left = fingerprint_from_schedule_fields(
        beneficiary_patient_id=u1,
        booker_person_id=None,
        service_id=u2,
        booking_channel="MANUAL_STAFF",
        capacity_pool="MANUAL",
        resource_ids=[u2, u1],
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=None,
        acknowledge_overlap=True,
        acknowledged_conflict_ids=[u2, u1],
        patient_booking_note=None,
    )
    right = fingerprint_from_schedule_fields(
        beneficiary_patient_id=str(u1),
        booker_person_id=None,
        service_id=str(u2),
        booking_channel="MANUAL_STAFF",
        capacity_pool="MANUAL",
        resource_ids=[u1, u2],
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=None,
        acknowledge_overlap=True,
        acknowledged_conflict_ids=[u1, u2],
        patient_booking_note=None,
    )
    assert left == right


def test_different_semantic_requests_differ() -> None:
    u1 = UUID("01900000-0000-7000-8000-000000000001")
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    base = dict(
        beneficiary_patient_id=u1,
        booker_person_id=None,
        service_id=u1,
        booking_channel="MANUAL_STAFF",
        capacity_pool="MANUAL",
        resource_ids=[u1],
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=None,
        acknowledge_overlap=False,
        acknowledged_conflict_ids=(),
        patient_booking_note=None,
    )
    a = fingerprint_from_schedule_fields(**base)
    b = fingerprint_from_schedule_fields(**{**base, "acknowledge_overlap": True})
    assert a != b


def test_acknowledged_id_ordering_deterministic() -> None:
    ids = [
        UUID("01900000-0000-7000-8000-00000000000b"),
        UUID("01900000-0000-7000-8000-00000000000a"),
    ]
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    kwargs = dict(
        beneficiary_patient_id=ids[0],
        booker_person_id=None,
        service_id=ids[0],
        booking_channel="MANUAL_STAFF",
        capacity_pool="MANUAL",
        resource_ids=ids,
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=None,
        acknowledge_overlap=True,
        patient_booking_note=None,
    )
    assert fingerprint_from_schedule_fields(
        **kwargs, acknowledged_conflict_ids=ids
    ) == fingerprint_from_schedule_fields(
        **kwargs, acknowledged_conflict_ids=list(reversed(ids))
    )
