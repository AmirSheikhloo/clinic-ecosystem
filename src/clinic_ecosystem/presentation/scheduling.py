"""Thin presentation adapter for ScheduleAppointment command construction."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool


def fingerprint_schedule_request(body: dict) -> str:
    """Stable SHA-256 over RFC8785-ish sorted JSON (M1-01 pragmatic canonicalization).

    Full RFC8785 JCS can replace this helper without changing the handler contract.
    """
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def command_from_api_payload(
    *,
    verified_tenant_id: UUID,
    verified_principal_id: UUID,
    actor_type: str,
    payload: dict,
    idempotency_key: str,
    correlation_id: UUID,
) -> ScheduleAppointmentCommand:
    """Map an API payload to ScheduleAppointmentCommand using server-verified identity."""
    body_for_fp = {
        "beneficiary_patient_id": payload["beneficiary_patient_id"],
        "booker_person_id": payload.get("booker_person_id"),
        "service_id": payload["service_id"],
        "booking_channel": payload["booking_channel"],
        "capacity_pool": payload["capacity_pool"],
        "resource_ids": payload["resource_ids"],
        "start_at_utc": payload["start_at_utc"],
        "end_at_utc": payload["end_at_utc"],
        "hold_expires_at_utc": payload.get("hold_expires_at_utc"),
        "acknowledge_overlap": bool(payload.get("acknowledge_overlap", False)),
        "patient_booking_note": payload.get("patient_booking_note"),
    }
    return ScheduleAppointmentCommand(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint_schedule_request(body_for_fp),
        principal_id=verified_principal_id,
        actor_type=actor_type,
        tenant_id=verified_tenant_id,
        beneficiary_patient_id=UUID(payload["beneficiary_patient_id"]),
        booker_person_id=(
            UUID(payload["booker_person_id"]) if payload.get("booker_person_id") else None
        ),
        patient_booking_note=payload.get("patient_booking_note"),
        service_id=UUID(payload["service_id"]),
        booking_channel=BookingChannel(payload["booking_channel"]),
        capacity_pool=CapacityPool(payload["capacity_pool"]),
        resource_ids=tuple(UUID(x) for x in payload["resource_ids"]),
        start_at_utc=datetime.fromisoformat(payload["start_at_utc"]),
        end_at_utc=datetime.fromisoformat(payload["end_at_utc"]),
        hold_expires_at_utc=(
            datetime.fromisoformat(payload["hold_expires_at_utc"])
            if payload.get("hold_expires_at_utc")
            else None
        ),
        acknowledge_overlap=bool(payload.get("acknowledge_overlap", False)),
    )
