"""Supervisory audit list over append-only audit_entries (Class A — existing DDL)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class AuditEntry(BaseModel):
    id: str
    actor_type: str
    actor_id: str | None
    actor_login: str | None
    operation: str
    target_type: str
    target_id: str | None
    details: dict[str, Any]
    created_at_utc: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    limit: int
    offset: int


@router.get("/entries", response_model=AuditPage)
async def list_audit_entries(
    principal: Principal,
    uow: Uow,
    operation: Annotated[str | None, Query(max_length=128)] = None,
    target_type: Annotated[str | None, Query(max_length=128)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
) -> AuditPage:
    require(await load_granted(principal, uow), perm.AUDIT_VIEW)
    rows, total = await SqlAuditStore(uow.session).list_page(
        tenant_id=principal.claims.tenant_id,
        operation=(operation or "").strip() or None,
        target_type=(target_type or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return AuditPage(
        items=[
            AuditEntry(
                id=str(r.id),
                actor_type=r.actor_type,
                actor_id=str(r.actor_id) if r.actor_id else None,
                actor_login=r.actor_login,
                operation=r.operation,
                target_type=r.target_type,
                target_id=str(r.target_id) if r.target_id else None,
                details=r.details_json,
                created_at_utc=r.created_at_utc,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
