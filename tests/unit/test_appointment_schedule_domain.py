"""Domain Appointment.schedule invariants."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from clinic_ecosystem.domain.scheduling.exceptions import InvalidAppointmentSchedule
from clinic_ecosystem.domain.scheduling.model import (
    Appointment,
    AppointmentStatus,
    BookingChannel,
    CapacityPool,
    ResourceAllocationRequest,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


def test_schedule_online_hold_requires_expiry() -> None:
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=30)
    with pytest.raises(InvalidAppointmentSchedule):
        Appointment.schedule(
            tenant_id=new_uuid7(),
            beneficiary_patient_id=new_uuid7(),
            booker_person_id=None,
            patient_booking_note=None,
            service_id=new_uuid7(),
            booking_channel=BookingChannel.ONLINE_WEB,
            capacity_pool=CapacityPool.ONLINE,
            start_at_utc=start,
            end_at_utc=end,
            resource_allocations=[
                ResourceAllocationRequest(resource_id=new_uuid7(), resource_type="ROOM")
            ],
            hold_expires_at_utc=None,
            initial_status=AppointmentStatus.PENDING_PAYMENT_HOLD,
        )


def test_schedule_manual_success() -> None:
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=30)
    appt = Appointment.schedule(
        tenant_id=new_uuid7(),
        beneficiary_patient_id=new_uuid7(),
        booker_person_id=None,
        patient_booking_note=None,
        service_id=new_uuid7(),
        booking_channel=BookingChannel.MANUAL_STAFF,
        capacity_pool=CapacityPool.MANUAL,
        start_at_utc=start,
        end_at_utc=end,
        resource_allocations=[
            ResourceAllocationRequest(resource_id=new_uuid7(), resource_type="ROOM")
        ],
        hold_expires_at_utc=None,
        initial_status=AppointmentStatus.CONFIRMED,
    )
    assert appt.aggregate_version == 1
    assert len(appt.allocations) == 1
    assert appt.domain_events[0]["event_type"] == "appointment.scheduled"
