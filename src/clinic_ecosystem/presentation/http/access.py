"""Users, roles and permissions HTTP routes (Workstream C)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, Field

from clinic_ecosystem.application.access.service import AccessService
from clinic_ecosystem.application.shared.errors import NotFound
from clinic_ecosystem.application.shared.preconditions import parse_if_match
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.domain.access.permissions import PERMISSION_CATALOG
from clinic_ecosystem.domain.access.rules import GOVERNANCE_ROLES
from clinic_ecosystem.infrastructure.persistence.access_admin import SqlAccessAdmin
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import actor_of, load_granted, require, set_etag
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/access", tags=["access"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class CreateRoleBody(BaseModel):
    role_code: str = Field(max_length=64)
    role_name: str = Field(max_length=120)
    permissions: list[str] = Field(default_factory=list, max_length=100)


class PermissionsBody(BaseModel):
    permissions: list[str] = Field(max_length=100)


class RolesBody(BaseModel):
    role_ids: list[UUID] = Field(max_length=50)


class StatusBody(BaseModel):
    is_active: bool


class GovernanceBody(BaseModel):
    roles: list[str] = Field(max_length=10)


async def _commit(uow: SqlAlchemyUnitOfWork, work):
    try:
        result = await work
        await uow.commit()
        return result
    except BaseException:
        await uow.rollback()
        raise


@router.get("/permissions")
async def permission_catalog(principal: Principal, uow: Uow) -> dict:
    require(await load_granted(principal, uow), perm.ROLES_VIEW)
    return {
        "items": [
            {"code": d.code, "category": d.category, "label_fa": d.label_fa,
             "description": d.description}
            for d in PERMISSION_CATALOG.values()
        ],
        "governance_roles": list(GOVERNANCE_ROLES),
    }


@router.get("/roles")
async def list_roles(principal: Principal, uow: Uow) -> dict:
    require(await load_granted(principal, uow), perm.ROLES_VIEW)
    rows = await SqlAccessAdmin(uow.session).list_roles(tenant_id=principal.claims.tenant_id)
    return {
        "items": [
            {
                "role_id": str(r["role_id"]),
                "role_code": r["role_code"],
                "role_name": r["role_name"],
                "is_system_defined": r["is_system_defined"],
                "permissions": list(r["permission_codes"]),
                "member_count": int(r["member_count"]),
            }
            for r in rows
        ]
    }


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(body: CreateRoleBody, principal: Principal, uow: Uow) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ROLES_MANAGE)
    role_id = await _commit(
        uow,
        AccessService(uow).create_role(
            actor_of(principal), granted, body.role_code.strip(), body.role_name, body.permissions
        ),
    )
    return {"role_id": str(role_id)}


@router.put("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: UUID, body: PermissionsBody, principal: Principal, uow: Uow
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ROLES_MANAGE)
    return await _commit(
        uow,
        AccessService(uow).set_role_permissions(
            actor_of(principal), granted, role_id, body.permissions
        ),
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: UUID, principal: Principal, uow: Uow) -> Response:
    require(await load_granted(principal, uow), perm.ROLES_MANAGE)
    await _commit(uow, AccessService(uow).delete_role(actor_of(principal), role_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounts")
async def list_accounts(
    principal: Principal,
    uow: Uow,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    require(await load_granted(principal, uow), perm.ACCOUNTS_VIEW)
    rows, total = await SqlAccessAdmin(uow.session).list_accounts(
        tenant_id=principal.claims.tenant_id,
        q=(q or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    now = datetime.now(timezone.utc)
    return {
        "items": [
            {
                "account_id": str(r["account_id"]),
                "person_id": str(r["person_id"]),
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "login_identifier": r["login_identifier"],
                "is_active": r["is_active"],
                "is_locked": bool(r["locked_until_utc"] and r["locked_until_utc"] > now),
                "staff_kind": r["staff_kind"],
                "roles": list(r["role_codes"]),
                "governance_roles": list(r["governance_roles"]),
                "aggregate_version": int(r["aggregate_version"]),
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/accounts/{account_id}/effective-permissions")
async def effective_permissions(account_id: UUID, principal: Principal, uow: Uow) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ROLES_VIEW)
    require(granted, perm.ACCOUNTS_VIEW)
    admin = SqlAccessAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    if await admin.get_account(tenant_id=tenant_id, account_id=account_id) is None:
        raise NotFound("Account not found", code="account_not_found")
    grouped: dict[str, list[str]] = {}
    for row in await admin.account_permissions(tenant_id=tenant_id, account_id=account_id):
        grouped.setdefault(row["permission_code"], []).append(row["role_code"])
    return {
        "account_id": str(account_id),
        "items": [
            {"permission_code": code, "via_roles": roles} for code, roles in sorted(grouped.items())
        ],
    }


@router.put("/accounts/{account_id}/roles")
async def set_account_roles(
    account_id: UUID, body: RolesBody, principal: Principal, uow: Uow
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.USER_ROLES_ASSIGN)
    return await _commit(
        uow,
        AccessService(uow).set_account_roles(
            actor_of(principal), granted, account_id, body.role_ids
        ),
    )


@router.put("/accounts/{account_id}/status")
async def set_account_status(
    account_id: UUID,
    body: StatusBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ACCOUNTS_SET_ACTIVE)
    expected = parse_if_match(if_match)
    result = await _commit(
        uow,
        AccessService(uow).set_account_active(
            actor_of(principal), granted, account_id, expected, body.is_active
        ),
    )
    set_etag(response, result["aggregate_version"])
    return result


@router.get("/governance")
async def list_governance(principal: Principal, uow: Uow) -> dict:
    require(await load_granted(principal, uow), perm.GOVERNANCE_VIEW)
    rows = await SqlAccessAdmin(uow.session).list_governance(
        tenant_id=principal.claims.tenant_id
    )
    return {
        "items": [
            {
                "person_id": str(r["person_id"]),
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "roles": list(r["roles"]),
            }
            for r in rows
        ]
    }


@router.put("/governance/{person_id}")
async def set_governance(
    person_id: UUID, body: GovernanceBody, principal: Principal, uow: Uow
) -> dict:
    require(await load_granted(principal, uow), perm.GOVERNANCE_MANAGE)
    return await _commit(
        uow, AccessService(uow).set_governance(actor_of(principal), person_id, body.roles)
    )
