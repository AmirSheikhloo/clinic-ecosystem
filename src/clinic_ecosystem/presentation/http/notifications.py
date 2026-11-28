"""Staff notification inbox (disposable dashboard R2 schema)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from clinic_ecosystem.application.shared.errors import Conflict, NotFound
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.dashboard_ops import SqlDashboardOps
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


@router.get("")
async def list_notifications(
    principal: Principal,
    uow: Uow,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_LIST)
    ops = SqlDashboardOps(uow.session)
    if not await ops.notifications_schema_ready():
        raise Conflict(
            "Staff notifications schema unavailable", code="ops_schema_unavailable"
        )
    rows, total = await ops.list_notifications(
        tenant_id=principal.claims.tenant_id,
        reader_user_id=principal.account.id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "notification_kind": r["notification_kind"],
                "title": r["title"],
                "body": r.get("body"),
                "related_appointment_id": (
                    str(r["related_appointment_id"])
                    if r.get("related_appointment_id")
                    else None
                ),
                "created_at_utc": r["created_at_utc"].isoformat(),
                "is_read": bool(r["is_read"]),
                "read_at_utc": r["read_at_utc"].isoformat() if r.get("read_at_utc") else None,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    principal: Principal,
    uow: Uow,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_LIST)
    ops = SqlDashboardOps(uow.session)
    if not await ops.notifications_schema_ready():
        raise Conflict(
            "Staff notifications schema unavailable", code="ops_schema_unavailable"
        )
    row = await ops.mark_notification_read(
        tenant_id=principal.claims.tenant_id,
        notification_id=notification_id,
        reader_user_id=principal.account.id,
        now=datetime.now(timezone.utc),
    )
    if row is None:
        raise NotFound("Notification not found", code="notification_not_found")
    await uow.commit()
    return {
        "notification_id": str(row["notification_id"]),
        "reader_user_id": str(row["reader_user_id"]),
        "read_at_utc": row["read_at_utc"].isoformat(),
    }
