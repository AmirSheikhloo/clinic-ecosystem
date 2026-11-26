"""Bounded appointment listing queries for reception (BETA-01B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class AppointmentListItem:
    appointment_id: UUID
    patient_profile_id: UUID
    patient_first_name: str
    patient_last_name: str
    service_id: UUID
    service_name: str
    status: str
    booking_channel: str
    capacity_pool: str
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime


class SqlAppointmentQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_in_range(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        limit: int = 200,
        status: str | None = None,
    ) -> list[AppointmentListItem]:
        where = [
            "a.tenant_id = :tenant_id",
            "a.scheduled_start_at_utc >= :start_at",
            "a.scheduled_start_at_utc < :end_at",
        ]
        params: dict = {
            "tenant_id": tenant_id,
            "start_at": start_at_utc,
            "end_at": end_at_utc,
            "limit": limit,
        }
        if status is not None:
            where.append("a.status = :status")
            params["status"] = status
        result = await self._session.execute(
            text(
                f"""
                SELECT a.id AS appointment_id,
                       a.beneficiary_patient_id AS patient_profile_id,
                       tp.first_name AS patient_first_name,
                       tp.last_name AS patient_last_name,
                       a.service_id,
                       s.service_name,
                       a.status,
                       a.booking_channel,
                       a.capacity_pool,
                       a.scheduled_start_at_utc,
                       a.scheduled_end_at_utc
                FROM appointments a
                JOIN patient_profiles p
                  ON p.tenant_id = a.tenant_id AND p.id = a.beneficiary_patient_id
                JOIN tenant_persons tp
                  ON tp.tenant_id = p.tenant_id AND tp.id = p.person_id
                JOIN services s
                  ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE {" AND ".join(where)}
                ORDER BY a.scheduled_start_at_utc ASC, a.id ASC
                LIMIT :limit
                """
            ),
            params,
        )
        items: list[AppointmentListItem] = []
        for row in result.mappings().all():
            items.append(
                AppointmentListItem(
                    appointment_id=row["appointment_id"],
                    patient_profile_id=row["patient_profile_id"],
                    patient_first_name=row["patient_first_name"],
                    patient_last_name=row["patient_last_name"],
                    service_id=row["service_id"],
                    service_name=row["service_name"],
                    status=row["status"],
                    booking_channel=row["booking_channel"],
                    capacity_pool=row["capacity_pool"],
                    scheduled_start_at_utc=row["scheduled_start_at_utc"],
                    scheduled_end_at_utc=row["scheduled_end_at_utc"],
                )
            )
        return items

    async def list_waiting_room(
        self,
        *,
        tenant_id: UUID,
        start_at_utc: datetime,
        end_at_utc: datetime,
        limit: int = 200,
    ) -> list[AppointmentListItem]:
        """CHECKED_IN appointments whose scheduled start falls in the Tehran day window."""
        return await self.list_in_range(
            tenant_id=tenant_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
            limit=limit,
            status="CHECKED_IN",
        )
