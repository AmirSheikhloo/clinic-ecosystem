"""Presentation adapter: RFC8785 fingerprints + ScheduleAppointment command mapping.

Clause 779 conflict projections are returned via ManualOverlapAcknowledgementRequired
from the application handler; this module maps HTTP/API payloads into commands and
serializes authorized conflict display items for the staff interface.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.application.scheduling.commands import (
    ScheduleAppointmentCommand,
    ScheduleAppointmentGroupCommand,
    ScheduleGroupLine,
)
from clinic_ecosystem.application.scheduling.exceptions import (
    ConflictDisplayItem,
    GroupManualOverlapAcknowledgementRequired,
    ManualOverlapAcknowledgementRequired,
)
from clinic_ecosystem.application.scheduling.fingerprint import (
    fingerprint_from_group_fields,
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
    immediate_check_in = bool(payload.get("immediate_check_in", False))
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
    # Include immediate_check_in in fingerprint by appending to note-sensitive object
    # via a dedicated field hash: recompute with group-style flag when set.
    if immediate_check_in:
        from clinic_ecosystem.application.scheduling.fingerprint import (
            fingerprint_schedule_request as _fp,
            canonical_schedule_request_object,
        )

        body = canonical_schedule_request_object(
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
        body["immediate_check_in"] = True
        fingerprint = _fp(body)

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
        immediate_check_in=immediate_check_in,
    )


def group_command_from_api_payload(
    *,
    verified_tenant_id: UUID,
    verified_principal_id: UUID,
    actor_type: str,
    payload: dict,
    idempotency_key: str,
    correlation_id: UUID,
) -> ScheduleAppointmentGroupCommand:
    booker = (
        UUID(payload["booker_person_id"]) if payload.get("booker_person_id") else None
    )
    immediate_check_in = bool(payload.get("immediate_check_in", False))
    raw_lines = list(payload["lines"])
    lines: list[ScheduleGroupLine] = []
    fingerprint_lines: list[dict] = []
    for raw in raw_lines:
        start_at = datetime.fromisoformat(raw["start_at_utc"])
        end_at = datetime.fromisoformat(raw["end_at_utc"])
        resource_ids = tuple(UUID(x) for x in raw["resource_ids"])
        ack_ids = tuple(UUID(x) for x in raw.get("acknowledged_conflict_ids", []))
        acknowledge = bool(raw.get("acknowledge_overlap", False))
        lines.append(
            ScheduleGroupLine(
                client_line_id=str(raw["client_line_id"]),
                service_id=UUID(raw["service_id"]),
                resource_ids=resource_ids,
                start_at_utc=start_at,
                end_at_utc=end_at,
                acknowledge_overlap=acknowledge,
                acknowledged_conflict_ids=ack_ids,
                patient_booking_note=raw.get("patient_booking_note"),
            )
        )
        fingerprint_lines.append(
            {
                "client_line_id": raw["client_line_id"],
                "service_id": raw["service_id"],
                "resource_ids": list(raw["resource_ids"]),
                "start_at_utc": start_at,
                "end_at_utc": end_at,
                "acknowledge_overlap": acknowledge,
                "acknowledged_conflict_ids": list(ack_ids),
                "patient_booking_note": raw.get("patient_booking_note"),
            }
        )
    fingerprint = fingerprint_from_group_fields(
        beneficiary_patient_id=UUID(payload["beneficiary_patient_id"]),
        booker_person_id=booker,
        booking_channel=payload.get("booking_channel", "MANUAL_STAFF"),
        capacity_pool=payload.get("capacity_pool", "MANUAL"),
        immediate_check_in=immediate_check_in,
        lines=fingerprint_lines,
    )
    return ScheduleAppointmentGroupCommand(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        principal_id=verified_principal_id,
        actor_type=actor_type,
        tenant_id=verified_tenant_id,
        beneficiary_patient_id=UUID(payload["beneficiary_patient_id"]),
        booker_person_id=booker,
        lines=tuple(lines),
        booking_channel=BookingChannel(payload.get("booking_channel", "MANUAL_STAFF")),
        capacity_pool=CapacityPool(payload.get("capacity_pool", "MANUAL")),
        immediate_check_in=immediate_check_in,
    )


def serialize_manual_conflict_response(
    exc: ManualOverlapAcknowledgementRequired,
) -> dict:
    """Staff-interface JSON body for clause 779 conflict acknowledgement."""
    return {
        "error": "manual_overlap_acknowledgement_required",
        "conflicts": [_serialize_conflict(item) for item in exc.conflicts],
    }


def serialize_group_manual_conflict_response(
    exc: GroupManualOverlapAcknowledgementRequired,
) -> dict:
    """409 body with per-line conflict snapshots keyed by client_line_id."""
    return {
        "error": "manual_overlap_acknowledgement_required",
        "line_conflicts": {
            client_line_id: [_serialize_conflict(item) for item in conflicts]
            for client_line_id, conflicts in sorted(exc.conflicts_by_line.items())
        },
    }


def _serialize_conflict(item: ConflictDisplayItem) -> dict:
    payload = asdict(item)
    payload["appointment_id"] = str(item.appointment_id)
    payload["scheduled_start_at_utc"] = item.scheduled_start_at_utc.isoformat()
    payload["scheduled_end_at_utc"] = item.scheduled_end_at_utc.isoformat()
    return payload
