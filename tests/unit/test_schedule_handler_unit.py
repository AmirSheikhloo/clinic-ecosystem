"""ScheduleAppointmentHandler unit tests with in-memory fakes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import IdempotencyInProgress
from clinic_ecosystem.application.scheduling.handler import ScheduleAppointmentHandler
from clinic_ecosystem.domain.scheduling.exceptions import (
    ManualOverlapAcknowledgementRequired,
)
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
    def __init__(self, *, overlaps: list[dict] | None = None) -> None:
        self.overlaps = overlaps or []
        self.added = None
        self.resource_id = new_uuid7()

    async def lock_resources(self, tenant_id: UUID, resource_ids: list[UUID]) -> None:
        return None

    async def get_service_requirements(self, tenant_id: UUID, service_id: UUID) -> list:
        return []

    async def get_resource_types(self, tenant_id: UUID, resource_ids: list[UUID]) -> dict:
        return {rid: "ROOM" for rid in resource_ids}

    async def find_overlaps(self, **kwargs: Any) -> list[dict]:
        return list(self.overlaps)

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
    )
    base.update(overrides)
    return ScheduleAppointmentCommand(**base)


@pytest.mark.asyncio
async def test_idempotency_in_progress_raises_425_semantics() -> None:
    uow = FakeUow()

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=FakeAppointments(),
        idempotency=FakeIdempotency(status="IN_PROGRESS"),
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(),
    )
    with pytest.raises(IdempotencyInProgress):
        await handler.handle(_command())
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_manual_overlap_requires_acknowledgement() -> None:
    uow = FakeUow()

    @asynccontextmanager
    async def factory():
        yield uow

    appts = FakeAppointments(
        overlaps=[
            {
                "appointment_id": new_uuid7(),
                "booking_channel": "ONLINE_WEB",
                "capacity_pool": "ONLINE",
            }
        ]
    )
    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(),
    )
    with pytest.raises(ManualOverlapAcknowledgementRequired):
        await handler.handle(_command())


@pytest.mark.asyncio
async def test_manual_schedule_success_stages_outbox() -> None:
    uow = FakeUow()

    @asynccontextmanager
    async def factory():
        yield uow

    outbox = FakeOutbox()
    appts = FakeAppointments()
    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=outbox,
        audit=FakeAudit(),
        permissions=FakePermissions(),
    )
    result = await handler.handle(_command())
    assert result.replayed is False
    assert appts.added is not None
    assert len(outbox.messages) == 1
    assert uow.committed
