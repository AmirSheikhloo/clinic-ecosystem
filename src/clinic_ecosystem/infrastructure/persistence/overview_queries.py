"""Read-only aggregate and global-search queries (Workstream F)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains


class SqlOverviewQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def appointment_status_counts(
        self, *, tenant_id: UUID, start_at_utc: datetime, end_at_utc: datetime
    ) -> dict[str, int]:
        result = await self._session.execute(
            text(
                """
                SELECT status, count(*) AS n FROM appointments
                WHERE tenant_id = :t AND scheduled_start_at_utc >= :s
                  AND scheduled_start_at_utc < :e
                GROUP BY status
                """
            ),
            {"t": tenant_id, "s": start_at_utc, "e": end_at_utc},
        )
        return {row.status: int(row.n) for row in result}

    async def unique_patient_count(
        self, *, tenant_id: UUID, start_at_utc: datetime, end_at_utc: datetime
    ) -> int:
        """Distinct patients with ≥1 appointment in range (≠ appointment total)."""
        return await self.scalar_count(
            """
            SELECT count(DISTINCT beneficiary_patient_id) FROM appointments
            WHERE tenant_id = :t AND scheduled_start_at_utc >= :s
              AND scheduled_start_at_utc < :e
            """,
            {"t": tenant_id, "s": start_at_utc, "e": end_at_utc},
        )

    async def scalar_count(self, sql: str, params: dict[str, Any]) -> int:
        result = await self._session.execute(text(sql), params)
        return int(result.scalar_one())

    async def active_patients(self, tenant_id: UUID) -> int:
        return await self.scalar_count(
            "SELECT count(*) FROM patient_profiles WHERE tenant_id = :t AND is_active", {"t": tenant_id}
        )

    async def active_staff(self, tenant_id: UUID) -> int:
        return await self.scalar_count(
            "SELECT count(*) FROM staff_profiles WHERE tenant_id = :t AND is_active", {"t": tenant_id}
        )

    async def active_services(self, tenant_id: UUID) -> int:
        return await self.scalar_count(
            "SELECT count(*) FROM services WHERE tenant_id = :t AND is_active", {"t": tenant_id}
        )

    async def active_resources(self, tenant_id: UUID) -> int:
        return await self.scalar_count(
            "SELECT count(*) FROM bookable_resources WHERE tenant_id = :t AND is_active",
            {"t": tenant_id},
        )

    async def search_patients(self, *, tenant_id: UUID, q: str, limit: int) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT pp.id AS id, p.first_name, p.last_name, pp.dossier_number
                FROM patient_profiles pp
                JOIN tenant_persons p ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id
                WHERE pp.tenant_id = :t AND pp.is_active
                  AND ((p.first_name || ' ' || p.last_name) ILIKE :pat ESCAPE '\\'
                       OR pp.dossier_number ILIKE :pat ESCAPE '\\')
                ORDER BY p.last_name, p.first_name, pp.id LIMIT :limit
                """
            ),
            {"t": tenant_id, "pat": like_contains(q), "limit": limit},
        )
        return [dict(r._mapping) for r in result]

    async def search_staff(self, *, tenant_id: UUID, q: str, limit: int) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT sp.id AS id, p.first_name, p.last_name, sp.staff_kind
                FROM staff_profiles sp
                JOIN tenant_persons p ON p.tenant_id = sp.tenant_id AND p.id = sp.person_id
                WHERE sp.tenant_id = :t
                  AND (p.first_name || ' ' || p.last_name) ILIKE :pat ESCAPE '\\'
                ORDER BY p.last_name, p.first_name, sp.id LIMIT :limit
                """
            ),
            {"t": tenant_id, "pat": like_contains(q), "limit": limit},
        )
        return [dict(r._mapping) for r in result]

    async def search_services(self, *, tenant_id: UUID, q: str, limit: int) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, service_name, service_code FROM services
                WHERE tenant_id = :t AND is_active
                  AND (service_name ILIKE :pat ESCAPE '\\' OR service_code ILIKE :pat ESCAPE '\\')
                ORDER BY service_name, id LIMIT :limit
                """
            ),
            {"t": tenant_id, "pat": like_contains(q), "limit": limit},
        )
        return [dict(r._mapping) for r in result]
