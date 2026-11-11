"""ScheduleAppointmentHandler unit tests with in-memory fakes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import (
    IdempotencyInProgress,
    ManualOverlapAcknowledgementRequired,
    UnauthorizedScheduling,
)
from clinic_ecosystem.application.scheduling.handler import ScheduleAppointmentHandler
from clinic_ecosystem.domain.scheduling.conflicts import OverlapConflictFact
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def bind_tenant(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def flush(self) -> None:
        return None


class FakeIdempotency:
    def __init__(self, status: str = "CLAIMED", payload: dict | None = None) -> None:
        self.status = status
        self.payload = payload or {}
        self.completed = False

    async def claim(self, **kwargs: Any) -> dict[str, Any]:
        if self.status == "COMPLETED":
            return {"status": "COMPLETED", "response_payload": self.payload}
        return {"status": self.status}

    async def complete(self, **kwargs: Any) -> None:
        self.completed = True


class FakeAppointments:
    def __init__(self, *, facts: list[OverlapConflictFact] | None = None) -> None:
        self.facts = facts or []
        self.added = None
        self.lock_calls: list[str] = []

    async def lock_resources(self, tenant_id: UUID, resource_ids: list[UUID]) -> None:
        self.lock_calls.append("resources")

    async def get_service_requirements(self, tenant_id: UUID, service_id: UUID) -> list:
        return []

    async def get_resource_types(self, tenant_id: UUID, resource_ids: list[UUID]) -> dict:
        return {rid: "ROOM" for rid in resource_ids}

    async def discover_overlapping_appointment_ids(self, **kwargs: Any) -> list[UUID]:
        return sorted({f.appointment_id for f in self.facts}, key=str)

    async def lock_appointments(self, tenant_id: UUID, appointment_ids: list[UUID]) -> None:
        self.lock_calls.append("appointments")

    async def lock_allocations_for_appointments(
        self, tenant_id: UUID, appointment_ids: list[UUID]
    ) -> None:
        self.lock_calls.append("allocations")

    async def find_overlap_facts(self, **kwargs: Any) -> list[OverlapConflictFact]:
        return list(self.facts)

    async def expire_conflicting_holds(self, **kwargs: Any) -> list[UUID]:
        return []

    async def add(self, appointment: Any) -> None:
        self.added = appointment

    async def enqueue_hold_expiry(self, **kwargs: Any) -> None:
        return None


class FakeOutbox:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def stage(self, **kwargs: Any) -> None:
        self.messages.append(kwargs)


class FakeAudit:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def append(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)


class FakePermissions:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def principal_has(self, **kwargs: Any) -> bool:
        return self.allowed


class FakePatientDisplay:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}
        self.called = False

    async def display_safe_names(self, **kwargs: Any) -> dict[UUID, str]:
        self.called = True
        return dict(self.names)


def _command(**overrides: Any) -> ScheduleAppointmentCommand:
    resource_id = overrides.pop("resource_id", new_uuid7())
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    base = dict(
        correlation_id=new_uuid7(),
        idempotency_key="key-1",
        request_fingerprint="fp-1",
        principal_id=new_uuid7(),
        actor_type="USER",
        tenant_id=new_uuid7(),
        beneficiary_patient_id=new_uuid7(),
        booker_person_id=None,
        patient_booking_note=None,
        service_id=new_uuid7(),
        booking_channel=BookingChannel.MANUAL_STAFF,
        capacity_pool=CapacityPool.MANUAL,
        resource_ids=(resource_id,),
        start_at_utc=start,
        end_at_utc=start + timedelta(minutes=30),
        hold_expires_at_utc=None,
        acknowledge_overlap=False,
        acknowledged_conflict_ids=(),
    )
    base.update(overrides)
    return ScheduleAppointmentCommand(**base)


def _handler(uow, appts, perms=None, display=None, idem=None):
    @asynccontextmanager
    async def factory():
        yield uow

    return ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=idem or FakeIdempotency(),
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=perms or FakePermissions(),
        patient_display=display or FakePatientDisplay(),
    )


@pytest.mark.asyncio
async def test_idempotency_in_progress_raises_425_semantics() -> None:
    uow = FakeUow()
    handler = _handler(uow, FakeAppointments(), idem=FakeIdempotency(status="IN_PROGRESS"))
    with pytest.raises(IdempotencyInProgress):
        await handler.handle(_command())
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_manual_overlap_authorized_requires_ack_with_display_name() -> None:
    uow = FakeUow()
    patient_id = new_uuid7()
    appt_id = new_uuid7()
    start = datetime.now(timezone.utc)
    facts = [
        OverlapConflictFact(
            appointment_id=appt_id,
            beneficiary_patient_id=patient_id,
            booking_channel="ONLINE_WEB",
            capacity_pool="ONLINE",
            scheduled_start_at_utc=start,
            scheduled_end_at_utc=start + timedelta(minutes=30),
            resource_id=new_uuid7(),
            allocation_status="CONFIRMED",
        )
    ]
    display = FakePatientDisplay({patient_id: "Ada Clinic"})
    handler = _handler(
        uow,
        FakeAppointments(facts=facts),
        perms=FakePermissions(True),
        display=display,
    )
    with pytest.raises(ManualOverlapAcknowledgementRequired) as excinfo:
        await handler.handle(_command())
    assert display.called
    assert excinfo.value.conflicts[0].display_safe_patient_name == "Ada Clinic"
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_manual_overlap_unauthorized_no_display_lookup() -> None:
    uow = FakeUow()
    patient_id = new_uuid7()
    start = datetime.now(timezone.utc)
    facts = [
        OverlapConflictFact(
            appointment_id=new_uuid7(),
            beneficiary_patient_id=patient_id,
            booking_channel="MANUAL_STAFF",
            capacity_pool="MANUAL",
            scheduled_start_at_utc=start,
            scheduled_end_at_utc=start + timedelta(minutes=30),
            resource_id=new_uuid7(),
            allocation_status="CONFIRMED",
        )
    ]
    display = FakePatientDisplay({patient_id: "Secret Name"})
    handler = _handler(
        uow,
        FakeAppointments(facts=facts),
        perms=FakePermissions(False),
        display=display,
    )
    with pytest.raises(UnauthorizedScheduling):
        await handler.handle(_command())
    assert display.called is False
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_manual_ack_uses_preinsert_audit_snapshot_and_lock_order() -> None:
    uow = FakeUow()
    patient_id = new_uuid7()
    appt_id = new_uuid7()
    start = datetime.now(timezone.utc)
    facts = [
        OverlapConflictFact(
            appointment_id=appt_id,
            beneficiary_patient_id=patient_id,
            booking_channel="MANUAL_STAFF",
            capacity_pool="MANUAL",
            scheduled_start_at_utc=start,
            scheduled_end_at_utc=start + timedelta(minutes=30),
            resource_id=new_uuid7(),
            allocation_status="CONFIRMED",
        )
    ]
    appts = FakeAppointments(facts=facts)
    audit = FakeAudit()

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=FakeOutbox(),
        audit=audit,
        permissions=FakePermissions(True),
        patient_display=FakePatientDisplay({patient_id: "Ada Clinic"}),
    )
    result = await handler.handle(
        _command(acknowledge_overlap=True, acknowledged_conflict_ids=(appt_id,))
    )
    assert result.replayed is False
    assert appts.lock_calls == ["resources", "appointments", "allocations"]
    assert len(audit.entries) == 1
    snap = audit.entries[0]["details"]["conflict_snapshot"]
    assert len(snap) == 1
    assert snap[0]["appointment_id"] == str(appt_id)
    assert "display_safe_patient_name" not in snap[0]
    assert str(result.appointment_id) not in {
        item["appointment_id"] for item in snap
    }
    assert uow.committed


@pytest.mark.asyncio
async def test_manual_schedule_success_stages_outbox() -> None:
    uow = FakeUow()
    outbox = FakeOutbox()
    appts = FakeAppointments()

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=outbox,
        audit=FakeAudit(),
        permissions=FakePermissions(),
        patient_display=FakePatientDisplay(),
    )
    result = await handler.handle(_command())
    assert result.replayed is False
    assert appts.added is not None
    assert len(outbox.messages) == 1
    assert uow.committed
