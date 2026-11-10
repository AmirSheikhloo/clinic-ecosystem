"""ScheduleAppointment command DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool


@dataclass(frozen=True, slots=True)
class ScheduleAppointmentCommand:
    correlation_id: UUID
    idempotency_key: str
    request_fingerprint: str
    principal_id: UUID
    actor_type: str
    tenant_id: UUID
    beneficiary_patient_id: UUID
    booker_person_id: UUID | None
    patient_booking_note: str | None
    service_id: UUID
    booking_channel: BookingChannel
    capacity_pool: CapacityPool
    resource_ids: tuple[UUID, ...]
    start_at_utc: datetime
    end_at_utc: datetime
    hold_expires_at_utc: datetime | None
    acknowledge_overlap: bool
    operation_scope: str = "appointment.schedule"
