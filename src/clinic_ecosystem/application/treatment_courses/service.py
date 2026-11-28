"""Treatment-course commands (pay-per-session; prepaid fail-closed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.shared.errors import Conflict, ValidationFailed
from clinic_ecosystem.domain.treatment_courses.rolling import (
    compute_rolling_reminder_plan,
    defer_for_quiet_hours,
    tehran_date_to_utc_noon,
)
from clinic_ecosystem.infrastructure.persistence.outbox import SqlOutboxStore
from clinic_ecosystem.infrastructure.persistence.treatment_courses import (
    SqlTreatmentCourseStore,
)
from clinic_ecosystem.infrastructure.timezones import require_tehran_zoneinfo
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(frozen=True, slots=True)
class SessionCompletionResult:
    course_id: UUID
    session_id: UUID
    session_no: int
    suggested_date_tehran: date
    reminder_date_tehran: date
    schedule_version: int
    replayed: bool


class TreatmentCourseService:
    """Enroll / complete / correct / lifecycle for disposable courses."""

    def __init__(self, session) -> None:
        self._session = session
        self._store = SqlTreatmentCourseStore(session)
        self._outbox = SqlOutboxStore(session)

    async def enroll_pay_per_session(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        template_version_id: UUID | None,
        planned_sessions: int,
        interval_kind: str = "JALALI_CALENDAR_MONTH",
        interval_value: int = 1,
        reminder_lead_days: int = 2,
        actor_user_id: UUID,
    ) -> dict[str, Any]:
        if planned_sessions <= 0:
            raise ValidationFailed("planned_sessions must be positive")
        # Explicit fail-closed: never enable prepaid on this path.
        course_id = new_uuid7()
        now = datetime.now(timezone.utc)
        row = await self._store.insert_course(
            tenant_id=tenant_id,
            course_id=course_id,
            patient_id=patient_id,
            service_id=service_id,
            template_version_id=template_version_id,
            planned_sessions=planned_sessions,
            interval_kind=interval_kind,
            interval_value=interval_value,
            reminder_lead_days=reminder_lead_days,
            billing_mode="PAY_PER_SESSION",
            now_utc=now,
        )
        await self._outbox.stage(
            tenant_id=tenant_id,
            message_type="course.enrolled",
            payload={
                "course_id": str(course_id),
                "patient_id": str(patient_id),
                "service_id": str(service_id),
                "billing_mode": "PAY_PER_SESSION",
                "actor_user_id": str(actor_user_id),
            },
        )
        return row

    async def record_session_completion(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        service_record_id: UUID,
        appointment_id: UUID | None,
        idempotency_key: str,
        expected_version: int | None = None,
        now_utc: datetime | None = None,
    ) -> SessionCompletionResult:
        now = now_utc or datetime.now(timezone.utc)
        tehran = require_tehran_zoneinfo()
        completion_tehran = now.astimezone(tehran).date()

        existing = await self._store.find_session_by_idempotency(
            tenant_id=tenant_id, course_id=course_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            course = await self._store.get_course_for_update(tenant_id, course_id)
            return SessionCompletionResult(
                course_id=course_id,
                session_id=existing["id"],
                session_no=int(existing["session_no"]),
                suggested_date_tehran=course["next_suggested_date_tehran"],
                reminder_date_tehran=existing.get("reminder_date_tehran")
                or course["next_suggested_date_tehran"],
                schedule_version=int(course["current_schedule_version"]),
                replayed=True,
            )

        course = await self._store.get_course_for_update(tenant_id, course_id)
        if expected_version is not None and int(course["aggregate_version"]) != expected_version:
            raise Conflict("course version conflict", code="course_version_conflict")
        if course["status"] not in {"ACTIVE", "REASSESSMENT_REQUIRED"}:
            raise Conflict("course not completable", code="course_not_active")
        if course["billing_mode"] != "PAY_PER_SESSION":
            raise Conflict("prepaid path disabled", code="prepaid_disabled")
        if bool(course["prepaid_entitlement_enabled"]):
            raise Conflict("prepaid entitlement disabled", code="prepaid_disabled")

        evidence = await self._store.require_performed_record(
            tenant_id=tenant_id,
            service_record_id=service_record_id,
            patient_id=course["patient_id"],
            service_id=course["service_id"],
        )
        # Completion date follows actual evidence time (Tehran), not payment/booking.
        evidence_utc: datetime = evidence["occurred_at_utc"]
        if evidence_utc.tzinfo is None:
            evidence_utc = evidence_utc.replace(tzinfo=timezone.utc)
        completion_tehran = evidence_utc.astimezone(tehran).date()

        completed = int(course["completed_session_count"])
        if completed >= int(course["planned_sessions"]):
            raise Conflict("course already complete", code="course_already_complete")
        session_no = completed + 1

        plan = compute_rolling_reminder_plan(
            completion_tehran=completion_tehran,
            interval_kind=str(course["interval_kind"]),
            interval_value=int(course["interval_value"]),
            reminder_lead_days=int(course["reminder_lead_days"]),
            scheduling_mode=str(course["scheduling_mode"]),
        )

        session_id = new_uuid7()
        await self._store.insert_completed_session(
            tenant_id=tenant_id,
            session_id=session_id,
            course_id=course_id,
            patient_id=course["patient_id"],
            service_id=course["service_id"],
            session_no=session_no,
            appointment_id=appointment_id,
            service_record_id=service_record_id,
            completion_tehran_date=completion_tehran,
            completion_at_utc=evidence_utc,
            idempotency_key=idempotency_key,
            now_utc=now,
        )

        new_completed = completed + 1
        new_status = "COMPLETED" if new_completed >= int(course["planned_sessions"]) else "ACTIVE"
        # Long-gap reassessment is evaluated against wall clock, not payment time.
        gap = (now.astimezone(tehran).date() - completion_tehran).days
        if new_status == "ACTIVE" and gap > int(course["long_gap_days"]):
            new_status = "REASSESSMENT_REQUIRED"

        schedule_version = int(course["current_schedule_version"]) + 1
        await self._store.supersede_open_schedules(
            tenant_id=tenant_id, course_id=course_id, now_utc=now
        )
        policy_id = new_uuid7()
        await self._store.insert_policy_snapshot(
            tenant_id=tenant_id,
            snapshot_id=policy_id,
            course_id=course_id,
            schedule_version=schedule_version,
            reminder_lead_days=int(course["reminder_lead_days"]),
            quiet_hours_start_minute=int(course["quiet_hours_start_minute"]),
            quiet_hours_end_minute=int(course["quiet_hours_end_minute"]),
            max_reminder_attempts=int(course["max_reminder_attempts"]),
            now_utc=now,
        )

        suppressed = await self._store.has_qualifying_future_appointment(
            tenant_id=tenant_id,
            patient_id=course["patient_id"],
            service_id=course["service_id"],
            from_tehran=now.astimezone(tehran).date(),
            to_tehran=plan.suggested_tehran,
        )
        schedule_id = new_uuid7()
        logical_key = f"course:{course_id}:v{schedule_version}:remind:{plan.reminder_tehran.isoformat()}"
        schedule_status = "SUPPRESSED" if suppressed else "SCHEDULED"
        await self._store.insert_recall_schedule(
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            course_id=course_id,
            patient_id=course["patient_id"],
            service_id=course["service_id"],
            schedule_version=schedule_version,
            cycle_no=session_no,
            source_session_id=session_id,
            suggested_date_tehran=plan.suggested_tehran,
            reminder_date_tehran=plan.reminder_tehran,
            scheduled_at_utc=tehran_date_to_utc_noon(plan.reminder_tehran),
            status=schedule_status,
            suppress_reason="QUALIFYING_FUTURE_APPOINTMENT" if suppressed else None,
            policy_snapshot_id=policy_id,
            logical_key=logical_key,
            now_utc=now,
        )

        if not suppressed and new_status == "ACTIVE":
            prefs = await self._store.get_notification_prefs(
                tenant_id=tenant_id, patient_id=course["patient_id"]
            )
            if prefs and prefs["recalls_opted_out"]:
                await self._store.mark_schedule_status(
                    tenant_id=tenant_id,
                    schedule_id=schedule_id,
                    status="SUPPRESSED",
                    suppress_reason="OPTED_OUT",
                    now_utc=now,
                )
            else:
                quiet_start = int(
                    (prefs["quiet_hours_start_minute"] if prefs and prefs["quiet_hours_start_minute"] is not None else course["quiet_hours_start_minute"])
                )
                quiet_end = int(
                    (prefs["quiet_hours_end_minute"] if prefs and prefs["quiet_hours_end_minute"] is not None else course["quiet_hours_end_minute"])
                )
                earliest = defer_for_quiet_hours(
                    candidate_utc=tehran_date_to_utc_noon(plan.reminder_tehran),
                    quiet_start_minute=quiet_start,
                    quiet_end_minute=quiet_end,
                )
                dest_ref = prefs["destination_ref"] if prefs else "synthetic:default"
                dest_gen = int(prefs["destination_generation"]) if prefs else 1
                await self._store.stage_synthetic_reminder(
                    tenant_id=tenant_id,
                    outbox_id=new_uuid7(),
                    logical_key=logical_key,
                    course_id=course_id,
                    schedule_id=schedule_id,
                    schedule_version=schedule_version,
                    earliest_send_at_utc=earliest,
                    destination_ref=dest_ref,
                    destination_generation=dest_gen,
                    max_attempts=int(course["max_reminder_attempts"]),
                    payload={
                        "course_id": str(course_id),
                        "schedule_id": str(schedule_id),
                        "schedule_version": schedule_version,
                        "suggested_date_tehran": plan.suggested_tehran.isoformat(),
                        "reminder_date_tehran": plan.reminder_tehran.isoformat(),
                        "patient_id": str(course["patient_id"]),
                        "service_id": str(course["service_id"]),
                        "destination_ref": dest_ref,
                        "destination_generation": dest_gen,
                    },
                    now_utc=now,
                )

        await self._store.update_course_after_completion(
            tenant_id=tenant_id,
            course_id=course_id,
            completed_session_count=new_completed,
            status=new_status,
            next_suggested_date_tehran=plan.suggested_tehran,
            last_completion_date_tehran=completion_tehran,
            schedule_version=schedule_version,
            aggregate_version=int(course["aggregate_version"]) + 1,
            now_utc=now,
        )
        await self._outbox.stage(
            tenant_id=tenant_id,
            message_type="course.session_completed",
            payload={
                "course_id": str(course_id),
                "session_id": str(session_id),
                "session_no": session_no,
                "service_record_id": str(service_record_id),
                "schedule_version": schedule_version,
            },
        )
        return SessionCompletionResult(
            course_id=course_id,
            session_id=session_id,
            session_no=session_no,
            suggested_date_tehran=plan.suggested_tehran,
            reminder_date_tehran=plan.reminder_tehran,
            schedule_version=schedule_version,
            replayed=False,
        )

    async def set_lifecycle(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        status: str,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        if status not in {"ACTIVE", "PAUSED", "TERMINATED", "REASSESSMENT_REQUIRED", "COMPLETED"}:
            raise ValidationFailed("invalid course status")
        course = await self._store.get_course_for_update(tenant_id, course_id)
        if expected_version is not None and int(course["aggregate_version"]) != expected_version:
            raise Conflict("course version conflict", code="course_version_conflict")
        now = datetime.now(timezone.utc)
        if status in {"PAUSED", "TERMINATED"}:
            await self._store.invalidate_pending_reminders(
                tenant_id=tenant_id, course_id=course_id, now_utc=now
            )
        return await self._store.update_course_status(
            tenant_id=tenant_id,
            course_id=course_id,
            status=status,
            aggregate_version=int(course["aggregate_version"]) + 1,
            now_utc=now,
        )
