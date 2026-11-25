"""Approved lifecycle operations for staff-booked appointments (Workstream D).

Only operations with a source-grounded contract are exposed:
* cancel  (CONFIRMED -> CANCELLED) for MANUAL pool appointments,
* reschedule of CONFIRMED MANUAL appointments with the existing overlap
  acknowledgement contract (clause 779) and lock order (clause 783).
Check-in, completion and no-show transitions are intentionally absent because the
transition policy is unspecified (see ACR-BETA02-001).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.shared.actor import Actor
from clinic_ecosystem.application.shared.errors import (
    Conflict,
    Forbidden,
    NotFound,
    PreconditionFailed,
    ValidationFailed,
)
from clinic_ecosystem.domain.access.permissions import ALLOW_MANUAL_OVERBOOKING
from clinic_ecosystem.infrastructure.persistence.appointment_admin import SqlAppointmentAdmin
from clinic_ecosystem.infrastructure.persistence.appointment_repository import (
    SqlAppointmentRepository,
)
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.outbox import SqlOutboxStore
from clinic_ecosystem.infrastructure.persistence.patient_display import SqlPatientDisplayDirectory
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

MANUAL_POOL = "MANUAL"
MUTABLE_STATUS = "CONFIRMED"
MAX_REASON = 200


class AppointmentLifecycleService:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow
        self._admin = SqlAppointmentAdmin(uow.session)
        self._repo = SqlAppointmentRepository(uow.session)
        self._audit = SqlAuditStore(uow.session)
        self._outbox = SqlOutboxStore(uow.session)
        self._display = SqlPatientDisplayDirectory(uow.session)

    async def _lock_and_load(
        self, actor: Actor, appointment_id: UUID, expected_version: int,
        extra_appointment_ids: list[UUID] | None = None,
    ) -> dict[str, Any]:
        """Clause 783 order: resources ASC, appointments ASC, allocations ASC."""
        appt = await self._admin.get_appointment(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        if appt is None:
            raise NotFound("Appointment not found", code="appointment_not_found")
        allocations = await self._admin.get_allocations(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        resource_ids = sorted({a["resource_id"] for a in allocations})
        await self._repo.lock_resources(actor.tenant_id, resource_ids)
        ids = sorted({appointment_id, *(extra_appointment_ids or [])})
        await self._repo.lock_appointments(actor.tenant_id, ids)
        await self._repo.lock_allocations_for_appointments(actor.tenant_id, ids)
        appt = await self._admin.get_appointment(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        if appt is None:
            raise NotFound("Appointment not found", code="appointment_not_found")
        if appt["aggregate_version"] != expected_version:
            raise PreconditionFailed(
                "Appointment was modified by someone else",
                extra={"current_version": appt["aggregate_version"]},
            )
        appt["resource_ids"] = resource_ids
        return appt

    @staticmethod
    def _require_mutable(appt: dict[str, Any]) -> None:
        if appt["capacity_pool"] != MANUAL_POOL:
            raise Conflict(
                "Only staff-booked (manual pool) appointments can be changed here",
                code="operation_not_supported_for_pool",
            )
        if appt["status"] != MUTABLE_STATUS:
            raise Conflict(
                "Appointment status does not allow this operation",
                code="invalid_status_transition",
                extra={"current_status": appt["status"]},
            )

    async def cancel(
        self, actor: Actor, appointment_id: UUID, expected_version: int, reason: str | None
    ) -> dict[str, Any]:
        reason = (reason or "").strip() or None
        if reason and len(reason) > MAX_REASON:
            raise ValidationFailed("Reason is too long", code="reason_too_long")
        appt = await self._lock_and_load(actor, appointment_id, expected_version)
        self._require_mutable(appt)
        now = datetime.now(timezone.utc)
        version = await self._admin.transition_appointment(
            tenant_id=actor.tenant_id, appointment_id=appointment_id,
            expected_version=expected_version, new_status="CANCELLED",
            start_at_utc=None, end_at_utc=None, now=now,
        )
        if version is None:
            raise PreconditionFailed("Appointment was modified by someone else")
        await self._admin.cancel_allocations(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        await self._audit.append(
            tenant_id=actor.tenant_id, actor_type="USER_ACCOUNT", actor_id=actor.account_id,
            operation="appointment.cancelled", target_type="appointment",
            target_id=appointment_id,
            details={"from_status": appt["status"], "to_status": "CANCELLED",
                     "from_version": expected_version, "to_version": version,
                     "reason": reason},
        )
        await self._outbox.stage(
            tenant_id=actor.tenant_id, message_type="appointment.cancelled",
            payload={"event_type": "appointment.cancelled",
                     "appointment_id": str(appointment_id),
                     "aggregate_version": version},
        )
        return {"appointment_id": str(appointment_id), "status": "CANCELLED",
                "aggregate_version": version}

    async def reschedule(
        self,
        actor: Actor,
        granted: set[str],
        appointment_id: UUID,
        expected_version: int,
        start_at_utc: datetime,
        end_at_utc: datetime,
        acknowledge_overlap: bool,
        acknowledged_conflict_ids: list[UUID],
    ) -> dict[str, Any]:
        if end_at_utc <= start_at_utc:
            raise ValidationFailed("end must be after start", code="invalid_time_range")
        current = await self._admin.get_appointment(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        if current is None:
            raise NotFound("Appointment not found", code="appointment_not_found")
        allocations = await self._admin.get_allocations(
            tenant_id=actor.tenant_id, appointment_id=appointment_id
        )
        resource_ids = sorted({a["resource_id"] for a in allocations})
        await self._repo.lock_resources(actor.tenant_id, resource_ids)
        candidates = [
            c
            for c in await self._repo.discover_overlapping_appointment_ids(
                tenant_id=actor.tenant_id, resource_ids=resource_ids,
                start_at_utc=start_at_utc, end_at_utc=end_at_utc,
            )
            if c != appointment_id
        ]
        appt = await self._lock_and_load(actor, appointment_id, expected_version, candidates)
        self._require_mutable(appt)
        if (appt["scheduled_start_at_utc"], appt["scheduled_end_at_utc"]) == (
            start_at_utc, end_at_utc,
        ):
            raise ValidationFailed("New time equals the current time", code="no_change")

        facts = [
            f
            for f in await self._repo.find_overlap_facts(
                tenant_id=actor.tenant_id, resource_ids=resource_ids,
                start_at_utc=start_at_utc, end_at_utc=end_at_utc,
            )
            if f.appointment_id != appointment_id
        ]
        snapshot: list[dict[str, Any]] | None = None
        if facts:
            if ALLOW_MANUAL_OVERBOOKING not in granted:
                raise Forbidden("Manual overlap is not authorized", code="permission_denied")
            current_ids = {f.appointment_id for f in facts}
            if not acknowledge_overlap or set(acknowledged_conflict_ids) != current_ids:
                raise Conflict(
                    "Overlap acknowledgement is required",
                    code="manual_overlap_acknowledgement_required",
                    extra={"conflicts": await self._display_conflicts(actor, facts)},
                )
            snapshot = [
                {
                    "appointment_id": str(f.appointment_id),
                    "booking_channel": f.booking_channel,
                    "capacity_pool": f.capacity_pool,
                    "scheduled_start_at_utc": f.scheduled_start_at_utc.isoformat(),
                    "scheduled_end_at_utc": f.scheduled_end_at_utc.isoformat(),
                }
                for f in {f.appointment_id: f for f in facts}.values()
            ]

        now = datetime.now(timezone.utc)
        version = await self._admin.transition_appointment(
            tenant_id=actor.tenant_id, appointment_id=appointment_id,
            expected_version=expected_version, new_status=None,
            start_at_utc=start_at_utc, end_at_utc=end_at_utc, now=now,
        )
        if version is None:
            raise PreconditionFailed("Appointment was modified by someone else")
        await self._admin.move_allocations(
            tenant_id=actor.tenant_id, appointment_id=appointment_id,
            start_at_utc=start_at_utc, end_at_utc=end_at_utc,
        )
        await self._audit.append(
            tenant_id=actor.tenant_id, actor_type="USER_ACCOUNT", actor_id=actor.account_id,
            operation="appointment.rescheduled", target_type="appointment",
            target_id=appointment_id,
            details={
                "from_start_utc": appt["scheduled_start_at_utc"].isoformat(),
                "from_end_utc": appt["scheduled_end_at_utc"].isoformat(),
                "to_start_utc": start_at_utc.isoformat(),
                "to_end_utc": end_at_utc.isoformat(),
                "from_version": expected_version, "to_version": version,
                "overlap_acknowledged": snapshot is not None,
            },
        )
        if snapshot is not None:
            await self._audit.append(
                tenant_id=actor.tenant_id, actor_type="USER_ACCOUNT", actor_id=actor.account_id,
                operation=ALLOW_MANUAL_OVERBOOKING, target_type="appointment",
                target_id=appointment_id,
                details={"conflict_appointment_ids": [s["appointment_id"] for s in snapshot],
                         "conflict_snapshot": snapshot},
            )
        await self._outbox.stage(
            tenant_id=actor.tenant_id, message_type="appointment.rescheduled",
            payload={"event_type": "appointment.rescheduled",
                     "appointment_id": str(appointment_id),
                     "scheduled_start_at_utc": start_at_utc.isoformat(),
                     "scheduled_end_at_utc": end_at_utc.isoformat(),
                     "aggregate_version": version},
        )
        return {"appointment_id": str(appointment_id), "status": appt["status"],
                "aggregate_version": version}

    async def _display_conflicts(self, actor: Actor, facts) -> list[dict[str, Any]]:
        names = await self._display.display_safe_names(
            tenant_id=actor.tenant_id,
            patient_ids=sorted({f.beneficiary_patient_id for f in facts}),
        )
        first: dict[UUID, Any] = {}
        for fact in facts:
            first.setdefault(fact.appointment_id, fact)
        return [
            {
                "appointment_id": str(appt_id),
                "display_safe_patient_name": names.get(f.beneficiary_patient_id, ""),
                "booking_channel": f.booking_channel,
                "scheduled_start_at_utc": f.scheduled_start_at_utc.isoformat(),
                "scheduled_end_at_utc": f.scheduled_end_at_utc.isoformat(),
            }
            for appt_id, f in sorted(first.items(), key=lambda kv: str(kv[0]))
        ]
