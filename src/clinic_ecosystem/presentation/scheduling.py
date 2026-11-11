"""Presentation adapter: RFC8785 fingerprints + ScheduleAppointment command mapping.

Clause 779 conflict projections are returned via ManualOverlapAcknowledgementRequired
from the application handler; this module maps HTTP/API payloads into commands and
serializes authorized conflict display items for the staff interface.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import (
    ConflictDisplayItem,
    ManualOverlapAcknowledgementRequired,
)
from clinic_ecosystem.application.scheduling.fingerprint import (
    fingerprint_from_schedule_fields,
)
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool


def fingerprint_schedule_request(body: dict) -> str:
    """Backward-compatible name: RFC 8785 fingerprint of a schedule request object."""
    from clinic_ecosystem.application.scheduling.fingerprint import (
        fingerprint_schedule_request as _fp,
    )

    return _fp(body)


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
    resource_ids = tuple(UUID(x) for x in payload["resource_ids"])
    ack_ids = tuple(UUID(x) for x in payload.get("acknowledged_conflict_ids", []))
    start_at = datetime.fromisoformat(payload["start_at_utc"])
    end_at = datetime.fromisoformat(payload["end_at_utc"])
    hold = (
        datetime.fromisoformat(payload["hold_expires_at_utc"])
        if payload.get("hold_expires_at_utc")
        else None
    )
    booker = (
        UUID(payload["booker_person_id"]) if payload.get("booker_person_id") else None
    )
    acknowledge = bool(payload.get("acknowledge_overlap", False))
    fingerprint = fingerprint_from_schedule_fields(
        beneficiary_patient_id=UUID(payload["beneficiary_patient_id"]),
        booker_person_id=booker,
        service_id=UUID(payload["service_id"]),
        booking_channel=payload["booking_channel"],
        capacity_pool=payload["capacity_pool"],
        resource_ids=resource_ids,
        start_at_utc=start_at,
        end_at_utc=end_at,
        hold_expires_at_utc=hold,
        acknowledge_overlap=acknowledge,
        acknowledged_conflict_ids=ack_ids,
        patient_booking_note=payload.get("patient_booking_note"),
    )
    return ScheduleAppointmentCommand(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        principal_id=verified_principal_id,
        actor_type=actor_type,
        tenant_id=verified_tenant_id,
        beneficiary_patient_id=UUID(payload["beneficiary_patient_id"]),
        booker_person_id=booker,
        patient_booking_note=payload.get("patient_booking_note"),
        service_id=UUID(payload["service_id"]),
        booking_channel=BookingChannel(payload["booking_channel"]),
        capacity_pool=CapacityPool(payload["capacity_pool"]),
        resource_ids=resource_ids,
        start_at_utc=start_at,
        end_at_utc=end_at,
        hold_expires_at_utc=hold,
        acknowledge_overlap=acknowledge,
        acknowledged_conflict_ids=ack_ids,
    )


def serialize_manual_conflict_response(
    exc: ManualOverlapAcknowledgementRequired,
) -> dict:
    """Staff-interface JSON body for clause 779 conflict acknowledgement."""
    return {
        "error": "manual_overlap_acknowledgement_required",
        "conflicts": [_serialize_conflict(item) for item in exc.conflicts],
    }


def _serialize_conflict(item: ConflictDisplayItem) -> dict:
    payload = asdict(item)
    payload["appointment_id"] = str(item.appointment_id)
    payload["scheduled_start_at_utc"] = item.scheduled_start_at_utc.isoformat()
    payload["scheduled_end_at_utc"] = item.scheduled_end_at_utc.isoformat()
    return payload
