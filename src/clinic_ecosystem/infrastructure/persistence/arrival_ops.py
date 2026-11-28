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

    async def record_completion_service(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        appointment_id: UUID,
        service_id: UUID,
        operator_user_id: UUID,
        now: datetime,
        department_id: UUID | None = None,
    ) -> UUID | None:
        """Insert PERFORMED service_record before COMPLETED transition (ACR-D0.11).

        Must run while appointment is still CHECKED_IN so the lifecycle trigger
        can see the performed record when status flips to COMPLETED.
        """
        if not await self.schema_ready():
            return None
        existing = await self._session.execute(
            text(
                """
                SELECT id FROM service_records
                WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                  AND record_kind = 'PERFORMED'
                """
            ),
            {"tenant_id": tenant_id, "appointment_id": appointment_id},
        )
        row = existing.mappings().one_or_none()
        if row:
            return row["id"]

        visit = await self._session.execute(
            text(
                """
                SELECT visit_id FROM appointment_arrival_facts
                WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                """
            ),
            {"tenant_id": tenant_id, "appointment_id": appointment_id},
        )
        visit_row = visit.mappings().one_or_none()
        visit_id = visit_row["visit_id"] if visit_row else None
        if department_id is None:
            dept = await self._session.execute(
                text(
                    """
                    SELECT id FROM departments
                    WHERE tenant_id = :tenant_id AND is_active IS TRUE
                    ORDER BY created_at_utc, id LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            )
            dept_row = dept.mappings().one_or_none()
            department_id = dept_row["id"] if dept_row else None

        record_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO service_records (
                  id, tenant_id, patient_id, service_id, appointment_id, visit_id,
                  department_id, record_kind, occurred_at_utc, operator_user_id,
                  created_at_utc
                ) VALUES (
                  :id, :tenant_id, :patient_id, :service_id, :appointment_id, :visit_id,
                  :department_id, 'PERFORMED', :now, :user_id, :now
                )
                """
            ),
            {
                "id": record_id,
                "tenant_id": tenant_id,
                "patient_id": patient_id,
                "service_id": service_id,
                "appointment_id": appointment_id,
                "visit_id": visit_id,
                "department_id": department_id,
                "now": now,
                "user_id": operator_user_id,
            },
        )
        return record_id
