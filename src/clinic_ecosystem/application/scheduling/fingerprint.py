"""RFC 8785 (JCS) request fingerprinting for idempotency (clauses 172–176)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import rfc8785


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone-aware datetime required for fingerprinting")
    utc = value.astimezone(timezone.utc)
    if utc.microsecond:
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    raise TypeError(f"unsupported fingerprint value type: {type(value)!r}")


def canonical_schedule_request_object(
    *,
    beneficiary_patient_id: UUID | str,
    booker_person_id: UUID | str | None,
    service_id: UUID | str,
    booking_channel: str,
    capacity_pool: str,
    resource_ids: list[UUID | str] | tuple[UUID | str, ...],
    start_at_utc: datetime | str,
    end_at_utc: datetime | str,
    hold_expires_at_utc: datetime | str | None,
    acknowledge_overlap: bool,
    acknowledged_conflict_ids: list[UUID | str] | tuple[UUID | str, ...] = (),
    patient_booking_note: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-compatible object with deterministically ordered UUID arrays."""
    resources = sorted(str(x) for x in resource_ids)
    ack_ids = sorted(str(x) for x in acknowledged_conflict_ids)
    return _jsonable(
        {
            "acknowledge_overlap": bool(acknowledge_overlap),
            "acknowledged_conflict_ids": ack_ids,
            "beneficiary_patient_id": beneficiary_patient_id,
            "booker_person_id": booker_person_id,
            "booking_channel": booking_channel,
            "capacity_pool": capacity_pool,
            "end_at_utc": end_at_utc,
            "hold_expires_at_utc": hold_expires_at_utc,
            "patient_booking_note": patient_booking_note,
            "resource_ids": resources,
            "service_id": service_id,
            "start_at_utc": start_at_utc,
        }
    )


def fingerprint_schedule_request(body: dict[str, Any]) -> str:
    """SHA-256 hex digest of RFC 8785 canonical UTF-8 bytes."""
    canonical = rfc8785.dumps(_jsonable(body))
    return hashlib.sha256(canonical).hexdigest()


def fingerprint_from_schedule_fields(**kwargs: Any) -> str:
    return fingerprint_schedule_request(canonical_schedule_request_object(**kwargs))
