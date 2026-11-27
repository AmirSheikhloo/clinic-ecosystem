"""Synthetic return-visit reminder worker (Task 34 R2 §9).

Mirrors TP0006 / HoldExpirationWorker claim+lease semantics.
Delivers ONLY to ``synthetic_notification_deliveries`` — never SMS/bot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.domain.treatment_courses.rolling import defer_for_quiet_hours
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(slots=True)
class ClaimedReminderWork:
    outbox_id: UUID
    tenant_id: UUID
    logical_key: str
    schedule_version: int | None
    course_id: UUID | None
    lease_id: UUID
    payload: dict[str, Any]
    destination_ref: str | None
    destination_generation: int | None
    attempt_count: int
    max_attempts: int


class SyntheticReminderWorker:
    """Claim due synthetic reminder jobs and accept them into the synthetic sink."""

    MESSAGE_TYPE = "course.return_visit_reminder"

    def __init__(self, *, session_factory, worker_id: str) -> None:
        self._session_factory = session_factory
        self._worker_id = worker_id

    async def claim_due_work(
        self, *, tenant_id: UUID, lease_seconds: int = 30, now_utc: datetime | None = None
    ) -> ClaimedReminderWork | None:
        now = now_utc or datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)
        lease_id = new_uuid7()
        async with self._session_factory() as session:
            assert isinstance(session, AsyncSession)
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            row = (
                await session.execute(
                    text(
                        """
                        SELECT id, tenant_id, logical_key, schedule_version, course_id,
                               payload_json, destination_ref, destination_generation,
                               attempt_count, max_attempts, earliest_send_at_utc
                        FROM notification_outbox_synthetic
                        WHERE tenant_id = :tenant_id
                          AND work_state IN ('PENDING', 'RETRYABLE')
                          AND earliest_send_at_utc <= :now_utc
                          AND destination_kind IN ('SYNTHETIC_SINK', 'SYNTHETIC_LOG')
                        ORDER BY earliest_send_at_utc, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                        """
                    ),
                    {"tenant_id": tenant_id, "now_utc": now},
                )
            ).mappings().first()
            if row is None:
                await session.rollback()
                return None
            await session.execute(
                text(
                    """
                    UPDATE notification_outbox_synthetic
                    SET work_state = 'CLAIMED',
                        lease_id = :lease_id,
                        locked_until = :lease_until,
                        attempt_count = attempt_count + 1
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {
                    "id": row["id"],
                    "tenant_id": tenant_id,
                    "lease_id": lease_id,
                    "lease_until": lease_until,
                },
            )
            await session.commit()
            payload = row["payload_json"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return ClaimedReminderWork(
                outbox_id=row["id"],
                tenant_id=row["tenant_id"],
                logical_key=row["logical_key"],
                schedule_version=row["schedule_version"],
                course_id=row["course_id"],
                lease_id=lease_id,
                payload=dict(payload),
                destination_ref=row["destination_ref"],
                destination_generation=row["destination_generation"],
                attempt_count=int(row["attempt_count"]) + 1,
                max_attempts=int(row["max_attempts"]),
            )

    async def process_claimed(
        self, work: ClaimedReminderWork, *, now_utc: datetime | None = None
    ) -> str:
        """Validate staleness/opt-out/identity then accept into synthetic sink.

        Returns terminal work_state applied.
        """
        now = now_utc or datetime.now(timezone.utc)
        async with self._session_factory() as session:
            assert isinstance(session, AsyncSession)
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(work.tenant_id)},
            )

            # Stale-job invalidation: schedule version must still be current.
            course: dict[str, Any] | None = None
            if work.course_id is not None:
                course = (
                    await session.execute(
                        text(
                            """
                            SELECT status, current_schedule_version,
                                   quiet_hours_start_minute, quiet_hours_end_minute
                            FROM treatment_courses
                            WHERE tenant_id = :tenant_id AND id = :course_id
                            """
                        ),
                        {"tenant_id": work.tenant_id, "course_id": work.course_id},
                    )
                ).mappings().first()
                if course is None or course["status"] != "ACTIVE":
                    await self._finalize(
                        session, work, state="INVALIDATED", error="COURSE_NOT_ACTIVE", now=now
                    )
                    await session.commit()
                    return "INVALIDATED"
                if (
                    work.schedule_version is not None
                    and int(course["current_schedule_version"]) != int(work.schedule_version)
                ):
                    await self._finalize(
                        session, work, state="INVALIDATED", error="STALE_SCHEDULE_VERSION", now=now
                    )
                    await session.commit()
                    return "INVALIDATED"

            prefs = (
                await session.execute(
                    text(
                        """
                        SELECT recalls_opted_out, destination_ref, destination_generation,
                               quiet_hours_start_minute, quiet_hours_end_minute
                        FROM patient_notification_preferences
                        WHERE tenant_id = :tenant_id
                          AND patient_id = CAST(:patient_id AS uuid)
                        """
                    ),
                    {
                        "tenant_id": work.tenant_id,
                        "patient_id": work.payload.get("patient_id"),
                    },
                )
            ).mappings().first()
            if prefs and prefs["recalls_opted_out"]:
                await self._finalize(
                    session, work, state="SUPPRESSED", error="OPTED_OUT", now=now
                )
                await session.commit()
                return "SUPPRESSED"

            # Recipient identity change → invalidate (caller may reschedule).
            if prefs is not None and work.destination_generation is not None:
                if int(prefs["destination_generation"]) != int(work.destination_generation):
                    await self._finalize(
                        session,
                        work,
                        state="INVALIDATED",
                        error="DESTINATION_GENERATION_MISMATCH",
                        now=now,
                    )
                    await session.commit()
                    return "INVALIDATED"
                if (
                    work.destination_ref is not None
                    and prefs["destination_ref"] is not None
                    and prefs["destination_ref"] != work.destination_ref
                ):
                    await self._finalize(
                        session,
                        work,
                        state="INVALIDATED",
                        error="DESTINATION_REF_CHANGED",
                        now=now,
                    )
                    await session.commit()
                    return "INVALIDATED"

            # Quiet hours deferral (re-check at dispatch time).
            quiet_start = 1320
            quiet_end = 480
            if course is not None:
                quiet_start = int(course["quiet_hours_start_minute"])
                quiet_end = int(course["quiet_hours_end_minute"])
            if prefs and prefs["quiet_hours_start_minute"] is not None:
                quiet_start = int(prefs["quiet_hours_start_minute"])
            if prefs and prefs["quiet_hours_end_minute"] is not None:
                quiet_end = int(prefs["quiet_hours_end_minute"])
            deferred = defer_for_quiet_hours(
                candidate_utc=now,
                quiet_start_minute=quiet_start,
                quiet_end_minute=quiet_end,
            )
            if deferred > now + timedelta(seconds=1):
                await session.execute(
                    text(
                        """
                        UPDATE notification_outbox_synthetic
                        SET work_state = 'RETRYABLE',
                            earliest_send_at_utc = :earliest,
                            locked_until = NULL,
                            lease_id = NULL,
                            last_error_code = 'QUIET_HOURS'
                        WHERE tenant_id = :tenant_id
                          AND id = :id
                          AND lease_id = :lease_id
                        """
                    ),
                    {
                        "tenant_id": work.tenant_id,
                        "id": work.outbox_id,
                        "lease_id": work.lease_id,
                        "earliest": deferred,
                    },
                )
                await session.commit()
                return "RETRYABLE"

            # Bounded retries — if somehow over max, fail closed.
            if work.attempt_count > work.max_attempts:
                await self._finalize(
                    session, work, state="FAILED", error="MAX_ATTEMPTS", now=now
                )
                await session.commit()
                return "FAILED"

            delivery_id = new_uuid7()
            await session.execute(
                text(
                    """
                    INSERT INTO synthetic_notification_deliveries (
                      id, tenant_id, outbox_id, logical_key, message_type,
                      payload_json, destination_kind, accepted_at_utc
                    ) VALUES (
                      :id, :tenant_id, :outbox_id, :logical_key, :message_type,
                      CAST(:payload AS jsonb), 'SYNTHETIC_SINK', :now_utc
                    )
                    ON CONFLICT (tenant_id, logical_key) DO NOTHING
                    """
                ),
                {
                    "id": delivery_id,
                    "tenant_id": work.tenant_id,
                    "outbox_id": work.outbox_id,
                    "logical_key": work.logical_key,
                    "message_type": self.MESSAGE_TYPE,
                    "payload": json.dumps(work.payload),
                    "now_utc": now,
                },
            )
            await self._finalize(session, work, state="DELIVERED", error=None, now=now)
            if work.course_id is not None and work.schedule_version is not None:
                await session.execute(
                    text(
                        """
                        UPDATE treatment_recall_schedules
                        SET status = 'ACCEPTED', updated_at_utc = :now_utc
                        WHERE tenant_id = :tenant_id
                          AND course_id = :course_id
                          AND schedule_version = :schedule_version
                          AND status IN ('SCHEDULED', 'ATTEMPTED')
                        """
                    ),
                    {
                        "tenant_id": work.tenant_id,
                        "course_id": work.course_id,
                        "schedule_version": work.schedule_version,
                        "now_utc": now,
                    },
                )
            await session.commit()
            return "DELIVERED"

    async def _finalize(
        self,
        session: AsyncSession,
        work: ClaimedReminderWork,
        *,
        state: str,
        error: str | None,
        now: datetime,
    ) -> None:
        delivered_at = now if state == "DELIVERED" else None
        await session.execute(
            text(
                """
                UPDATE notification_outbox_synthetic
                SET work_state = :state,
                    delivered_at_utc = COALESCE(:delivered_at, delivered_at_utc),
                    locked_until = NULL,
                    lease_id = NULL,
                    last_error_code = :error
                WHERE tenant_id = :tenant_id
                  AND id = :id
                  AND lease_id = :lease_id
                """
            ),
            {
                "tenant_id": work.tenant_id,
                "id": work.outbox_id,
                "lease_id": work.lease_id,
                "state": state,
                "delivered_at": delivered_at,
                "error": error,
            },
        )
