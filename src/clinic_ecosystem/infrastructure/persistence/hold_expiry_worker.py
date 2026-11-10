"""HoldExpirationWorker — queue claim then Resource→Appointment→Allocation locks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


def _ids_stmt(sql: str):
    return text(sql).bindparams(bindparam("ids", type_=ARRAY(PGUUID(as_uuid=True))))


@dataclass(slots=True)
class ClaimedHoldWork:
    work_item_id: UUID
    tenant_id: UUID
    appointment_id: UUID
    claim_token: UUID


class HoldExpirationWorker:
    def __init__(self, *, claim_session_factory, scheduling_session_factory, worker_id: str) -> None:
        self._claim_session_factory = claim_session_factory
        self._scheduling_session_factory = scheduling_session_factory
        self._worker_id = worker_id

    async def claim_due_work(
        self, *, tenant_id: UUID, lease_seconds: int = 30
    ) -> ClaimedHoldWork | None:
        """TX1: SKIP LOCKED only on hold_expiry_work_items (clause 782/F.5).

        Tenant context must be bound before the claim SELECT because FORCE RLS
        on hold_expiry_work_items fails closed without app.current_tenant_id.
        """
        claim_token = new_uuid7()
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)
        async with self._claim_session_factory() as session:
            assert isinstance(session, AsyncSession)
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            row = (
                await session.execute(
                    text(
                        """
                        SELECT id, tenant_id, appointment_id
                        FROM hold_expiry_work_items
                        WHERE tenant_id = :tenant_id
                          AND work_state IN ('PENDING', 'RETRYABLE')
                          AND due_at_utc <= :now_utc
                        ORDER BY due_at_utc, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                        """
                    ),
                    {"now_utc": now, "tenant_id": tenant_id},
                )
            ).first()
            if row is None:
                await session.rollback()
                return None
            await session.execute(
                text(
                    """
                    UPDATE hold_expiry_work_items
                    SET work_state = 'CLAIMED',
                        claim_token = :claim_token,
                        claimed_by = :worker_id,
                        lease_expires_at_utc = :lease_until,
                        attempt_count = attempt_count + 1,
                        updated_at_utc = :now_utc
                    WHERE id = :id
                    """
                ),
                {
                    "id": row.id,
                    "claim_token": claim_token,
                    "worker_id": self._worker_id,
                    "lease_until": lease_until,
                    "now_utc": now,
                },
            )
            await session.commit()
            return ClaimedHoldWork(
                work_item_id=row.id,
                tenant_id=row.tenant_id,
                appointment_id=row.appointment_id,
                claim_token=claim_token,
            )

    async def process_claim(self, claim: ClaimedHoldWork) -> str:
        """TX2 scheduling UoW: lock order Resource → Appointment → Allocation."""
        now = datetime.now(timezone.utc)
        async with self._scheduling_session_factory() as session:
            assert isinstance(session, AsyncSession)
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(claim.tenant_id)},
            )

            work = (
                await session.execute(
                    text(
                        """
                        SELECT claim_token, work_state, lease_expires_at_utc
                        FROM hold_expiry_work_items
                        WHERE id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": claim.work_item_id, "tenant_id": claim.tenant_id},
                )
            ).first()
            if (
                work is None
                or work.claim_token != claim.claim_token
                or work.work_state != "CLAIMED"
                or (work.lease_expires_at_utc is not None and work.lease_expires_at_utc < now)
            ):
                await session.execute(
                    text(
                        """
                        UPDATE hold_expiry_work_items
                        SET work_state = 'NOOP', updated_at_utc = :now_utc
                        WHERE id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": claim.work_item_id, "tenant_id": claim.tenant_id, "now_utc": now},
                )
                await session.commit()
                return "NOOP"

            resource_ids = [
                r.resource_id
                for r in (
                    await session.execute(
                        text(
                            """
                            SELECT resource_id
                            FROM appointment_resource_allocations
                            WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                            ORDER BY resource_id ASC
                            """
                        ),
                        {
                            "tenant_id": claim.tenant_id,
                            "appointment_id": claim.appointment_id,
                        },
                    )
                )
            ]
            if resource_ids:
                await session.execute(
                    _ids_stmt(
                        """
                        SELECT id FROM bookable_resources
                        WHERE tenant_id = :tenant_id AND id = ANY(:ids)
                        ORDER BY id ASC
                        FOR UPDATE
                        """
                    ),
                    {"tenant_id": claim.tenant_id, "ids": resource_ids},
                )
            await session.execute(
                text(
                    """
                    SELECT id FROM appointments
                    WHERE tenant_id = :tenant_id AND id = :appointment_id
                    ORDER BY id ASC
                    FOR UPDATE
                    """
                ),
                {"tenant_id": claim.tenant_id, "appointment_id": claim.appointment_id},
            )
            await session.execute(
                text(
                    """
                    SELECT id FROM appointment_resource_allocations
                    WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                    ORDER BY appointment_id ASC, resource_id ASC, id ASC
                    FOR UPDATE
                    """
                ),
                {"tenant_id": claim.tenant_id, "appointment_id": claim.appointment_id},
            )

            appt = (
                await session.execute(
                    text(
                        """
                        SELECT status, hold_expires_at_utc
                        FROM appointments
                        WHERE tenant_id = :tenant_id AND id = :appointment_id
                        """
                    ),
                    {
                        "tenant_id": claim.tenant_id,
                        "appointment_id": claim.appointment_id,
                    },
                )
            ).first()
            if (
                appt is None
                or appt.status != "PENDING_PAYMENT_HOLD"
                or appt.hold_expires_at_utc is None
                or appt.hold_expires_at_utc > now
            ):
                await session.execute(
                    text(
                        """
                        UPDATE hold_expiry_work_items
                        SET work_state = 'NOOP', updated_at_utc = :now_utc
                        WHERE id = :id AND tenant_id = :tenant_id
                          AND claim_token = :claim_token
                        """
                    ),
                    {
                        "id": claim.work_item_id,
                        "tenant_id": claim.tenant_id,
                        "claim_token": claim.claim_token,
                        "now_utc": now,
                    },
                )
                await session.commit()
                return "NOOP"

            await session.execute(
                text(
                    """
                    UPDATE appointments
                    SET status = 'EXPIRED_HOLD',
                        hold_expires_at_utc = NULL,
                        aggregate_version = aggregate_version + 1,
                        updated_at_utc = :now_utc
                    WHERE tenant_id = :tenant_id AND id = :appointment_id
                    """
                ),
                {
                    "tenant_id": claim.tenant_id,
                    "appointment_id": claim.appointment_id,
                    "now_utc": now,
                },
            )
            await session.execute(
                text(
                    """
                    UPDATE appointment_resource_allocations
                    SET allocation_status = 'EXPIRED_HOLD'
                    WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
                    """
                ),
                {
                    "tenant_id": claim.tenant_id,
                    "appointment_id": claim.appointment_id,
                },
            )
            await session.execute(
                text(
                    """
                    UPDATE hold_expiry_work_items
                    SET work_state = 'DONE', updated_at_utc = :now_utc
                    WHERE id = :id AND tenant_id = :tenant_id
                      AND claim_token = :claim_token
                    """
                ),
                {
                    "id": claim.work_item_id,
                    "tenant_id": claim.tenant_id,
                    "claim_token": claim.claim_token,
                    "now_utc": now,
                },
            )
            await session.commit()
            return "DONE"
