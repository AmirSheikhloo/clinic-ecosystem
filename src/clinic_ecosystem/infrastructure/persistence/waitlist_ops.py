"""SQL access for waitlist and physical waiting-room metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlWaitlistOps:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schema_ready(self) -> bool:
        row = await self._session.execute(
            text("SELECT to_regclass('public.appointment_waitlist_entries') IS NOT NULL AS ok")
        )
        return bool(row.mappings().one()["ok"])

    async def physical_waiting_count(
        self, *, tenant_id: UUID, start_at_utc: datetime, end_at_utc: datetime
    ) -> int:
        result = await self._session.execute(
            text(
                """
                SELECT COUNT(*) AS c
                FROM appointments
                WHERE tenant_id = :tenant_id
                  AND status = 'CHECKED_IN'
                  AND scheduled_start_at_utc >= :start_at
                  AND scheduled_start_at_utc < :end_at
                """
            ),
            {"tenant_id": tenant_id, "start_at": start_at_utc, "end_at": end_at_utc},
        )
        return int(result.mappings().one()["c"])

    async def future_waitlist_open_count(self, *, tenant_id: UUID) -> int:
        result = await self._session.execute(
            text(
                """
                SELECT COUNT(*) AS c
                FROM appointment_waitlist_entries
                WHERE tenant_id = :tenant_id AND status IN ('OPEN', 'CONTACTED')
                """
            ),
            {"tenant_id": tenant_id},
        )
        return int(result.mappings().one()["c"])

    async def list_entries(
        self,
        *,
        tenant_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        clauses = ["w.tenant_id = :tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "limit": limit,
            "offset": offset,
        }
        if status:
            clauses.append("w.status = :status")
            params["status"] = status
        where = " AND ".join(clauses)
        result = await self._session.execute(
            text(
                f"""
                SELECT w.id, w.patient_id, w.service_id, w.department_id, w.priority,
                       w.status, w.contact_state, w.preferred_start_utc, w.preferred_end_utc,
                       w.notes, w.aggregate_version, w.created_at_utc, w.updated_at_utc,
                       s.service_name, pp.first_name, pp.last_name
                FROM appointment_waitlist_entries w
                JOIN services s ON s.tenant_id = w.tenant_id AND s.id = w.service_id
                JOIN patient_profiles p ON p.tenant_id = w.tenant_id AND p.id = w.patient_id
                JOIN tenant_persons pp ON pp.tenant_id = p.tenant_id AND pp.id = p.person_id
                WHERE {where}
                ORDER BY w.priority ASC, w.created_at_utc ASC, w.id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r) for r in result.mappings().all()]

    async def create_entry(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        service_id: UUID,
        department_id: UUID | None,
        priority: int,
        preferred_start_utc: datetime | None,
        preferred_end_utc: datetime | None,
        notes: str | None,
        user_id: UUID,
        now: datetime,
    ) -> UUID:
        entry_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO appointment_waitlist_entries (
                  id, tenant_id, patient_id, service_id, department_id,
                  preferred_start_utc, preferred_end_utc, priority, status, contact_state,
                  notes, created_by_user_id, updated_by_user_id, aggregate_version,
                  created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :tenant_id, :patient_id, :service_id, :department_id,
                  :preferred_start, :preferred_end, :priority, 'OPEN', 'NONE',
                  :notes, :user_id, :user_id, 1, :now, :now
                )
                """
            ),
            {
                "id": entry_id,
                "tenant_id": tenant_id,
                "patient_id": patient_id,
                "service_id": service_id,
                "department_id": department_id,
                "preferred_start": preferred_start_utc,
                "preferred_end": preferred_end_utc,
                "priority": priority,
                "notes": notes,
                "user_id": user_id,
                "now": now,
            },
        )
        return entry_id

    async def update_status(
        self,
        *,
        tenant_id: UUID,
        entry_id: UUID,
        status: str,
        contact_state: str | None,
        user_id: UUID,
        expected_version: int,
        now: datetime,
    ) -> int | None:
        result = await self._session.execute(
            text(
                """
                UPDATE appointment_waitlist_entries SET
                  status = :status,
                  contact_state = COALESCE(:contact_state, contact_state),
                  updated_by_user_id = :user_id,
                  aggregate_version = aggregate_version + 1,
                  updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :entry_id
                  AND aggregate_version = :expected_version
                  AND status NOT IN ('CONVERTED', 'CANCELLED', 'EXPIRED')
                RETURNING aggregate_version
                """
            ),
            {
                "status": status,
                "contact_state": contact_state,
                "user_id": user_id,
                "now": now,
                "tenant_id": tenant_id,
                "entry_id": entry_id,
                "expected_version": expected_version,
            },
        )
        row = result.mappings().one_or_none()
        return int(row["aggregate_version"]) if row else None
