"""Appointment aggregate and related value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from clinic_ecosystem.domain.scheduling.exceptions import InvalidAppointmentSchedule
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class BookingChannel(StrEnum):
    ONLINE_WEB = "ONLINE_WEB"
    ONLINE_BOT = "ONLINE_BOT"
    MANUAL_STAFF = "MANUAL_STAFF"


class CapacityPool(StrEnum):
    ONLINE = "ONLINE"
    MANUAL = "MANUAL"


class AppointmentStatus(StrEnum):
    PENDING_PAYMENT_HOLD = "PENDING_PAYMENT_HOLD"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED_HOLD = "EXPIRED_HOLD"
    NO_SHOW = "NO_SHOW"


class AllocationStatus(StrEnum):
    PENDING_PAYMENT_HOLD = "PENDING_PAYMENT_HOLD"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED_HOLD = "EXPIRED_HOLD"
    NO_SHOW = "NO_SHOW"


OCCUPYING_ONLINE_STATUSES = frozenset(
    {
        AllocationStatus.PENDING_PAYMENT_HOLD,
        AllocationStatus.CONFIRMED,
        AllocationStatus.CHECKED_IN,
    }
)


@dataclass(frozen=True, slots=True)
class ResourceAllocationRequest:
    resource_id: UUID
    resource_type: str


@dataclass(slots=True)
class AppointmentAllocation:
    id: UUID
    resource_id: UUID
    booking_channel: BookingChannel
    capacity_pool: CapacityPool
    allocation_status: AllocationStatus
    start_at_utc: datetime
    end_at_utc: datetime
    created_at_utc: datetime


@dataclass(slots=True)
class Appointment:
    id: UUID
    tenant_id: UUID
    beneficiary_patient_id: UUID
    booker_person_id: UUID | None
    patient_booking_note: str | None
    service_id: UUID
    status: AppointmentStatus
    booking_channel: BookingChannel
    capacity_pool: CapacityPool
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime
    hold_expires_at_utc: datetime | None
    aggregate_version: int
    created_at_utc: datetime
    updated_at_utc: datetime
    allocations: list[AppointmentAllocation] = field(default_factory=list)
    domain_events: list[dict] = field(default_factory=list)

    @staticmethod
    def schedule(
        *,
        tenant_id: UUID,
        beneficiary_patient_id: UUID,
        booker_person_id: UUID | None,
        patient_booking_note: str | None,
        service_id: UUID,
        booking_channel: BookingChannel,
        capacity_pool: CapacityPool,
        start_at_utc: datetime,
        end_at_utc: datetime,
        resource_allocations: list[ResourceAllocationRequest],
        hold_expires_at_utc: datetime | None,
        initial_status: AppointmentStatus,
        now_utc: datetime | None = None,
    ) -> Appointment:
        now = now_utc or datetime.now(timezone.utc)
        if start_at_utc.tzinfo is None or end_at_utc.tzinfo is None:
            raise InvalidAppointmentSchedule("schedule times must be timezone-aware UTC")
        if start_at_utc >= end_at_utc:
            raise InvalidAppointmentSchedule("start must be before end")
        if patient_booking_note is not None and len(patient_booking_note) > 2000:
            raise InvalidAppointmentSchedule("patient_booking_note exceeds 2000 chars")
        if not resource_allocations:
            raise InvalidAppointmentSchedule("at least one resource allocation required")

        online_channels = {BookingChannel.ONLINE_WEB, BookingChannel.ONLINE_BOT}
        if booking_channel in online_channels and capacity_pool != CapacityPool.ONLINE:
            raise InvalidAppointmentSchedule("online channel requires ONLINE pool")
        if booking_channel == BookingChannel.MANUAL_STAFF and capacity_pool != CapacityPool.MANUAL:
            raise InvalidAppointmentSchedule("manual channel requires MANUAL pool")
        if capacity_pool == CapacityPool.ONLINE and initial_status not in {
            AppointmentStatus.PENDING_PAYMENT_HOLD,
            AppointmentStatus.CONFIRMED,
        }:
            raise InvalidAppointmentSchedule("invalid initial ONLINE status")
        if (
            capacity_pool == CapacityPool.ONLINE
            and initial_status == AppointmentStatus.PENDING_PAYMENT_HOLD
            and hold_expires_at_utc is None
        ):
            raise InvalidAppointmentSchedule("ONLINE hold requires hold_expires_at_utc")

        appointment_id = new_uuid7()
        allocation_status = AllocationStatus(initial_status.value)
        allocations = [
            AppointmentAllocation(
                id=new_uuid7(),
                resource_id=req.resource_id,
                booking_channel=booking_channel,
                capacity_pool=capacity_pool,
                allocation_status=allocation_status,
                start_at_utc=start_at_utc,
                end_at_utc=end_at_utc,
                created_at_utc=now,
            )
            for req in resource_allocations
        ]
        # Unique resources per appointment
        resource_ids = [a.resource_id for a in allocations]
        if len(resource_ids) != len(set(resource_ids)):
            raise InvalidAppointmentSchedule("duplicate resource in allocation set")

        appt = Appointment(
            id=appointment_id,
            tenant_id=tenant_id,
            beneficiary_patient_id=beneficiary_patient_id,
            booker_person_id=booker_person_id,
            patient_booking_note=patient_booking_note,
            service_id=service_id,
            status=initial_status,
            booking_channel=booking_channel,
            capacity_pool=capacity_pool,
            scheduled_start_at_utc=start_at_utc,
            scheduled_end_at_utc=end_at_utc,
            hold_expires_at_utc=hold_expires_at_utc,
            aggregate_version=1,
            created_at_utc=now,
            updated_at_utc=now,
            allocations=allocations,
        )
        appt.domain_events.append(
            {
                "event_type": "appointment.scheduled",
                "appointment_id": str(appointment_id),
                "tenant_id": str(tenant_id),
                "capacity_pool": capacity_pool.value,
                "booking_channel": booking_channel.value,
                "resource_ids": [str(r) for r in resource_ids],
                "scheduled_start_at_utc": start_at_utc.isoformat(),
                "scheduled_end_at_utc": end_at_utc.isoformat(),
            }
        )
        return appt

    def expire_hold(self, *, now_utc: datetime) -> None:
        if self.status != AppointmentStatus.PENDING_PAYMENT_HOLD:
            raise InvalidAppointmentSchedule("only PENDING_PAYMENT_HOLD can expire")
        if self.hold_expires_at_utc is None or self.hold_expires_at_utc > now_utc:
            raise InvalidAppointmentSchedule("hold not yet expired")
        self.status = AppointmentStatus.EXPIRED_HOLD
        self.hold_expires_at_utc = None
        self.aggregate_version += 1
        self.updated_at_utc = now_utc
        for alloc in self.allocations:
            alloc.allocation_status = AllocationStatus.EXPIRED_HOLD
        self.domain_events.append(
            {
                "event_type": "appointment.hold_expired",
                "appointment_id": str(self.id),
                "tenant_id": str(self.tenant_id),
            }
        )
