"""ScheduleAppointmentHandler — clauses 185–201 / 779 / 782–783 + atomic groups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.scheduling.commands import (
    ScheduleAppointmentCommand,
    ScheduleAppointmentGroupCommand,
    ScheduleGroupLine,
)
from clinic_ecosystem.application.scheduling.exceptions import (
    ConflictDisplayItem,
    GroupManualOverlapAcknowledgementRequired,
    IdempotencyConflict,
    IdempotencyInProgress,
    ManualOverlapAcknowledgementRequired,
    UnauthorizedScheduling,
)
from clinic_ecosystem.application.scheduling.ports import (
    AppointmentRepository,
    AuditStore,
    IdempotencyStore,
    OutboxStore,
    PatientDisplayDirectory,
    PermissionService,
    UnitOfWork,
    validate_resource_set,
)
from clinic_ecosystem.domain.access.permissions import APPOINTMENTS_CHECK_IN
from clinic_ecosystem.domain.scheduling.conflicts import OverlapConflictFact
from clinic_ecosystem.domain.scheduling.exceptions import CapacityConflictException
from clinic_ecosystem.domain.scheduling.model import (
    Appointment,
    AppointmentStatus,
    CapacityPool,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

ALLOW_MANUAL_OVERBOOKING = "ALLOW_MANUAL_OVERBOOKING"
EXCLUDE_CONSTRAINT_NAME = "ex_online_resource_time"


@dataclass(slots=True)
class ScheduleAppointmentResult:
    appointment_id: UUID
    replayed: bool
    status: str | None = None


@dataclass(slots=True)
class ScheduleGroupLineResult:
    client_line_id: str
    appointment_id: UUID
    status: str


@dataclass(slots=True)
class ScheduleAppointmentGroupResult:
    lines: list[ScheduleGroupLineResult]
    replayed: bool


class ScheduleAppointmentHandler:
    def __init__(
        self,
        *,
        uow_factory,
        appointments: AppointmentRepository,
        idempotency: IdempotencyStore,
        outbox: OutboxStore,
        audit: AuditStore,
        permissions: PermissionService,
        patient_display: PatientDisplayDirectory,
    ) -> None:
        self._uow_factory = uow_factory
        self._appointments = appointments
        self._idempotency = idempotency
        self._outbox = outbox
        self._audit = audit
        self._permissions = permissions
        self._patient_display = patient_display

    async def handle(self, command: ScheduleAppointmentCommand) -> ScheduleAppointmentResult:
        owner_token = new_uuid7()
        async with self._uow_factory() as uow:
            await uow.bind_tenant(command.tenant_id)
            claim = await self._idempotency.claim(
                tenant_id=command.tenant_id,
                principal_id=command.principal_id,
                operation_scope=command.operation_scope,
                idempotency_key=command.idempotency_key,
                request_fingerprint=command.request_fingerprint,
                owner_token=owner_token,
            )
            status = claim["status"]
            if status == "COMPLETED":
                await uow.commit()
                payload = claim["response_payload"]
                return ScheduleAppointmentResult(
                    appointment_id=UUID(payload["appointment_id"]),
                    replayed=True,
                    status=payload.get("status"),
                )
            if status == "IN_PROGRESS":
                await uow.rollback()
                raise IdempotencyInProgress("idempotency owner active")
            if status == "FINGERPRINT_CONFLICT":
                await uow.rollback()
                raise IdempotencyConflict("idempotency fingerprint mismatch")

            try:
                result = await self._execute_business(uow, command)
            except Exception:
                # Unsuccessful MANUAL confirmation / any business failure rolls back
                # the entire UoW including the idempotency claim.
                await uow.rollback()
                raise

            await self._idempotency.complete(
                tenant_id=command.tenant_id,
                principal_id=command.principal_id,
                operation_scope=command.operation_scope,
                idempotency_key=command.idempotency_key,
                owner_token=owner_token,
                response_payload={
                    "appointment_id": str(result.appointment_id),
                    "status": result.status,
                },
            )
            await uow.commit()
            return result

    async def handle_group(
        self, command: ScheduleAppointmentGroupCommand
    ) -> ScheduleAppointmentGroupResult:
        """Persist all group lines in one UoW; fail together on any line error."""
        if not command.lines:
            raise CapacityConflictException("group requires at least one line")
        owner_token = new_uuid7()
        async with self._uow_factory() as uow:
            await uow.bind_tenant(command.tenant_id)
            claim = await self._idempotency.claim(
                tenant_id=command.tenant_id,
                principal_id=command.principal_id,
                operation_scope=command.operation_scope,
                idempotency_key=command.idempotency_key,
                request_fingerprint=command.request_fingerprint,
                owner_token=owner_token,
            )
            status = claim["status"]
            if status == "COMPLETED":
                await uow.commit()
                payload = claim["response_payload"]
                return ScheduleAppointmentGroupResult(
                    lines=[
                        ScheduleGroupLineResult(
                            client_line_id=item["client_line_id"],
                            appointment_id=UUID(item["appointment_id"]),
                            status=item["status"],
                        )
                        for item in payload["lines"]
                    ],
                    replayed=True,
                )
            if status == "IN_PROGRESS":
                await uow.rollback()
                raise IdempotencyInProgress("idempotency owner active")
            if status == "FINGERPRINT_CONFLICT":
                await uow.rollback()
                raise IdempotencyConflict("idempotency fingerprint mismatch")

            try:
                result = await self._execute_group_business(uow, command)
            except Exception:
                await uow.rollback()
                raise

            await self._idempotency.complete(
                tenant_id=command.tenant_id,
                principal_id=command.principal_id,
                operation_scope=command.operation_scope,
                idempotency_key=command.idempotency_key,
                owner_token=owner_token,
                response_payload={
                    "lines": [
                        {
                            "client_line_id": line.client_line_id,
                            "appointment_id": str(line.appointment_id),
                            "status": line.status,
                        }
                        for line in result.lines
                    ]
                },
            )
            await uow.commit()
            return result

    async def _execute_group_business(
        self, uow: UnitOfWork, command: ScheduleAppointmentGroupCommand
    ) -> ScheduleAppointmentGroupResult:
        if command.immediate_check_in:
            await self._require_check_in_permission(command.tenant_id, command.principal_id)

        # Clause 783: collect ALL resource IDs across lines, sort ASC, lock once.
        all_resource_ids = sorted({rid for line in command.lines for rid in line.resource_ids})
        await self._appointments.lock_resources(command.tenant_id, list(all_resource_ids))

        # Pre-validate overlaps for every line before any insert (all-or-nothing ack).
        audit_by_line: dict[str, list[dict[str, Any]] | None] = {}
        conflicts_by_line: dict[str, list[ConflictDisplayItem]] = {}
        for line in command.lines:
            line_cmd = self._line_to_command(command, line)
            try:
                audit_by_line[line.client_line_id] = await self._manual_overlap_gate(
                    line_cmd, resource_ids=sorted(line.resource_ids)
                )
            except ManualOverlapAcknowledgementRequired as exc:
                conflicts_by_line[line.client_line_id] = list(exc.conflicts)

        if conflicts_by_line:
            raise GroupManualOverlapAcknowledgementRequired(conflicts_by_line)

        results: list[ScheduleGroupLineResult] = []
        for line in command.lines:
            line_cmd = self._line_to_command(command, line)
            persisted = await self._persist_appointment(
                uow,
                line_cmd,
                resource_ids=sorted(line.resource_ids),
                audit_conflict_snapshot=audit_by_line[line.client_line_id],
                skip_resource_lock=True,
            )
            results.append(
                ScheduleGroupLineResult(
                    client_line_id=line.client_line_id,
                    appointment_id=persisted.appointment_id,
                    status=persisted.status or AppointmentStatus.CONFIRMED.value,
                )
            )
        return ScheduleAppointmentGroupResult(lines=results, replayed=False)

    def _line_to_command(
        self, group: ScheduleAppointmentGroupCommand, line: ScheduleGroupLine
    ) -> ScheduleAppointmentCommand:
        return ScheduleAppointmentCommand(
            correlation_id=group.correlation_id,
            idempotency_key=group.idempotency_key,
            request_fingerprint=group.request_fingerprint,
            principal_id=group.principal_id,
            actor_type=group.actor_type,
            tenant_id=group.tenant_id,
            beneficiary_patient_id=group.beneficiary_patient_id,
            booker_person_id=group.booker_person_id,
            patient_booking_note=line.patient_booking_note,
            service_id=line.service_id,
            booking_channel=group.booking_channel,
            capacity_pool=group.capacity_pool,
            resource_ids=tuple(sorted(line.resource_ids)),
            start_at_utc=line.start_at_utc,
            end_at_utc=line.end_at_utc,
            hold_expires_at_utc=None,
            acknowledge_overlap=line.acknowledge_overlap,
            acknowledged_conflict_ids=line.acknowledged_conflict_ids,
            immediate_check_in=group.immediate_check_in,
        )

    async def _execute_business(
        self, uow: UnitOfWork, command: ScheduleAppointmentCommand
    ) -> ScheduleAppointmentResult:
        if command.immediate_check_in:
            await self._require_check_in_permission(command.tenant_id, command.principal_id)

        resource_ids = sorted(command.resource_ids)
        await self._appointments.lock_resources(command.tenant_id, list(resource_ids))

        audit_conflict_snapshot: list[dict[str, Any]] | None = None
        if command.capacity_pool == CapacityPool.ONLINE:
            now = datetime.now(timezone.utc)
            await self._appointments.expire_conflicting_holds(
                tenant_id=command.tenant_id,
                resource_ids=list(resource_ids),
                start_at_utc=command.start_at_utc,
                end_at_utc=command.end_at_utc,
                now_utc=now,
            )
        else:
            audit_conflict_snapshot = await self._manual_overlap_gate(
                command, resource_ids=list(resource_ids)
            )

        return await self._persist_appointment(
            uow,
            command,
            resource_ids=list(resource_ids),
            audit_conflict_snapshot=audit_conflict_snapshot,
            skip_resource_lock=True,
        )

    async def _persist_appointment(
        self,
        uow: UnitOfWork,
        command: ScheduleAppointmentCommand,
        *,
        resource_ids: list[UUID],
        audit_conflict_snapshot: list[dict[str, Any]] | None,
        skip_resource_lock: bool,
    ) -> ScheduleAppointmentResult:
        now = datetime.now(timezone.utc)
        if not skip_resource_lock:
            await self._appointments.lock_resources(command.tenant_id, list(resource_ids))

        requirements = await self._appointments.get_service_requirements(
            command.tenant_id, command.service_id
        )
        resource_types = await self._appointments.get_resource_types(
            command.tenant_id, list(resource_ids)
        )
        if len(resource_types) != len(resource_ids):
            missing = set(resource_ids) - set(resource_types)
            raise CapacityConflictException(f"unknown resources: {missing}")

        allocation_requests = validate_resource_set(
            requirements, resource_types, list(resource_ids)
        )

        initial_status = self._initial_status(command)

        appointment = Appointment.schedule(
            tenant_id=command.tenant_id,
            beneficiary_patient_id=command.beneficiary_patient_id,
            booker_person_id=command.booker_person_id,
            patient_booking_note=command.patient_booking_note,
            service_id=command.service_id,
            booking_channel=command.booking_channel,
            capacity_pool=command.capacity_pool,
            start_at_utc=command.start_at_utc,
            end_at_utc=command.end_at_utc,
            resource_allocations=allocation_requests,
            hold_expires_at_utc=command.hold_expires_at_utc,
            initial_status=initial_status,
            now_utc=now,
        )

        try:
            await self._appointments.add(appointment)
            await uow.flush()
        except Exception as exc:  # noqa: BLE001
            if _is_exclude_violation(exc):
                raise CapacityConflictException("online capacity conflict") from exc
            raise

        if (
            appointment.status == AppointmentStatus.PENDING_PAYMENT_HOLD
            and appointment.hold_expires_at_utc is not None
        ):
            await self._appointments.enqueue_hold_expiry(
                tenant_id=command.tenant_id,
                appointment_id=appointment.id,
                due_at_utc=appointment.hold_expires_at_utc,
            )

        for event in appointment.domain_events:
            await self._outbox.stage(
                tenant_id=command.tenant_id,
                message_type=str(event["event_type"]),
                payload=event,
            )

        if appointment.status == AppointmentStatus.CHECKED_IN:
            await self._outbox.stage(
                tenant_id=command.tenant_id,
                message_type="appointment.checked_in",
                payload={
                    "event_type": "appointment.checked_in",
                    "appointment_id": str(appointment.id),
                    "aggregate_version": appointment.aggregate_version,
                    "immediate_check_in": True,
                },
            )
            await self._audit.append(
                tenant_id=command.tenant_id,
                actor_type=command.actor_type,
                actor_id=command.principal_id,
                operation="appointment.checked_in",
                target_type="appointment",
                target_id=appointment.id,
                details={
                    "correlation_id": str(command.correlation_id),
                    "immediate_check_in": True,
                    "from_status": AppointmentStatus.CONFIRMED.value,
                    "to_status": AppointmentStatus.CHECKED_IN.value,
                },
            )

        if audit_conflict_snapshot is not None:
            await self._audit.append(
                tenant_id=command.tenant_id,
                actor_type=command.actor_type,
                actor_id=command.principal_id,
                operation="ALLOW_MANUAL_OVERBOOKING",
                target_type="appointment",
                target_id=appointment.id,
                details={
                    "correlation_id": str(command.correlation_id),
                    "conflict_appointment_ids": [
                        item["appointment_id"] for item in audit_conflict_snapshot
                    ],
                    "conflict_snapshot": audit_conflict_snapshot,
                },
            )

        return ScheduleAppointmentResult(
            appointment_id=appointment.id,
            replayed=False,
            status=appointment.status.value,
        )

    @staticmethod
    def _initial_status(command: ScheduleAppointmentCommand) -> AppointmentStatus:
        if command.capacity_pool == CapacityPool.MANUAL:
            if command.immediate_check_in:
                return AppointmentStatus.CHECKED_IN
            return AppointmentStatus.CONFIRMED
        if command.hold_expires_at_utc is not None:
            return AppointmentStatus.PENDING_PAYMENT_HOLD
        return AppointmentStatus.CONFIRMED

    async def _require_check_in_permission(
        self, tenant_id: UUID, principal_id: UUID
    ) -> None:
        allowed = await self._permissions.principal_has(
            tenant_id=tenant_id,
            principal_id=principal_id,
            permission_code=APPOINTMENTS_CHECK_IN,
        )
        if not allowed:
            raise UnauthorizedScheduling(APPOINTMENTS_CHECK_IN)

    async def _manual_overlap_gate(
        self, command: ScheduleAppointmentCommand, *, resource_ids: list[UUID]
    ) -> list[dict[str, Any]] | None:
        """Resource→Appointment→Allocation locks, authz, ack, pre-insert snapshot."""
        candidate_ids = await self._appointments.discover_overlapping_appointment_ids(
            tenant_id=command.tenant_id,
            resource_ids=resource_ids,
            start_at_utc=command.start_at_utc,
            end_at_utc=command.end_at_utc,
        )
        # Clause 783 steps 2–3 under the same UoW.
        await self._appointments.lock_appointments(command.tenant_id, candidate_ids)
        await self._appointments.lock_allocations_for_appointments(
            command.tenant_id, candidate_ids
        )
        facts = await self._appointments.find_overlap_facts(
            tenant_id=command.tenant_id,
            resource_ids=resource_ids,
            start_at_utc=command.start_at_utc,
            end_at_utc=command.end_at_utc,
        )
        if not facts:
            return None

        # Authz before any display-safe name disclosure.
        allowed = await self._permissions.principal_has(
            tenant_id=command.tenant_id,
            principal_id=command.principal_id,
            permission_code=ALLOW_MANUAL_OVERBOOKING,
        )
        if not allowed:
            raise UnauthorizedScheduling(ALLOW_MANUAL_OVERBOOKING)

        display = await self._to_display_conflicts(command.tenant_id, facts)
        current_ids = _unique_appointment_ids(facts)
        if not command.acknowledge_overlap:
            raise ManualOverlapAcknowledgementRequired(display)
        if set(command.acknowledged_conflict_ids) != current_ids:
            raise ManualOverlapAcknowledgementRequired(display)

        # Immutable pre-insert audit snapshot: IDs/channels/times only (no names).
        return _audit_snapshot(facts)

    async def _to_display_conflicts(
        self, tenant_id: UUID, facts: list[OverlapConflictFact]
    ) -> list[ConflictDisplayItem]:
        patient_ids = sorted({f.beneficiary_patient_id for f in facts})
        names = await self._patient_display.display_safe_names(
            tenant_id=tenant_id, patient_ids=patient_ids
        )
        by_appointment: dict[UUID, OverlapConflictFact] = {}
        for fact in facts:
            by_appointment.setdefault(fact.appointment_id, fact)
        return [
            ConflictDisplayItem(
                appointment_id=appt_id,
                display_safe_patient_name=names.get(
                    fact.beneficiary_patient_id, ""
                ),
                booking_channel=fact.booking_channel,
                scheduled_start_at_utc=fact.scheduled_start_at_utc,
                scheduled_end_at_utc=fact.scheduled_end_at_utc,
            )
            for appt_id, fact in sorted(by_appointment.items(), key=lambda x: str(x[0]))
        ]


def _unique_appointment_ids(facts: list[OverlapConflictFact]) -> set[UUID]:
    return {f.appointment_id for f in facts}


def _audit_snapshot(facts: list[OverlapConflictFact]) -> list[dict[str, Any]]:
    by_appointment: dict[UUID, OverlapConflictFact] = {}
    for fact in facts:
        by_appointment.setdefault(fact.appointment_id, fact)
    return [
        {
            "appointment_id": str(fact.appointment_id),
            "beneficiary_patient_id": str(fact.beneficiary_patient_id),
            "booking_channel": fact.booking_channel,
            "capacity_pool": fact.capacity_pool,
            "scheduled_start_at_utc": fact.scheduled_start_at_utc.isoformat(),
            "scheduled_end_at_utc": fact.scheduled_end_at_utc.isoformat(),
        }
        for _, fact in sorted(by_appointment.items(), key=lambda x: str(x[0]))
    ]


def _is_exclude_violation(exc: BaseException) -> bool:
    text = str(exc).lower()
    if EXCLUDE_CONSTRAINT_NAME.lower() in text:
        return True
    if "exclusion constraint" in text or "conflicting key value" in text:
        return True
    cause = getattr(exc, "orig", None) or getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return _is_exclude_violation(cause)
    return False
