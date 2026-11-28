"""Synthetic-only return-visit reminder worker (no real SMS/bot)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

# Destinations must stay synthetic — never dial/SMS real numbers.
_ALLOWED_DESTINATION_PREFIXES = ("synthetic:", "sink:", "log:")


@dataclass(frozen=True, slots=True)
class WorkerResult:
    claimed: int
    delivered: int
    retryable: int
    failed: int
    invalidated: int


class SyntheticReminderWorker:
    """Claim due notification_outbox_synthetic rows and write sink deliveries."""

    def __init__(self, session: AsyncSession, *, lease_seconds: int = 30) -> None:
        self._session = session
        self._lease_seconds = lease_seconds

    async def run_once(
        self, *, tenant_id: UUID, now_utc: datetime | None = None, limit: int = 50
    ) -> WorkerResult:
        now = now_utc or datetime.now(timezone.utc)
        lease_id = new_uuid7()
        locked_until = now + timedelta(seconds=self._lease_seconds)
        claimed = await self._session.execute(
            text(
                """
                UPDATE notification_outbox_synthetic o
                SET work_state = 'CLAIMED',
                    lease_id = :lease,
                    locked_until = :until,
                    attempt_count = o.attempt_count + 1
                WHERE o.id IN (
                  SELECT id FROM notification_outbox_synthetic
                  WHERE tenant_id = :t
                    AND work_state IN ('PENDING', 'RETRYABLE')
                    AND earliest_send_at_utc <= :now
                    AND (locked_until IS NULL OR locked_until < :now)
                  ORDER BY earliest_send_at_utc ASC, id ASC
                  LIMIT :limit
                  FOR UPDATE SKIP LOCKED
                )
                RETURNING id, logical_key, message_type, payload_json, schedule_id,
                          schedule_version, destination_ref, destination_generation,
                          attempt_count, max_attempts, course_id
                """
            ),
            {
                "t": tenant_id,
                "now": now,
                "limit": limit,
                "lease": lease_id,
                "until": locked_until,
            },
        )
        rows = [dict(r) for r in claimed.mappings().all()]
        delivered = retryable = failed = invalidated = 0
        for row in rows:
            outcome = await self._process_row(tenant_id=tenant_id, row=row, now=now)
            if outcome == "DELIVERED":
                delivered += 1
            elif outcome == "RETRYABLE":
                retryable += 1
            elif outcome == "INVALIDATED":
                invalidated += 1
            else:
                failed += 1
        return WorkerResult(
            claimed=len(rows),
            delivered=delivered,
            retryable=retryable,
            failed=failed,
            invalidated=invalidated,
        )

    async def _process_row(
        self, *, tenant_id: UUID, row: dict[str, Any], now: datetime
    ) -> str:
        dest = str(row.get("destination_ref") or "")
        if not any(dest.startswith(p) for p in _ALLOWED_DESTINATION_PREFIXES):
            await self._fail(row["id"], tenant_id, "NON_SYNTHETIC_DESTINATION", now)
            return "FAILED"

        # Stale schedule / version invalidation.
        if row.get("schedule_id") is not None:
            sched = await self._session.execute(
                text(
                    """
                    SELECT status, schedule_version FROM treatment_recall_schedules
                    WHERE tenant_id = :t AND id = :id
                    """
                ),
                {"t": tenant_id, "id": row["schedule_id"]},
            )
            s = sched.mappings().one_or_none()
            if s is None or s["status"] in {"SUPERSEDED", "INVALIDATED", "SUPPRESSED"}:
                await self._invalidate(row["id"], tenant_id, "STALE_SCHEDULE", now)
                return "INVALIDATED"
            if row.get("schedule_version") is not None and int(s["schedule_version"]) != int(
                row["schedule_version"]
            ):
                await self._invalidate(row["id"], tenant_id, "SCHEDULE_VERSION_MISMATCH", now)
                return "INVALIDATED"

        # Recipient identity generation drift → invalidate (must re-stage).
        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        expected_gen = payload.get("destination_generation")
        if expected_gen is not None and row.get("destination_generation") is not None:
            if int(expected_gen) != int(row["destination_generation"]):
                await self._invalidate(row["id"], tenant_id, "DESTINATION_CHANGED", now)
                return "INVALIDATED"

        try:
            delivery_id = new_uuid7()
            await self._session.execute(
                text(
                    """
                    INSERT INTO synthetic_notification_deliveries (
                      id, tenant_id, outbox_id, logical_key, message_type,
                      payload_json, destination_kind, accepted_at_utc
                    ) VALUES (
                      :id, :t, :oid, :lkey, :mtype,
                      CAST(:payload AS jsonb), 'SYNTHETIC_SINK', :now
                    )
                    """
                ),
                {
                    "id": delivery_id,
                    "t": tenant_id,
                    "oid": row["id"],
                    "lkey": row["logical_key"],
                    "mtype": row["message_type"],
                    "payload": json.dumps(payload if isinstance(payload, dict) else {}),
                    "now": now,
                },
            )
            await self._session.execute(
                text(
                    """
                    UPDATE notification_outbox_synthetic
                    SET work_state = 'DELIVERED', delivered_at_utc = :now,
                        locked_until = NULL, lease_id = NULL
                    WHERE tenant_id = :t AND id = :id
                    """
                ),
                {"t": tenant_id, "id": row["id"], "now": now},
            )
            if row.get("schedule_id") is not None:
                await self._session.execute(
                    text(
                        """
                        UPDATE treatment_recall_schedules
                        SET status = 'ACCEPTED', updated_at_utc = :now
                        WHERE tenant_id = :t AND id = :id AND status = 'SCHEDULED'
                        """
                    ),
                    {"t": tenant_id, "id": row["schedule_id"], "now": now},
                )
            return "DELIVERED"
        except Exception:  # noqa: BLE001 — bounded retry path
            if int(row["attempt_count"]) >= int(row["max_attempts"]):
                await self._fail(row["id"], tenant_id, "MAX_ATTEMPTS", now)
                return "FAILED"
            await self._session.execute(
                text(
                    """
                    UPDATE notification_outbox_synthetic
                    SET work_state = 'RETRYABLE',
                        last_error_code = 'TRANSIENT',
                        locked_until = :backoff,
                        lease_id = NULL
                    WHERE tenant_id = :t AND id = :id
                    """
                ),
                {
                    "t": tenant_id,
                    "id": row["id"],
                    "backoff": now + timedelta(seconds=min(300, 5 * int(row["attempt_count"]))),
                },
            )
            return "RETRYABLE"

    async def _fail(
        self, outbox_id: UUID, tenant_id: UUID, code: str, now: datetime
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE notification_outbox_synthetic
                SET work_state = 'FAILED', last_error_code = :code,
                    locked_until = NULL, lease_id = NULL
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {"t": tenant_id, "id": outbox_id, "code": code},
        )

    async def _invalidate(
        self, outbox_id: UUID, tenant_id: UUID, code: str, now: datetime
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE notification_outbox_synthetic
                SET work_state = 'INVALIDATED', last_error_code = :code,
                    locked_until = NULL, lease_id = NULL
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {"t": tenant_id, "id": outbox_id, "code": code},
        )
