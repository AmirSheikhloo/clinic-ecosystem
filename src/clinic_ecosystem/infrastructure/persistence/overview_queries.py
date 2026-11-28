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
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        service_ids: set[UUID] | None = None,
    ) -> dict[str, int]:
        params: dict[str, Any] = {
            "t": tenant_id,
            "s": start_at_utc,
            "e": end_at_utc,
        }
        service_clause = ""
        if service_ids is not None:
            if not service_ids:
                return {}
            service_clause = " AND service_id = ANY(:services)"
            params["services"] = list(service_ids)
        result = await self._session.execute(
            text(
                f"""
                SELECT status, count(*) AS n FROM appointments
                WHERE tenant_id = :t AND scheduled_start_at_utc >= :s
                  AND scheduled_start_at_utc < :e
                  {service_clause}
                GROUP BY status
                """
            ),
            params,
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
        """Exact dashboard predicates (Task 34 R2).

        - today: all appointments scheduled for the Tehran day (any status)
        - upcoming: CONFIRMED with start > now and still within the day
        - needs_status: due for human resolution (CHECKED_IN, or CONFIRMED with end <= now)
        - cancelled: status CANCELLED scheduled for the day
        - online_bookings_today: ONLINE_WEB/ONLINE_BOT CONFIRMED by created_at within day
          (excludes holds / expired holds)
        - online_unreviewed_count: online CONFIRMED lacking online_booking_reviews (any date)
        """
        service_clause = ""
        params: dict[str, Any] = {
            "t": tenant_id,
            "s": start_at_utc,
            "e": end_at_utc,
            "now": now_utc,
        }
        empty = {
            "today": 0,
            "upcoming": 0,
            "needs_status": 0,
            "cancelled": 0,
            "online_bookings_today": 0,
            "online_unreviewed_count": 0,
        }
        if service_ids is not None:
            if not service_ids:
                return empty
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
        online_service_clause = service_clause.replace("service_id", "a.service_id")
        online_today_n = await self.scalar_count(
            f"""
            SELECT count(*) FROM appointments a
            WHERE a.tenant_id = :t
              AND a.booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')
              AND a.status = 'CONFIRMED'
              AND a.created_at_utc >= :s
              AND a.created_at_utc < :e
              {online_service_clause}
            """,
            params,
        )
        reviews_ready = await self._session.execute(
            text(
                "SELECT to_regclass('public.online_booking_reviews') IS NOT NULL AS ok"
            )
        )
        if bool(reviews_ready.mappings().one()["ok"]):
            online_unreviewed = await self.scalar_count(
                f"""
                SELECT count(*) FROM appointments a
                WHERE a.tenant_id = :t
                  AND a.booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')
                  AND a.status = 'CONFIRMED'
                  AND NOT EXISTS (
                    SELECT 1 FROM online_booking_reviews r
                    WHERE r.tenant_id = a.tenant_id
                      AND r.appointment_id = a.id
                  )
                  {online_service_clause}
                """,
                params,
            )
        else:
            # Without the reviews table every online CONFIRMED row is unreviewed.
            online_unreviewed = await self.scalar_count(
                f"""
                SELECT count(*) FROM appointments a
                WHERE a.tenant_id = :t
                  AND a.booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')
                  AND a.status = 'CONFIRMED'
                  {online_service_clause}
                """,
                params,
            )
        return {
            "today": int(row["today"]),
            "upcoming": int(row["upcoming"]),
            "needs_status": int(row["needs_status"]),
            "cancelled": int(row["cancelled"]),
            "online_bookings_today": online_today_n,
            "online_unreviewed_count": online_unreviewed,
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
        online_review: str | None = None,
        booking_channel: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Server-paginated operational day rows matching a metric predicate."""
        is_online = metric == "online"
        metric_sql = {
            "today": "TRUE",
            "upcoming": "a.status = 'CONFIRMED' AND a.scheduled_start_at_utc > :now",
            "needs_status": (
                "a.status = 'CHECKED_IN' OR "
                "(a.status = 'CONFIRMED' AND a.scheduled_end_at_utc <= :now)"
            ),
            "cancelled": "a.status = 'CANCELLED'",
            "online": (
                "a.status = 'CONFIRMED' "
                "AND a.booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT')"
            ),
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
        channel_clause = ""
        if is_online and booking_channel in {"ONLINE_WEB", "ONLINE_BOT"}:
            channel_clause = " AND a.booking_channel = :booking_channel"
            params["booking_channel"] = booking_channel
        review_clause = ""
        if is_online and online_review in {"reviewed", "unreviewed"}:
            reviews_ready = await self._session.execute(
                text(
                    "SELECT to_regclass('public.online_booking_reviews') IS NOT NULL AS ok"
                )
            )
            has_reviews = bool(reviews_ready.mappings().one()["ok"])
            if online_review == "reviewed":
                if not has_reviews:
                    return [], 0
                review_clause = (
                    " AND EXISTS ("
                    "SELECT 1 FROM online_booking_reviews obr "
                    "WHERE obr.tenant_id = a.tenant_id AND obr.appointment_id = a.id)"
                )
            else:
                if has_reviews:
                    review_clause = (
                        " AND NOT EXISTS ("
                        "SELECT 1 FROM online_booking_reviews obr "
                        "WHERE obr.tenant_id = a.tenant_id AND obr.appointment_id = a.id)"
                    )
        # Online metric: never restrict by scheduled_start; unreviewed ignores created_at day.
        if is_online:
            if online_review == "unreviewed":
                date_clause = ""
            else:
                date_clause = " AND a.created_at_utc >= :s AND a.created_at_utc < :e"
            order_clause = "ORDER BY a.created_at_utc DESC, a.id ASC"
        else:
            date_clause = (
                " AND a.scheduled_start_at_utc >= :s AND a.scheduled_start_at_utc < :e"
            )
            order_clause = "ORDER BY a.scheduled_start_at_utc ASC, a.id ASC"
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
                  {date_clause}
                  AND ({metric_sql})
                  {service_clause}
                  {search_clause}
                  {channel_clause}
                  {review_clause}
                """
            ),
            params,
        )
        total = int(count_row.scalar_one())
        result = await self._session.execute(
            text(
                f"""
                SELECT a.id AS appointment_id, a.status, a.scheduled_start_at_utc,
                       a.scheduled_end_at_utc, a.created_at_utc, a.service_id,
                       a.beneficiary_patient_id AS patient_profile_id,
                       pp.person_id AS person_id,
                       p.first_name AS patient_first_name, p.last_name AS patient_last_name,
                       s.service_name,
                       a.booking_channel, a.capacity_pool, a.aggregate_version,
                       (
                         SELECT pi.masked_display
                         FROM person_identifiers pi
                         WHERE pi.tenant_id = pp.tenant_id AND pi.person_id = pp.person_id
                         ORDER BY pi.created_at_utc ASC, pi.id ASC
                         LIMIT 1
                       ) AS national_id_masked,
                       (
                         SELECT ph.masked_phone
                         FROM person_phones ph
                         WHERE ph.tenant_id = pp.tenant_id AND ph.person_id = pp.person_id
                         ORDER BY ph.created_at_utc ASC, ph.id ASC
                         LIMIT 1
                       ) AS patient_phone_masked,
                       COALESCE((
                           SELECT array_agg(r.resource_name ORDER BY r.resource_name)
                           FROM appointment_resource_allocations ara
                           JOIN bookable_resources r
                             ON r.tenant_id = ara.tenant_id AND r.id = ara.resource_id
                           WHERE ara.tenant_id = a.tenant_id AND ara.appointment_id = a.id
                       ), ARRAY[]::text[]) AS resource_names,
                       (
                           SELECT r.resource_name
                           FROM appointment_resource_allocations ara
                           JOIN bookable_resources r
                             ON r.tenant_id = ara.tenant_id AND r.id = ara.resource_id
                           WHERE ara.tenant_id = a.tenant_id
                             AND ara.appointment_id = a.id
                             AND r.resource_type = 'PRACTITIONER'
                           ORDER BY r.resource_name ASC, r.id ASC
                           LIMIT 1
                       ) AS practitioner_name
                FROM appointments a
                JOIN patient_profiles pp
                  ON pp.tenant_id = a.tenant_id AND pp.id = a.beneficiary_patient_id
                JOIN tenant_persons p
                  ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id
                JOIN services s
                  ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE a.tenant_id = :t
                  {date_clause}
                  AND ({metric_sql})
                  {service_clause}
                  {search_clause}
                  {channel_clause}
                  {review_clause}
                {order_clause}
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r) for r in result.mappings().all()], total

    async def insurance_labels_for_patients(
        self, *, tenant_id: UUID, patient_ids: list[UUID]
    ) -> dict[UUID, str]:
        """Best-effort insurance display names when disposable insurer tables exist."""
        if not patient_ids:
            return {}
        ready = await self._session.execute(
            text(
                "SELECT to_regclass('public.clinic_insurers') IS NOT NULL AS ok"
            )
        )
        if not bool(ready.mappings().one()["ok"]):
            catalog = await self._session.execute(
                text(
                    "SELECT to_regclass('public.insurance_catalog_entries') IS NOT NULL AS ok"
                )
            )
            if not bool(catalog.mappings().one()["ok"]):
                return {}
            # Disposable catalog without patient link — nothing to project yet.
            return {}
        # Prefer insurer name tied to the patient's most recent invoice expectation.
        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT ON (inv.beneficiary_patient_id)
                       inv.beneficiary_patient_id AS patient_id,
                       ci.insurer_name AS insurer_name
                FROM invoice_documents inv
                JOIN invoice_lines il
                  ON il.tenant_id = inv.tenant_id AND il.invoice_id = inv.id
                JOIN invoice_insurer_expectations ie
                  ON ie.tenant_id = il.tenant_id AND ie.invoice_line_id = il.id
                JOIN clinic_insurers ci
                  ON ci.tenant_id = ie.tenant_id AND ci.id = ie.insurer_id
                WHERE inv.tenant_id = :t
                  AND inv.beneficiary_patient_id = ANY(:patients)
                ORDER BY inv.beneficiary_patient_id, inv.created_at_utc DESC, ie.created_at_utc DESC
                """
            ),
            {"t": tenant_id, "patients": patient_ids},
        )
        return {
            row["patient_id"]: str(row["insurer_name"])
            for row in result.mappings().all()
            if row["insurer_name"]
        }

    async def unique_patient_count(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        service_ids: set[UUID] | None = None,
    ) -> int:
        """Distinct patients with ≥1 appointment in range (≠ appointment total)."""
        params: dict[str, Any] = {
            "t": tenant_id,
            "s": start_at_utc,
            "e": end_at_utc,
        }
        service_clause = ""
        if service_ids is not None:
            if not service_ids:
                return 0
            service_clause = " AND service_id = ANY(:services)"
            params["services"] = list(service_ids)
        return await self.scalar_count(
            f"""
            SELECT count(DISTINCT beneficiary_patient_id) FROM appointments
            WHERE tenant_id = :t AND scheduled_start_at_utc >= :s
              AND scheduled_start_at_utc < :e
              {service_clause}
            """,
            params,
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
