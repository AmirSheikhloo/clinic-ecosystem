"""Historical appointment late-entry with explicit reason and recording timestamp."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from clinic_ecosystem.application.shared.errors import Conflict, NotFound, ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/appointments", tags=["historical-entry"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class HistoricalEntryIn(BaseModel):
    late_entry_reason: str = Field(min_length=1, max_length=200)
    reported_occurrence_at_utc: datetime | None = None


@router.post("/{appointment_id}/historical-entry")
async def record_historical_entry(
    principal: Principal, uow: Uow, appointment_id: UUID, body: HistoricalEntryIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_SCHEDULE_MANUAL)
    ready = await uow.session.execute(
        text("SELECT to_regclass('public.historical_appointment_entries') IS NOT NULL AS ok")
    )
    if not ready.mappings().one()["ok"]:
        raise Conflict("Ops historical schema unavailable", code="ops_schema_unavailable")
    if not body.late_entry_reason.strip():
        raise ValidationFailed("late_entry_reason required", code="missing_reason")

    appt = await uow.session.execute(
        text(
            """
            SELECT id, status FROM appointments
            WHERE tenant_id = :tenant_id AND id = :id
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "id": appointment_id},
    )
    row = appt.mappings().one_or_none()
    if row is None:
        raise NotFound("Appointment not found", code="appointment_not_found")

    now = datetime.now(timezone.utc)
    entry_id = new_uuid7()
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO historical_appointment_entries (
                  id, tenant_id, appointment_id, late_entry_reason,
                  reported_occurrence_at_utc, suppress_past_reminders,
                  operator_user_id, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :appointment_id, :reason, :occurred, TRUE, :user_id, :now
                )
                """
            ),
            {
                "id": entry_id,
                "tenant_id": principal.claims.tenant_id,
                "appointment_id": appointment_id,
                "reason": body.late_entry_reason.strip(),
                "occurred": body.reported_occurrence_at_utc.astimezone(timezone.utc)
                if body.reported_occurrence_at_utc
                else None,
                "user_id": principal.account.id,
                "now": now,
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise Conflict(
            "Historical entry rejected",
            code="historical_entry_rejected",
            extra={"detail": str(exc.__class__.__name__)},
        ) from exc

    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="appointment.historical_entry",
        target_type="appointment",
        target_id=appointment_id,
        details={
            "entry_id": str(entry_id),
            "recorded_at_utc": now.isoformat(),
            "reason_present": True,
        },
    )
    await uow.commit()
    return {
        "id": str(entry_id),
        "appointment_id": str(appointment_id),
        "recorded_at_utc": now.isoformat(),
        "late_entry_reason": body.late_entry_reason.strip(),
    }


@router.get("/{appointment_id}/historical-entry")
async def get_historical_entry(
    principal: Principal, uow: Uow, appointment_id: UUID
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_VIEW_DETAILS)
    result = await uow.session.execute(
        text(
            """
            SELECT id, late_entry_reason, reported_occurrence_at_utc, created_at_utc,
                   operator_user_id
            FROM historical_appointment_entries
            WHERE tenant_id = :tenant_id AND appointment_id = :appointment_id
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "appointment_id": appointment_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return {"entry": None}
    return {
        "entry": {
            "id": str(row["id"]),
            "late_entry_reason": row["late_entry_reason"],
            "reported_occurrence_at_utc": row["reported_occurrence_at_utc"].isoformat()
            if row["reported_occurrence_at_utc"]
            else None,
            "recorded_at_utc": row["created_at_utc"].isoformat(),
            "operator_user_id": str(row["operator_user_id"]),
        }
    }
