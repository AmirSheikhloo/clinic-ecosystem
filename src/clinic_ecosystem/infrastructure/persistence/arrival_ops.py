"""Physical arrival facts for CHECKED_IN appointments (ACR-D0.11)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlArrivalOps:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schema_ready(self) -> bool:
        row = await self._session.execute(
            text("SELECT to_regclass('public.appointment_arrival_facts') IS NOT NULL AS ok")
        )
        return bool(row.mappings().one()["ok"])

    async def record_check_in_arrival(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        appointment_id: UUID,
        operator_user_id: UUID,
        now: datetime,
    ) -> UUID | None:
        """Create visit + visit_appointment + arrival_fact in one UoW when schema present.

        Idempotent on appointment_id unique constraint — returns existing fact id.
        """
        if not await self.schema_ready():
            return None
        existing = await self._session.execute(
            text(
                """
                SELECT id FROM appointment_arrival_facts
                WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                """
            ),
            {"tenant_id": tenant_id, "appointment_id": appointment_id},
        )
        row = existing.mappings().one_or_none()
        if row:
            return row["id"]

        visit_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO clinic_visits (
                  id, tenant_id, patient_id, admission_at_utc, arrived_at_utc,
                  registered_by_user_id, aggregate_version, created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :tenant_id, :patient_id, :now, :now, :user_id, 1, :now, :now
                )
                """
            ),
            {
                "id": visit_id,
                "tenant_id": tenant_id,
                "patient_id": patient_id,
                "now": now,
                "user_id": operator_user_id,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO visit_appointments (
                  id, tenant_id, visit_id, patient_id, appointment_id, created_at_utc
                ) VALUES (:id, :tenant_id, :visit_id, :patient_id, :appointment_id, :now)
                """
            ),
            {
                "id": new_uuid7(),
                "tenant_id": tenant_id,
                "visit_id": visit_id,
                "patient_id": patient_id,
                "appointment_id": appointment_id,
                "now": now,
            },
        )
        fact_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO appointment_arrival_facts (
                  id, tenant_id, visit_id, appointment_id, checked_in_at_utc,
                  operator_user_id, created_at_utc
                ) VALUES (:id, :tenant_id, :visit_id, :appointment_id, :now, :user_id, :now)
                """
            ),
            {
                "id": fact_id,
                "tenant_id": tenant_id,
                "visit_id": visit_id,
                "appointment_id": appointment_id,
                "now": now,
                "user_id": operator_user_id,
            },
        )
        return fact_id
