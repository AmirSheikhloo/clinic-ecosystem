"""Future waitlist APIs (physical waiting remains CHECKED_IN appointments)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from clinic_ecosystem.application.shared.errors import Conflict, NotFound, ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.infrastructure.persistence.waitlist_ops import SqlWaitlistOps
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class WaitlistCreateIn(BaseModel):
    patient_id: UUID
    service_id: UUID
    department_id: UUID | None = None
    priority: int = Field(default=100, ge=1, le=1000)
    preferred_start_utc: datetime | None = None
    preferred_end_utc: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class WaitlistUpdateIn(BaseModel):
    status: str = Field(pattern="^(OPEN|CONTACTED|CANCELLED|EXPIRED)$")
    contact_state: str | None = Field(
        default=None, pattern="^(NONE|PENDING|CONTACTED|UNREACHABLE|DECLINED)$"
    )
    expected_version: int = Field(ge=1)


@router.get("/entries")
async def list_waitlist(
    principal: Principal,
    uow: Uow,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.WAITLIST_VIEW)
    ops = SqlWaitlistOps(uow.session)
    if not await ops.schema_ready():
        raise Conflict("Ops waitlist schema unavailable", code="ops_schema_unavailable")
    rows = await ops.list_entries(
        tenant_id=principal.claims.tenant_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "patient_id": str(r["patient_id"]),
                "patient_name": f"{r['first_name']} {r['last_name']}",
                "service_id": str(r["service_id"]),
                "service_name": r["service_name"],
                "department_id": str(r["department_id"]) if r["department_id"] else None,
                "priority": r["priority"],
                "status": r["status"],
                "contact_state": r["contact_state"],
                "preferred_start_utc": r["preferred_start_utc"].isoformat()
                if r["preferred_start_utc"]
                else None,
                "preferred_end_utc": r["preferred_end_utc"].isoformat()
                if r["preferred_end_utc"]
                else None,
                "notes": r["notes"],
                "aggregate_version": r["aggregate_version"],
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@router.post("/entries")
async def create_waitlist(principal: Principal, uow: Uow, body: WaitlistCreateIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.WAITLIST_MANAGE)
    ops = SqlWaitlistOps(uow.session)
    if not await ops.schema_ready():
        raise Conflict("Ops waitlist schema unavailable", code="ops_schema_unavailable")
    if body.preferred_start_utc and body.preferred_end_utc:
        if body.preferred_end_utc <= body.preferred_start_utc:
            raise ValidationFailed("Invalid preferred window", code="invalid_time_range")
    now = datetime.now(timezone.utc)
    entry_id = await ops.create_entry(
        tenant_id=principal.claims.tenant_id,
        patient_id=body.patient_id,
        service_id=body.service_id,
        department_id=body.department_id,
        priority=body.priority,
        preferred_start_utc=body.preferred_start_utc,
        preferred_end_utc=body.preferred_end_utc,
        notes=body.notes,
        user_id=principal.account.id,
        now=now,
    )
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="waitlist.created",
        target_type="waitlist_entry",
        target_id=entry_id,
        details={"service_id": str(body.service_id), "patient_id": str(body.patient_id)},
    )
    await uow.commit()
    return {"id": str(entry_id), "status": "OPEN", "aggregate_version": 1}


@router.patch("/entries/{entry_id}")
async def update_waitlist(
    principal: Principal, uow: Uow, entry_id: UUID, body: WaitlistUpdateIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.WAITLIST_MANAGE)
    ops = SqlWaitlistOps(uow.session)
    if not await ops.schema_ready():
        raise Conflict("Ops waitlist schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    version = await ops.update_status(
        tenant_id=principal.claims.tenant_id,
        entry_id=entry_id,
        status=body.status,
        contact_state=body.contact_state,
        user_id=principal.account.id,
        expected_version=body.expected_version,
        now=now,
    )
    if version is None:
        raise NotFound("Waitlist entry not found or version conflict", code="waitlist_conflict")
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="waitlist.updated",
        target_type="waitlist_entry",
        target_id=entry_id,
        details={"status": body.status, "to_version": version},
    )
    await uow.commit()
    return {"id": str(entry_id), "status": body.status, "aggregate_version": version}
