"""Appointment calendar reads and guarded state changes (Workstream D)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ACTIVE_ALLOCATION_STATES = ("PENDING_PAYMENT_HOLD", "CONFIRMED", "CHECKED_IN")


class SqlAppointmentAdmin:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_calendar(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        service_id: UUID | None,
        resource_id: UUID | None,
        status: str | None,
        patient_profile_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        where = [
            "a.tenant_id = :tenant_id",
            "a.scheduled_start_at_utc >= :start_at",
            "a.scheduled_start_at_utc < :end_at",
        ]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "start_at": start_at_utc,
            "end_at": end_at_utc,
            "limit": limit,
        }
        if service_id:
            where.append("a.service_id = :service_id")
            params["service_id"] = service_id
        if status:
            where.append("a.status = :status")
            params["status"] = status
        if patient_profile_id:
            where.append("a.beneficiary_patient_id = :patient_id")
            params["patient_id"] = patient_profile_id
        if resource_id:
            where.append(
                "EXISTS (SELECT 1 FROM appointment_resource_allocations f "
                "WHERE f.tenant_id = a.tenant_id AND f.appointment_id = a.id "
                "AND f.resource_id = :resource_id)"
            )
            params["resource_id"] = resource_id
        result = await self._session.execute(
            text(
                f"""
                SELECT a.id AS appointment_id,
                       a.beneficiary_patient_id AS patient_profile_id,
                       tp.first_name AS patient_first_name,
                       tp.last_name AS patient_last_name,
                       a.service_id, s.service_name, a.status, a.booking_channel,
                       a.capacity_pool, a.scheduled_start_at_utc, a.scheduled_end_at_utc,
                       a.aggregate_version,
                       COALESCE((
                           SELECT array_agg(r.resource_name ORDER BY r.resource_name)
                           FROM appointment_resource_allocations ara
                           JOIN bookable_resources r
                             ON r.tenant_id = ara.tenant_id AND r.id = ara.resource_id
                           WHERE ara.tenant_id = a.tenant_id AND ara.appointment_id = a.id
                       ), ARRAY[]::text[]) AS resource_names
                FROM appointments a
                JOIN patient_profiles p
                  ON p.tenant_id = a.tenant_id AND p.id = a.beneficiary_patient_id
                JOIN tenant_persons tp ON tp.tenant_id = p.tenant_id AND tp.id = p.person_id
                JOIN services s ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE {' AND '.join(where)}
                ORDER BY a.scheduled_start_at_utc ASC, a.id ASC
                LIMIT :limit
                """
            ),
            params,
        )
        return [dict(r._mapping) for r in result]

    async def get_appointment(
        self, *, tenant_id: UUID, appointment_id: UUID
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                """
                SELECT a.id AS appointment_id, a.beneficiary_patient_id AS patient_profile_id,
                       tp.first_name AS patient_first_name, tp.last_name AS patient_last_name,
                       a.service_id, s.service_name, a.status, a.booking_channel,
                       a.capacity_pool, a.scheduled_start_at_utc, a.scheduled_end_at_utc,
                       a.hold_expires_at_utc, a.aggregate_version,
                       a.created_at_utc, a.updated_at_utc
                FROM appointments a
                JOIN patient_profiles p
                  ON p.tenant_id = a.tenant_id AND p.id = a.beneficiary_patient_id
                JOIN tenant_persons tp ON tp.tenant_id = p.tenant_id AND tp.id = p.person_id
                JOIN services s ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE a.tenant_id = :tenant_id AND a.id = :id
                """
            ),
            {"tenant_id": tenant_id, "id": appointment_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def get_allocations(
        self, *, tenant_id: UUID, appointment_id: UUID
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT ara.resource_id, r.resource_name, r.resource_type, ara.allocation_status
                FROM appointment_resource_allocations ara
                JOIN bookable_resources r
                  ON r.tenant_id = ara.tenant_id AND r.id = ara.resource_id
                WHERE ara.tenant_id = :tenant_id AND ara.appointment_id = :id
                ORDER BY r.resource_name, ara.resource_id
                """
            ),
            {"tenant_id": tenant_id, "id": appointment_id},
        )
        return [dict(r._mapping) for r in result]

    async def transition_appointment(
        self,
        *,
        tenant_id: UUID,
        appointment_id: UUID,
        expected_version: int,
        new_status: str | None,
        start_at_utc: datetime | None,
        end_at_utc: datetime | None,
        now: datetime,
    ) -> int | None:
        sets = ["aggregate_version = aggregate_version + 1", "updated_at_utc = :now"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "id": appointment_id,
            "expected": expected_version,
            "now": now,
        }
        if new_status:
            sets.append("status = :status")
            params["status"] = new_status
        if start_at_utc and end_at_utc:
            sets.append("scheduled_start_at_utc = :start_at")
            sets.append("scheduled_end_at_utc = :end_at")
            params["start_at"] = start_at_utc
            params["end_at"] = end_at_utc
        result = await self._session.execute(
            text(
                f"UPDATE appointments SET {', '.join(sets)} "
                "WHERE tenant_id = :tenant_id AND id = :id AND aggregate_version = :expected "
                "RETURNING aggregate_version"
            ),
            params,
        )
        row = result.first()
        return int(row.aggregate_version) if row else None

    async def cancel_allocations(self, *, tenant_id: UUID, appointment_id: UUID) -> None:
        await self._session.execute(
            text(
                """
                UPDATE appointment_resource_allocations
                SET allocation_status = 'CANCELLED'
                WHERE tenant_id = :tenant_id AND appointment_id = :id
                  AND allocation_status = ANY(:states)
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": appointment_id,
                "states": list(_ACTIVE_ALLOCATION_STATES),
            },
        )

    async def move_allocations(
        self,
        *,
        tenant_id: UUID,
        appointment_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE appointment_resource_allocations
                SET time_slot = tstzrange(:start_at, :end_at, '[)')
                WHERE tenant_id = :tenant_id AND appointment_id = :id
                  AND allocation_status = ANY(:states)
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": appointment_id,
                "start_at": start_at_utc,
                "end_at": end_at_utc,
                "states": list(_ACTIVE_ALLOCATION_STATES),
            },
        )
