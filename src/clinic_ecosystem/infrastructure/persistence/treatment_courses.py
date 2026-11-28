"""Disposable treatment-course / recall persistence (Task 34 R2 §9)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.application.shared.errors import Conflict, NotFound, ValidationFailed


class SqlTreatmentCourseStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schema_ready(self) -> bool:
        row = await self._session.execute(
            text("SELECT to_regclass('public.treatment_courses') IS NOT NULL")
        )
        return bool(row.scalar())

    async def insert_course(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        template_version_id: UUID | None,
        planned_sessions: int,
        interval_kind: str,
        interval_value: int,
        reminder_lead_days: int,
        billing_mode: str,
        now_utc: datetime,
    ) -> dict[str, Any]:
        await self._session.execute(
            text(
                """
                INSERT INTO treatment_courses (
                  id, tenant_id, patient_id, service_id, template_version_id,
                  planned_sessions, completed_session_count, status, scheduling_mode,
                  interval_kind, interval_value, reminder_lead_days,
                  billing_mode, prepaid_entitlement_enabled,
                  current_schedule_version, aggregate_version,
                  created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :tenant_id, :patient_id, :service_id, :template_version_id,
                  :planned, 0, 'ACTIVE', 'ROLLING',
                  :interval_kind, :interval_value, :lead,
                  :billing_mode, FALSE,
                  0, 1, :now, :now
                )
                """
            ),
            {
                "id": course_id,
                "tenant_id": tenant_id,
                "patient_id": patient_id,
                "service_id": service_id,
                "template_version_id": template_version_id,
                "planned": planned_sessions,
                "interval_kind": interval_kind,
                "interval_value": interval_value,
                "lead": reminder_lead_days,
                "billing_mode": billing_mode,
                "now": now_utc,
            },
        )
        return await self.get_course(tenant_id, course_id)

    async def get_course(self, tenant_id: UUID, course_id: UUID) -> dict[str, Any]:
        row = await self._session.execute(
            text(
                """
                SELECT * FROM treatment_courses
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {"t": tenant_id, "id": course_id},
        )
        data = row.mappings().one_or_none()
        if data is None:
            raise NotFound("Course not found", code="course_not_found")
        return dict(data)

    async def get_course_for_update(self, tenant_id: UUID, course_id: UUID) -> dict[str, Any]:
        row = await self._session.execute(
            text(
                """
                SELECT * FROM treatment_courses
                WHERE tenant_id = :t AND id = :id
                FOR UPDATE
                """
            ),
            {"t": tenant_id, "id": course_id},
        )
        data = row.mappings().one_or_none()
        if data is None:
            raise NotFound("Course not found", code="course_not_found")
        return dict(data)

    async def find_session_by_idempotency(
        self, *, tenant_id: UUID, course_id: UUID, idempotency_key: str
    ) -> dict[str, Any] | None:
        row = await self._session.execute(
            text(
                """
                SELECT * FROM treatment_course_sessions
                WHERE tenant_id = :t AND course_id = :c AND idempotency_key = :k
                """
            ),
            {"t": tenant_id, "c": course_id, "k": idempotency_key},
        )
        data = row.mappings().one_or_none()
        return dict(data) if data else None

    async def require_performed_record(
        self,
        *,
        tenant_id: UUID,
        service_record_id: UUID,
        patient_id: UUID,
        service_id: UUID,
    ) -> dict[str, Any]:
        row = await self._session.execute(
            text(
                """
                SELECT id, patient_id, service_id, record_kind, occurred_at_utc
                FROM service_records
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {"t": tenant_id, "id": service_record_id},
        )
        data = row.mappings().one_or_none()
        if data is None:
            raise NotFound("Service record not found", code="service_record_not_found")
        if data["patient_id"] != patient_id or data["service_id"] != service_id:
            raise ValidationFailed("Service record mismatch", code="service_record_mismatch")
        if data["record_kind"] != "PERFORMED":
            raise Conflict(
                "Course completion requires PERFORMED evidence",
                code="course_completion_requires_performed",
            )
        return dict(data)

    async def insert_completed_session(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        course_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        session_no: int,
        appointment_id: UUID | None,
        service_record_id: UUID,
        completion_tehran_date: date,
        completion_at_utc: datetime,
        idempotency_key: str,
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO treatment_course_sessions (
                  id, tenant_id, course_id, patient_id, service_id, session_no,
                  status, appointment_id, service_record_id,
                  completion_tehran_date, completion_at_utc, idempotency_key,
                  created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :t, :c, :p, :s, :n,
                  'COMPLETED', :appt, :sr,
                  :ct, :cu, :ikey, :now, :now
                )
                """
            ),
            {
                "id": session_id,
                "t": tenant_id,
                "c": course_id,
                "p": patient_id,
                "s": service_id,
                "n": session_no,
                "appt": appointment_id,
                "sr": service_record_id,
                "ct": completion_tehran_date,
                "cu": completion_at_utc,
                "ikey": idempotency_key,
                "now": now_utc,
            },
        )

    async def supersede_open_schedules(
        self, *, tenant_id: UUID, course_id: UUID, now_utc: datetime
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE treatment_recall_schedules
                SET status = 'SUPERSEDED', updated_at_utc = :now
                WHERE tenant_id = :t AND course_id = :c
                  AND status IN ('SCHEDULED', 'ATTEMPTED', 'RETRYABLE')
                """
            ),
            {"t": tenant_id, "c": course_id, "now": now_utc},
        )
        await self._session.execute(
            text(
                """
                UPDATE notification_outbox_synthetic
                SET work_state = 'INVALIDATED', last_error_code = 'SCHEDULE_SUPERSEDED'
                WHERE tenant_id = :t AND course_id = :c
                  AND work_state IN ('PENDING', 'RETRYABLE', 'CLAIMED')
                """
            ),
            {"t": tenant_id, "c": course_id},
        )

    async def insert_policy_snapshot(
        self,
        *,
        tenant_id: UUID,
        snapshot_id: UUID,
        course_id: UUID,
        schedule_version: int,
        reminder_lead_days: int,
        quiet_hours_start_minute: int,
        quiet_hours_end_minute: int,
        max_reminder_attempts: int,
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO treatment_reminder_policy_snapshots (
                  id, tenant_id, course_id, schedule_version, reminder_lead_days,
                  quiet_hours_start_minute, quiet_hours_end_minute, max_reminder_attempts,
                  destination_kind, created_at_utc
                ) VALUES (
                  :id, :t, :c, :v, :lead, :qs, :qe, :maxa, 'SYNTHETIC_SINK', :now
                )
                """
            ),
            {
                "id": snapshot_id,
                "t": tenant_id,
                "c": course_id,
                "v": schedule_version,
                "lead": reminder_lead_days,
                "qs": quiet_hours_start_minute,
                "qe": quiet_hours_end_minute,
                "maxa": max_reminder_attempts,
                "now": now_utc,
            },
        )

    async def has_qualifying_future_appointment(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        from_tehran: date,
        to_tehran: date,
    ) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1 FROM appointments a
                  WHERE a.tenant_id = :t
                    AND a.beneficiary_patient_id = :p
                    AND a.service_id = :s
                    AND a.status IN ('CONFIRMED', 'CHECKED_IN', 'PENDING_PAYMENT_HOLD')
                    AND (a.scheduled_start_at_utc AT TIME ZONE 'Asia/Tehran')::date
                        BETWEEN :from_d AND :to_d
                )
                """
            ),
            {
                "t": tenant_id,
                "p": patient_id,
                "s": service_id,
                "from_d": from_tehran,
                "to_d": to_tehran,
            },
        )
        return bool(row.scalar())

    async def insert_recall_schedule(
        self,
        *,
        tenant_id: UUID,
        schedule_id: UUID,
        course_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        schedule_version: int,
        cycle_no: int,
        source_session_id: UUID,
        suggested_date_tehran: date,
        reminder_date_tehran: date,
        scheduled_at_utc: datetime,
        status: str,
        suppress_reason: str | None,
        policy_snapshot_id: UUID,
        logical_key: str,
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO treatment_recall_schedules (
                  id, tenant_id, course_id, patient_id, service_id, schedule_version,
                  cycle_no, source_session_id, suggested_date_tehran, reminder_date_tehran,
                  scheduled_at_utc, status, suppress_reason, policy_snapshot_id,
                  logical_key, created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :t, :c, :p, :s, :v,
                  :cycle, :src, :sug, :rem,
                  :sched, :status, :suppress, :policy,
                  :lkey, :now, :now
                )
                """
            ),
            {
                "id": schedule_id,
                "t": tenant_id,
                "c": course_id,
                "p": patient_id,
                "s": service_id,
                "v": schedule_version,
                "cycle": cycle_no,
                "src": source_session_id,
                "sug": suggested_date_tehran,
                "rem": reminder_date_tehran,
                "sched": scheduled_at_utc,
                "status": status,
                "suppress": suppress_reason,
                "policy": policy_snapshot_id,
                "lkey": logical_key,
                "now": now_utc,
            },
        )

    async def mark_schedule_status(
        self,
        *,
        tenant_id: UUID,
        schedule_id: UUID,
        status: str,
        suppress_reason: str | None,
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE treatment_recall_schedules
                SET status = :status, suppress_reason = :suppress, updated_at_utc = :now
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {
                "t": tenant_id,
                "id": schedule_id,
                "status": status,
                "suppress": suppress_reason,
                "now": now_utc,
            },
        )

    async def get_notification_prefs(
        self, *, tenant_id: UUID, patient_id: UUID
    ) -> dict[str, Any] | None:
        row = await self._session.execute(
            text(
                """
                SELECT * FROM patient_notification_preferences
                WHERE tenant_id = :t AND patient_id = :p
                """
            ),
            {"t": tenant_id, "p": patient_id},
        )
        data = row.mappings().one_or_none()
        return dict(data) if data else None

    async def stage_synthetic_reminder(
        self,
        *,
        tenant_id: UUID,
        outbox_id: UUID,
        logical_key: str,
        course_id: UUID,
        schedule_id: UUID,
        schedule_version: int,
        earliest_send_at_utc: datetime,
        destination_ref: str,
        destination_generation: int,
        max_attempts: int,
        payload: dict[str, Any],
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO notification_outbox_synthetic (
                  id, tenant_id, message_type, payload_json, logical_key,
                  course_id, schedule_id, schedule_version,
                  destination_kind, destination_ref, destination_generation,
                  earliest_send_at_utc, created_at_utc, attempt_count, max_attempts,
                  work_state
                ) VALUES (
                  :id, :t, 'course.return_visit_reminder', CAST(:payload AS jsonb), :lkey,
                  :c, :s, :v,
                  'SYNTHETIC_SINK', :dref, :dgen,
                  :earliest, :now, 0, :maxa, 'PENDING'
                )
                ON CONFLICT (tenant_id, logical_key) DO NOTHING
                """
            ),
            {
                "id": outbox_id,
                "t": tenant_id,
                "payload": json.dumps(payload),
                "lkey": logical_key,
                "c": course_id,
                "s": schedule_id,
                "v": schedule_version,
                "dref": destination_ref,
                "dgen": destination_generation,
                "earliest": earliest_send_at_utc,
                "now": now_utc,
                "maxa": max_attempts,
            },
        )

    async def update_course_after_completion(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        completed_session_count: int,
        status: str,
        next_suggested_date_tehran: date,
        last_completion_date_tehran: date,
        schedule_version: int,
        aggregate_version: int,
        now_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE treatment_courses SET
                  completed_session_count = :completed,
                  status = :status,
                  next_suggested_date_tehran = :next_d,
                  last_completion_date_tehran = :last_d,
                  current_schedule_version = :sv,
                  aggregate_version = :av,
                  updated_at_utc = :now
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {
                "t": tenant_id,
                "id": course_id,
                "completed": completed_session_count,
                "status": status,
                "next_d": next_suggested_date_tehran,
                "last_d": last_completion_date_tehran,
                "sv": schedule_version,
                "av": aggregate_version,
                "now": now_utc,
            },
        )

    async def invalidate_pending_reminders(
        self, *, tenant_id: UUID, course_id: UUID, now_utc: datetime
    ) -> None:
        await self.supersede_open_schedules(
            tenant_id=tenant_id, course_id=course_id, now_utc=now_utc
        )

    async def update_course_status(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        status: str,
        aggregate_version: int,
        now_utc: datetime,
    ) -> dict[str, Any]:
        await self._session.execute(
            text(
                """
                UPDATE treatment_courses
                SET status = :status, aggregate_version = :av, updated_at_utc = :now
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {
                "t": tenant_id,
                "id": course_id,
                "status": status,
                "av": aggregate_version,
                "now": now_utc,
            },
        )
        return await self.get_course(tenant_id, course_id)
