"""Disposable dashboard ops: online booking reviews + staff notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlDashboardOps:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reviews_schema_ready(self) -> bool:
        result = await self._session.execute(
            text(
                "SELECT to_regclass('public.online_booking_reviews') IS NOT NULL AS ok"
            )
        )
        return bool(result.mappings().one()["ok"])

    async def notifications_schema_ready(self) -> bool:
        result = await self._session.execute(
            text(
                "SELECT to_regclass('public.clinic_staff_notifications') IS NOT NULL AS ok"
            )
        )
        return bool(result.mappings().one()["ok"])

    async def appointment_is_online_confirmed(
        self, *, tenant_id: UUID, appointment_id: UUID
    ) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT 1 FROM appointments
                WHERE tenant_id = :t AND id = :id
                  AND status = 'CONFIRMED'
                  AND booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')
                """
            ),
            {"t": tenant_id, "id": appointment_id},
        )
        return result.first() is not None

    async def get_review(
        self, *, tenant_id: UUID, appointment_id: UUID
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, appointment_id, reviewed_by_user_id, reviewed_at_utc, note
                FROM online_booking_reviews
                WHERE tenant_id = :t AND appointment_id = :id
                """
            ),
            {"t": tenant_id, "id": appointment_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def upsert_review(
        self,
        *,
        tenant_id: UUID,
        appointment_id: UUID,
        reviewer_user_id: UUID,
        now: datetime,
        note: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Insert review if missing. Returns (row, created). Idempotent."""
        existing = await self.get_review(
            tenant_id=tenant_id, appointment_id=appointment_id
        )
        if existing is not None:
            return existing, False
        review_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO online_booking_reviews (
                  id, tenant_id, appointment_id, reviewed_by_user_id,
                  reviewed_at_utc, note, created_at_utc
                ) VALUES (
                  :id, :t, :appt, :reviewer, :now, :note, :now
                )
                ON CONFLICT (tenant_id, appointment_id) DO NOTHING
                """
            ),
            {
                "id": review_id,
                "t": tenant_id,
                "appt": appointment_id,
                "reviewer": reviewer_user_id,
                "now": now,
                "note": note,
            },
        )
        row = await self.get_review(tenant_id=tenant_id, appointment_id=appointment_id)
        assert row is not None
        created = row["id"] == review_id
        return row, created

    async def list_notifications(
        self,
        *,
        tenant_id: UUID,
        reader_user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        total = await self._session.execute(
            text(
                """
                SELECT count(*) FROM clinic_staff_notifications
                WHERE tenant_id = :t
                """
            ),
            {"t": tenant_id},
        )
        result = await self._session.execute(
            text(
                """
                SELECT n.id, n.notification_kind, n.title, n.body,
                       n.related_appointment_id, n.created_at_utc,
                       (r.id IS NOT NULL) AS is_read,
                       r.read_at_utc
                FROM clinic_staff_notifications n
                LEFT JOIN clinic_notification_reads r
                  ON r.tenant_id = n.tenant_id
                 AND r.notification_id = n.id
                 AND r.reader_user_id = :reader
                WHERE n.tenant_id = :t
                ORDER BY n.created_at_utc DESC, n.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "t": tenant_id,
                "reader": reader_user_id,
                "limit": limit,
                "offset": offset,
            },
        )
        return [dict(r) for r in result.mappings().all()], int(total.scalar_one())

    async def mark_notification_read(
        self,
        *,
        tenant_id: UUID,
        notification_id: UUID,
        reader_user_id: UUID,
        now: datetime,
    ) -> dict[str, Any] | None:
        exists = await self._session.execute(
            text(
                """
                SELECT id FROM clinic_staff_notifications
                WHERE tenant_id = :t AND id = :id
                """
            ),
            {"t": tenant_id, "id": notification_id},
        )
        if exists.first() is None:
            return None
        await self._session.execute(
            text(
                """
                INSERT INTO clinic_notification_reads (
                  id, tenant_id, notification_id, reader_user_id, read_at_utc
                ) VALUES (:id, :t, :nid, :reader, :now)
                ON CONFLICT (tenant_id, notification_id, reader_user_id) DO NOTHING
                """
            ),
            {
                "id": new_uuid7(),
                "t": tenant_id,
                "nid": notification_id,
                "reader": reader_user_id,
                "now": now,
            },
        )
        result = await self._session.execute(
            text(
                """
                SELECT id, notification_id, reader_user_id, read_at_utc
                FROM clinic_notification_reads
                WHERE tenant_id = :t
                  AND notification_id = :nid
                  AND reader_user_id = :reader
                """
            ),
            {"t": tenant_id, "nid": notification_id, "reader": reader_user_id},
        )
        row = result.mappings().one()
        return dict(row)
