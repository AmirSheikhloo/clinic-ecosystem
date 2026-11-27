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

    async def operational_metric_counts(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        now_utc: datetime,
        service_ids: set[UUID] | None = None,
    ) -> dict[str, int]:
        """Exact dashboard predicates (Task 34 R2 §8).

        - today: all appointments scheduled for the Tehran day (any status)
        - upcoming: CONFIRMED with start > now and still within the day
        - needs_status: due for human resolution (CHECKED_IN, or CONFIRMED with end <= now)
        - cancelled: status CANCELLED scheduled for the day
        """
        service_clause = ""
        params: dict[str, Any] = {
            "t": tenant_id,
            "s": start_at_utc,
            "e": end_at_utc,
            "now": now_utc,
        }
        if service_ids is not None:
            if not service_ids:
                return {"today": 0, "upcoming": 0, "needs_status": 0, "cancelled": 0}
            service_clause = " AND service_id = ANY(:services)"
            params["services"] = list(service_ids)
        result = await self._session.execute(
            text(
                f"""
                SELECT
                  count(*) FILTER (WHERE TRUE) AS today,
                  count(*) FILTER (
                    WHERE status = 'CONFIRMED' AND scheduled_start_at_utc > :now
                  ) AS upcoming,
                  count(*) FILTER (
                    WHERE status = 'CHECKED_IN'
                       OR (status = 'CONFIRMED' AND scheduled_end_at_utc <= :now)
                  ) AS needs_status,
                  count(*) FILTER (WHERE status = 'CANCELLED') AS cancelled
                FROM appointments
                WHERE tenant_id = :t
                  AND scheduled_start_at_utc >= :s
                  AND scheduled_start_at_utc < :e
                  {service_clause}
                """
            ),
            params,
        )
        row = result.mappings().one()
        return {
            "today": int(row["today"]),
            "upcoming": int(row["upcoming"]),
            "needs_status": int(row["needs_status"]),
            "cancelled": int(row["cancelled"]),
        }

    async def list_operational_day(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        now_utc: datetime,
        metric: str,
        q: str | None,
        limit: int,
        offset: int,
        service_ids: set[UUID] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Server-paginated operational day rows matching a metric predicate."""
        metric_sql = {
            "today": "TRUE",
            "upcoming": "a.status = 'CONFIRMED' AND a.scheduled_start_at_utc > :now",
            "needs_status": (
                "a.status = 'CHECKED_IN' OR "
                "(a.status = 'CONFIRMED' AND a.scheduled_end_at_utc <= :now)"
            ),
            "cancelled": "a.status = 'CANCELLED'",
        }.get(metric, "TRUE")
        params: dict[str, Any] = {
            "t": tenant_id,
            "s": start_at_utc,
            "e": end_at_utc,
            "now": now_utc,
            "limit": limit,
            "offset": offset,
        }
        service_clause = ""
        if service_ids is not None:
            if not service_ids:
                return [], 0
            service_clause = " AND a.service_id = ANY(:services)"
            params["services"] = list(service_ids)
        search_clause = ""
        if q and q.strip():
            search_clause = (
                " AND (p.first_name ILIKE :pat OR p.last_name ILIKE :pat "
                "OR s.service_name ILIKE :pat)"
            )
            params["pat"] = like_contains(q.strip())
        count_row = await self._session.execute(
            text(
                f"""
                SELECT count(*) AS n
                FROM appointments a
                JOIN patient_profiles pp
                  ON pp.tenant_id = a.tenant_id AND pp.id = a.beneficiary_patient_id
                JOIN tenant_persons p
                  ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id
                JOIN services s
                  ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE a.tenant_id = :t
                  AND a.scheduled_start_at_utc >= :s
                  AND a.scheduled_start_at_utc < :e
                  AND ({metric_sql})
                  {service_clause}
                  {search_clause}
                """
            ),
            params,
        )
        total = int(count_row.scalar_one())
        result = await self._session.execute(
            text(
                f"""
                SELECT a.id AS appointment_id, a.status, a.scheduled_start_at_utc,
                       a.scheduled_end_at_utc, a.service_id, a.beneficiary_patient_id
                         AS patient_profile_id,
                       p.first_name AS patient_first_name, p.last_name AS patient_last_name,
                       s.service_name,
                       a.booking_channel, a.capacity_pool, a.aggregate_version
                FROM appointments a
                JOIN patient_profiles pp
                  ON pp.tenant_id = a.tenant_id AND pp.id = a.beneficiary_patient_id
                JOIN tenant_persons p
                  ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id
                JOIN services s
                  ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE a.tenant_id = :t
                  AND a.scheduled_start_at_utc >= :s
                  AND a.scheduled_start_at_utc < :e
                  AND ({metric_sql})
                  {service_clause}
                  {search_clause}
                ORDER BY a.scheduled_start_at_utc ASC, a.id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r) for r in result.mappings().all()], total

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
