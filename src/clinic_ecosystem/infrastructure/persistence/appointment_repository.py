"""Appointment persistence and lock-order helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.domain.scheduling.model import Appointment
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


def _ids_stmt(sql: str):
    return text(sql).bindparams(bindparam("ids", type_=ARRAY(PGUUID(as_uuid=True))))


class SqlAppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_resources(self, tenant_id: UUID, resource_ids: list[UUID]) -> None:
        if not resource_ids:
            return
        await self._session.execute(
            _ids_stmt(
                """
                SELECT id FROM bookable_resources
                WHERE tenant_id = :tenant_id AND id = ANY(:ids)
                ORDER BY id ASC
                FOR UPDATE
                """
            ),
            {"tenant_id": tenant_id, "ids": list(resource_ids)},
        )

    async def get_service_requirements(
        self, tenant_id: UUID, service_id: UUID
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, requirement_group, required_resource_type,
                       specific_resource_id, quantity_required
                FROM service_resource_requirements
                WHERE tenant_id = :tenant_id AND service_id = :service_id
                ORDER BY requirement_group, id
                """
            ),
            {"tenant_id": tenant_id, "service_id": service_id},
        )
        return [dict(row._mapping) for row in result]

    async def get_resource_types(
        self, tenant_id: UUID, resource_ids: list[UUID]
    ) -> dict[UUID, str]:
        if not resource_ids:
            return {}
        result = await self._session.execute(
            _ids_stmt(
                """
                SELECT id, resource_type FROM bookable_resources
                WHERE tenant_id = :tenant_id AND id = ANY(:ids) AND is_active
                """
            ),
            {"tenant_id": tenant_id, "ids": list(resource_ids)},
        )
        return {row.id: row.resource_type for row in result}

    async def find_overlaps(
        self,
        *,
        tenant_id: UUID,
        resource_ids: list[UUID],
        start_at_utc: datetime,
        end_at_utc: datetime,
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            _ids_stmt(
                """
                SELECT a.id AS appointment_id,
                       a.booking_channel,
                       a.capacity_pool,
                       a.scheduled_start_at_utc,
                       a.scheduled_end_at_utc,
                       a.beneficiary_patient_id,
                       ara.resource_id,
                       ara.allocation_status
                FROM appointment_resource_allocations ara
                JOIN appointments a
                  ON a.tenant_id = ara.tenant_id AND a.id = ara.appointment_id
                WHERE ara.tenant_id = :tenant_id
                  AND ara.resource_id = ANY(:ids)
                  AND ara.allocation_status IN (
                      'PENDING_PAYMENT_HOLD', 'CONFIRMED', 'CHECKED_IN'
                  )
                  AND ara.time_slot && tstzrange(:start_at, :end_at, '[)')
                ORDER BY a.id, ara.resource_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "ids": list(resource_ids),
                "start_at": start_at_utc,
                "end_at": end_at_utc,
            },
        )
        return [dict(row._mapping) for row in result]

    async def expire_conflicting_holds(
        self,
        *,
        tenant_id: UUID,
        resource_ids: list[UUID],
        start_at_utc: datetime,
        end_at_utc: datetime,
        now_utc: datetime,
    ) -> list[UUID]:
        discovered = await self._session.execute(
            _ids_stmt(
                """
                SELECT DISTINCT a.id AS appointment_id
                FROM appointments a
                JOIN appointment_resource_allocations ara
                  ON ara.tenant_id = a.tenant_id AND ara.appointment_id = a.id
                WHERE a.tenant_id = :tenant_id
                  AND a.status = 'PENDING_PAYMENT_HOLD'
                  AND a.hold_expires_at_utc IS NOT NULL
                  AND a.hold_expires_at_utc <= :now_utc
                  AND ara.resource_id = ANY(:ids)
                  AND ara.time_slot && tstzrange(:start_at, :end_at, '[)')
                ORDER BY a.id
                """
            ),
            {
                "tenant_id": tenant_id,
                "ids": list(resource_ids),
                "start_at": start_at_utc,
                "end_at": end_at_utc,
                "now_utc": now_utc,
            },
        )
        appointment_ids = [row.appointment_id for row in discovered]
        if not appointment_ids:
            return []

        await self._session.execute(
            _ids_stmt(
                """
                SELECT id FROM appointments
                WHERE tenant_id = :tenant_id AND id = ANY(:ids)
                ORDER BY id ASC
                FOR UPDATE
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids},
        )
        await self._session.execute(
            _ids_stmt(
                """
                SELECT id FROM appointment_resource_allocations
                WHERE tenant_id = :tenant_id AND appointment_id = ANY(:ids)
                ORDER BY appointment_id ASC, resource_id ASC, id ASC
                FOR UPDATE
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids},
        )
        await self._session.execute(
            _ids_stmt(
                """
                UPDATE appointments
                SET status = 'EXPIRED_HOLD',
                    hold_expires_at_utc = NULL,
                    aggregate_version = aggregate_version + 1,
                    updated_at_utc = :now_utc
                WHERE tenant_id = :tenant_id
                  AND id = ANY(:ids)
                  AND status = 'PENDING_PAYMENT_HOLD'
                  AND hold_expires_at_utc IS NOT NULL
                  AND hold_expires_at_utc <= :now_utc
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids, "now_utc": now_utc},
        )
        await self._session.execute(
            _ids_stmt(
                """
                UPDATE appointment_resource_allocations
                SET allocation_status = 'EXPIRED_HOLD'
                WHERE tenant_id = :tenant_id
                  AND appointment_id = ANY(:ids)
                  AND allocation_status = 'PENDING_PAYMENT_HOLD'
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids},
        )
        await self._session.execute(
            _ids_stmt(
                """
                UPDATE hold_expiry_work_items
                SET work_state = 'DONE', updated_at_utc = :now_utc
                WHERE tenant_id = :tenant_id
                  AND appointment_id = ANY(:ids)
                  AND work_state IN ('PENDING', 'RETRYABLE', 'CLAIMED')
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids, "now_utc": now_utc},
        )
        return appointment_ids

    async def add(self, appointment: Appointment) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO appointments (
                    id, tenant_id, beneficiary_patient_id, booker_person_id,
                    patient_booking_note, service_id, status, booking_channel,
                    capacity_pool, scheduled_start_at_utc, scheduled_end_at_utc,
                    hold_expires_at_utc, aggregate_version, created_at_utc, updated_at_utc
                ) VALUES (
                    :id, :tenant_id, :beneficiary_patient_id, :booker_person_id,
                    :patient_booking_note, :service_id, :status, :booking_channel,
                    :capacity_pool, :scheduled_start_at_utc, :scheduled_end_at_utc,
                    :hold_expires_at_utc, :aggregate_version, :created_at_utc, :updated_at_utc
                )
                """
            ),
            {
                "id": appointment.id,
                "tenant_id": appointment.tenant_id,
                "beneficiary_patient_id": appointment.beneficiary_patient_id,
                "booker_person_id": appointment.booker_person_id,
                "patient_booking_note": appointment.patient_booking_note,
                "service_id": appointment.service_id,
                "status": appointment.status.value,
                "booking_channel": appointment.booking_channel.value,
                "capacity_pool": appointment.capacity_pool.value,
                "scheduled_start_at_utc": appointment.scheduled_start_at_utc,
                "scheduled_end_at_utc": appointment.scheduled_end_at_utc,
                "hold_expires_at_utc": appointment.hold_expires_at_utc,
                "aggregate_version": appointment.aggregate_version,
                "created_at_utc": appointment.created_at_utc,
                "updated_at_utc": appointment.updated_at_utc,
            },
        )
        for alloc in appointment.allocations:
            await self._session.execute(
                text(
                    """
                    INSERT INTO appointment_resource_allocations (
                        id, tenant_id, appointment_id, resource_id,
                        booking_channel, capacity_pool, allocation_status,
                        time_slot, created_at_utc
                    ) VALUES (
                        :id, :tenant_id, :appointment_id, :resource_id,
                        :booking_channel, :capacity_pool, :allocation_status,
                        tstzrange(:start_at, :end_at, '[)'), :created_at_utc
                    )
                    """
                ),
                {
                    "id": alloc.id,
                    "tenant_id": appointment.tenant_id,
                    "appointment_id": appointment.id,
                    "resource_id": alloc.resource_id,
                    "booking_channel": alloc.booking_channel.value,
                    "capacity_pool": alloc.capacity_pool.value,
                    "allocation_status": alloc.allocation_status.value,
                    "start_at": alloc.start_at_utc,
                    "end_at": alloc.end_at_utc,
                    "created_at_utc": alloc.created_at_utc,
                },
            )

    async def enqueue_hold_expiry(
        self,
        *,
        tenant_id: UUID,
        appointment_id: UUID,
        due_at_utc: datetime,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO hold_expiry_work_items (
                    id, tenant_id, appointment_id, due_at_utc, work_state,
                    claim_token, claimed_by, lease_expires_at_utc, attempt_count,
                    created_at_utc, updated_at_utc
                ) VALUES (
                    :id, :tenant_id, :appointment_id, :due_at_utc, 'PENDING',
                    NULL, NULL, NULL, 0, :now_utc, :now_utc
                )
                """
            ),
            {
                "id": new_uuid7(),
                "tenant_id": tenant_id,
                "appointment_id": appointment_id,
                "due_at_utc": due_at_utc,
                "now_utc": now,
            },
        )
