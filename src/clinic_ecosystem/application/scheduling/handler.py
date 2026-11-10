"""ScheduleAppointmentHandler — clauses 185–201 + v3.0 amendment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import (
    IdempotencyConflict,
    IdempotencyInProgress,
    UnauthorizedScheduling,
)
from clinic_ecosystem.application.scheduling.ports import (
    AppointmentRepository,
    AuditStore,
    IdempotencyStore,
    OutboxStore,
    PermissionService,
    UnitOfWork,
    validate_resource_set,
)
from clinic_ecosystem.domain.scheduling.exceptions import (
    CapacityConflictException,
    ManualOverlapAcknowledgementRequired,
)
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
    ) -> None:
        self._uow_factory = uow_factory
        self._appointments = appointments
        self._idempotency = idempotency
        self._outbox = outbox
        self._audit = audit
        self._permissions = permissions

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
                return ScheduleAppointmentResult(
                    appointment_id=UUID(claim["response_payload"]["appointment_id"]),
                    replayed=True,
                )
            if status == "IN_PROGRESS":
                await uow.rollback()
                raise IdempotencyInProgress("idempotency owner active")
            if status == "FINGERPRINT_CONFLICT":
                await uow.rollback()
                raise IdempotencyConflict("idempotency fingerprint mismatch")

            result = await self._execute_business(uow, command)
            await self._idempotency.complete(
                tenant_id=command.tenant_id,
                principal_id=command.principal_id,
                operation_scope=command.operation_scope,
                idempotency_key=command.idempotency_key,
                owner_token=owner_token,
                response_payload={"appointment_id": str(result.appointment_id)},
            )
            await uow.commit()
            return result

    async def _execute_business(
        self, uow: UnitOfWork, command: ScheduleAppointmentCommand
    ) -> ScheduleAppointmentResult:
        now = datetime.now(timezone.utc)
        resource_ids = sorted(command.resource_ids)  # lock order: resource.id ASC

        # Resolve resources without business locks first (clause 783).
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

        # Global lock order step 1: BookableResource rows ASC.
        await self._appointments.lock_resources(command.tenant_id, list(resource_ids))

        if command.capacity_pool == CapacityPool.ONLINE:
            await self._appointments.expire_conflicting_holds(
                tenant_id=command.tenant_id,
                resource_ids=list(resource_ids),
                start_at_utc=command.start_at_utc,
                end_at_utc=command.end_at_utc,
                now_utc=now,
            )
        else:
            overlaps = await self._appointments.find_overlaps(
                tenant_id=command.tenant_id,
                resource_ids=list(resource_ids),
                start_at_utc=command.start_at_utc,
                end_at_utc=command.end_at_utc,
            )
            if overlaps:
                if not command.acknowledge_overlap:
                    raise ManualOverlapAcknowledgementRequired(overlaps)
                allowed = await self._permissions.principal_has(
                    tenant_id=command.tenant_id,
                    principal_id=command.principal_id,
                    permission_code=ALLOW_MANUAL_OVERBOOKING,
                )
                if not allowed:
                    raise UnauthorizedScheduling(ALLOW_MANUAL_OVERBOOKING)
                # Re-check conflict list after locks (clause 779).
                overlaps_again = await self._appointments.find_overlaps(
                    tenant_id=command.tenant_id,
                    resource_ids=list(resource_ids),
                    start_at_utc=command.start_at_utc,
                    end_at_utc=command.end_at_utc,
                )
                if _conflict_ids(overlaps) != _conflict_ids(overlaps_again):
                    raise ManualOverlapAcknowledgementRequired(overlaps_again)

        initial_status = (
            AppointmentStatus.PENDING_PAYMENT_HOLD
            if command.capacity_pool == CapacityPool.ONLINE
            and command.hold_expires_at_utc is not None
            else AppointmentStatus.CONFIRMED
            if command.capacity_pool == CapacityPool.MANUAL
            else AppointmentStatus.PENDING_PAYMENT_HOLD
        )
        if command.capacity_pool == CapacityPool.ONLINE and command.hold_expires_at_utc is None:
            initial_status = AppointmentStatus.CONFIRMED

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
        except Exception as exc:  # noqa: BLE001 — translate PG EXCLUDE
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

        if command.capacity_pool == CapacityPool.MANUAL and command.acknowledge_overlap:
            await self._audit.append(
                tenant_id=command.tenant_id,
                actor_type=command.actor_type,
                actor_id=command.principal_id,
                operation="ALLOW_MANUAL_OVERBOOKING",
                target_type="appointment",
                target_id=appointment.id,
                details={
                    "correlation_id": str(command.correlation_id),
                    "conflict_snapshot": await self._appointments.find_overlaps(
                        tenant_id=command.tenant_id,
                        resource_ids=list(resource_ids),
                        start_at_utc=command.start_at_utc,
                        end_at_utc=command.end_at_utc,
                    ),
                },
            )

        return ScheduleAppointmentResult(appointment_id=appointment.id, replayed=False)


def _conflict_ids(overlaps: list[dict[str, Any]]) -> set[str]:
    return {str(item["appointment_id"]) for item in overlaps}


def _is_exclude_violation(exc: BaseException) -> bool:
    text = str(exc).lower()
    if EXCLUDE_CONSTRAINT_NAME.lower() in text:
        return True
    # asyncpg / SQLAlchemy exclusion violation markers
    if "exclusion constraint" in text or "conflicting key value" in text:
        return True
    cause = getattr(exc, "orig", None) or getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return _is_exclude_violation(cause)
    return False
