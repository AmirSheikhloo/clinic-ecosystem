"""ScheduleAppointmentHandler unit tests with in-memory fakes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from clinic_ecosystem.application.scheduling.commands import (
    ScheduleAppointmentCommand,
    ScheduleAppointmentGroupCommand,
    ScheduleGroupLine,
)
from clinic_ecosystem.application.scheduling.exceptions import (
    GroupManualOverlapAcknowledgementRequired,
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
        self.payload = kwargs.get("response_payload") or self.payload
        self.status = "COMPLETED"


class FakeAppointments:
    def __init__(
        self,
        *,
        facts: list[OverlapConflictFact] | None = None,
        facts_by_resource: dict[UUID, list[OverlapConflictFact]] | None = None,
        fail_on_add_index: int | None = None,
    ) -> None:
        self.facts = facts or []
        self.facts_by_resource = facts_by_resource or {}
        self.fail_on_add_index = fail_on_add_index
        self.added = None
        self.added_list: list[Any] = []
        self.lock_calls: list[str] = []
        self.locked_resource_orders: list[list[UUID]] = []

    async def lock_resources(self, tenant_id: UUID, resource_ids: list[UUID]) -> None:
        self.lock_calls.append("resources")
        self.locked_resource_orders.append(list(resource_ids))

    async def get_service_requirements(self, tenant_id: UUID, service_id: UUID) -> list:
        return []

    async def get_resource_types(self, tenant_id: UUID, resource_ids: list[UUID]) -> dict:
        return {rid: "ROOM" for rid in resource_ids}

    async def discover_overlapping_appointment_ids(self, **kwargs: Any) -> list[UUID]:
        facts = self._facts_for_kwargs(kwargs)
        return sorted({f.appointment_id for f in facts}, key=str)

    async def lock_appointments(self, tenant_id: UUID, appointment_ids: list[UUID]) -> None:
        self.lock_calls.append("appointments")

    async def lock_allocations_for_appointments(
        self, tenant_id: UUID, appointment_ids: list[UUID]
    ) -> None:
        self.lock_calls.append("allocations")

    async def find_overlap_facts(self, **kwargs: Any) -> list[OverlapConflictFact]:
        return list(self._facts_for_kwargs(kwargs))

    def _facts_for_kwargs(self, kwargs: dict[str, Any]) -> list[OverlapConflictFact]:
        resource_ids = kwargs.get("resource_ids") or []
        if self.facts_by_resource:
            matched: list[OverlapConflictFact] = []
            for rid in resource_ids:
                matched.extend(self.facts_by_resource.get(rid, []))
            return matched
        return self.facts

    async def expire_conflicting_holds(self, **kwargs: Any) -> list[UUID]:
        return []

    async def add(self, appointment: Any) -> None:
        if (
            self.fail_on_add_index is not None
            and len(self.added_list) == self.fail_on_add_index
        ):
            raise RuntimeError("simulated mid-group failure")
        self.added = appointment
        self.added_list.append(appointment)

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


def _group_command(
    *,
    resource_ids: list[UUID],
    lines: list[ScheduleGroupLine] | None = None,
    **overrides: Any,
) -> ScheduleAppointmentGroupCommand:
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    if lines is None:
        lines = [
            ScheduleGroupLine(
                client_line_id=f"line-{idx}",
                service_id=new_uuid7(),
                resource_ids=(rid,),
                start_at_utc=start + timedelta(hours=idx),
                end_at_utc=start + timedelta(hours=idx, minutes=30),
            )
            for idx, rid in enumerate(resource_ids)
        ]
    base = dict(
        correlation_id=new_uuid7(),
        idempotency_key="group-key-1",
        request_fingerprint="group-fp-1",
        principal_id=new_uuid7(),
        actor_type="USER",
        tenant_id=new_uuid7(),
        beneficiary_patient_id=new_uuid7(),
        booker_person_id=None,
        lines=tuple(lines),
    )
    base.update(overrides)
    return ScheduleAppointmentGroupCommand(**base)


@pytest.mark.asyncio
async def test_group_atomic_success_locks_all_resources_once() -> None:
    uow = FakeUow()
    r1, r2, r3 = new_uuid7(), new_uuid7(), new_uuid7()
    # Deliberately unsorted input — handler must lock ASC once.
    appts = FakeAppointments()
    outbox = FakeOutbox()

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
    result = await handler.handle_group(_group_command(resource_ids=[r3, r1, r2]))
    assert result.replayed is False
    assert len(result.lines) == 3
    assert {line.client_line_id for line in result.lines} == {
        "line-0",
        "line-1",
        "line-2",
    }
    assert len(appts.added_list) == 3
    assert appts.locked_resource_orders[0] == sorted([r1, r2, r3])
    assert appts.lock_calls.count("resources") == 1
    assert uow.committed
    assert len(outbox.messages) == 3


@pytest.mark.asyncio
async def test_group_midway_failure_rolls_back_all() -> None:
    uow = FakeUow()
    r1, r2, r3 = new_uuid7(), new_uuid7(), new_uuid7()
    appts = FakeAppointments(fail_on_add_index=1)

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(),
        patient_display=FakePatientDisplay(),
    )
    with pytest.raises(RuntimeError, match="simulated mid-group failure"):
        await handler.handle_group(_group_command(resource_ids=[r1, r2, r3]))
    assert uow.rolled_back
    assert not uow.committed
    # One line may have been staged in-memory before failure; UoW rollback discards it.
    assert len(appts.added_list) == 1


@pytest.mark.asyncio
async def test_group_overlap_returns_per_line_conflicts() -> None:
    uow = FakeUow()
    patient_id = new_uuid7()
    conflict_id = new_uuid7()
    r_ok = new_uuid7()
    r_conflict = new_uuid7()
    start = datetime.now(timezone.utc)
    facts = [
        OverlapConflictFact(
            appointment_id=conflict_id,
            beneficiary_patient_id=patient_id,
            booking_channel="MANUAL_STAFF",
            capacity_pool="MANUAL",
            scheduled_start_at_utc=start,
            scheduled_end_at_utc=start + timedelta(minutes=30),
            resource_id=r_conflict,
            allocation_status="CONFIRMED",
        )
    ]
    appts = FakeAppointments(facts_by_resource={r_conflict: facts, r_ok: []})

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(True),
        patient_display=FakePatientDisplay({patient_id: "Ada Clinic"}),
    )
    lines = [
        ScheduleGroupLine(
            client_line_id="ok-line",
            service_id=new_uuid7(),
            resource_ids=(r_ok,),
            start_at_utc=start,
            end_at_utc=start + timedelta(minutes=30),
        ),
        ScheduleGroupLine(
            client_line_id="conflict-line",
            service_id=new_uuid7(),
            resource_ids=(r_conflict,),
            start_at_utc=start,
            end_at_utc=start + timedelta(minutes=30),
            acknowledge_overlap=False,
        ),
    ]
    with pytest.raises(GroupManualOverlapAcknowledgementRequired) as excinfo:
        await handler.handle_group(_group_command(resource_ids=[], lines=lines))
    assert set(excinfo.value.conflicts_by_line) == {"conflict-line"}
    assert (
        excinfo.value.conflicts_by_line["conflict-line"][0].display_safe_patient_name
        == "Ada Clinic"
    )
    assert uow.rolled_back
    assert appts.added_list == []


@pytest.mark.asyncio
async def test_group_intra_line_overlap_requires_ack() -> None:
    """Two draft lines on the same resource/time must surface per-line conflicts."""
    uow = FakeUow()
    resource_id = new_uuid7()
    start = datetime.now(timezone.utc)
    appts = FakeAppointments()
    handler = _handler(uow, appts, perms=FakePermissions(True))
    lines = [
        ScheduleGroupLine(
            client_line_id="line-a",
            service_id=new_uuid7(),
            resource_ids=(resource_id,),
            start_at_utc=start,
            end_at_utc=start + timedelta(minutes=30),
        ),
        ScheduleGroupLine(
            client_line_id="line-b",
            service_id=new_uuid7(),
            resource_ids=(resource_id,),
            start_at_utc=start,
            end_at_utc=start + timedelta(minutes=30),
        ),
    ]
    with pytest.raises(GroupManualOverlapAcknowledgementRequired) as excinfo:
        await handler.handle_group(_group_command(resource_ids=[], lines=lines))
    assert set(excinfo.value.conflicts_by_line) == {"line-a", "line-b"}
    assert appts.added_list == []
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_immediate_check_in_requires_permission() -> None:
    uow = FakeUow()
    handler = _handler(
        uow,
        FakeAppointments(),
        perms=FakePermissions(False),
    )
    with pytest.raises(UnauthorizedScheduling):
        await handler.handle(_command(immediate_check_in=True))
    assert uow.rolled_back


@pytest.mark.asyncio
async def test_immediate_check_in_sets_checked_in_status() -> None:
    uow = FakeUow()
    appts = FakeAppointments()
    outbox = FakeOutbox()

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=FakeIdempotency(),
        outbox=outbox,
        audit=FakeAudit(),
        permissions=FakePermissions(True),
        patient_display=FakePatientDisplay(),
    )
    result = await handler.handle(_command(immediate_check_in=True))
    assert result.status == "CHECKED_IN"
    assert appts.added is not None
    assert appts.added.status.value == "CHECKED_IN"
    assert any(m["message_type"] == "appointment.checked_in" for m in outbox.messages)
    assert uow.committed


@pytest.mark.asyncio
async def test_group_idempotent_replay_returns_same_payload() -> None:
    uow = FakeUow()
    r1, r2, r3 = new_uuid7(), new_uuid7(), new_uuid7()
    appts = FakeAppointments()
    idem = FakeIdempotency()

    @asynccontextmanager
    async def factory():
        yield uow

    handler = ScheduleAppointmentHandler(
        uow_factory=factory,
        appointments=appts,
        idempotency=idem,
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(),
        patient_display=FakePatientDisplay(),
    )
    command = _group_command(resource_ids=[r1, r2, r3])
    first = await handler.handle_group(command)
    assert first.replayed is False
    assert idem.completed

    uow2 = FakeUow()

    @asynccontextmanager
    async def factory2():
        yield uow2

    handler2 = ScheduleAppointmentHandler(
        uow_factory=factory2,
        appointments=FakeAppointments(),
        idempotency=idem,
        outbox=FakeOutbox(),
        audit=FakeAudit(),
        permissions=FakePermissions(),
        patient_display=FakePatientDisplay(),
    )
    replay = await handler2.handle_group(command)
    assert replay.replayed is True
    assert [line.appointment_id for line in replay.lines] == [
        line.appointment_id for line in first.lines
    ]
    assert uow2.committed
