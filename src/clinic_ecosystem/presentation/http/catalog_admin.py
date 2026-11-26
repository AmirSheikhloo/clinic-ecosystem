"""Manager-only services and resources administration routes (Workstream E)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, Field

from clinic_ecosystem.application.catalog_admin.service import RESOURCE_TYPES, CatalogAdminService
from clinic_ecosystem.application.shared.errors import NotFound
from clinic_ecosystem.application.shared.idempotent import run_idempotent, validate_key
from clinic_ecosystem.application.shared.preconditions import parse_if_match
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.catalog_admin import SqlCatalogAdmin
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import actor_of, load_granted, require, set_etag
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/catalog/admin", tags=["catalog-admin"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
_STATUS = "^(active|inactive|all)$"


class ServiceCreate(BaseModel):
    service_name: str = Field(max_length=200)
    service_code: str | None = Field(default=None, max_length=64)
    default_duration_minutes: int
    default_price_irr: int


class ServicePatch(BaseModel):
    service_name: str | None = Field(default=None, max_length=200)
    service_code: str | None = Field(default=None, max_length=64)
    default_duration_minutes: int | None = None
    default_price_irr: int | None = None
    is_active: bool | None = None


class RequirementIn(BaseModel):
    requirement_group: str = Field(max_length=64)
    required_resource_type: str = Field(max_length=40)
    specific_resource_id: UUID | None = None
    quantity_required: int = 1


class RequirementsBody(BaseModel):
    items: list[RequirementIn] = Field(max_length=20)


class ResourceCreate(BaseModel):
    resource_type: str = Field(max_length=40)
    resource_name: str = Field(max_length=200)


class ResourcePatch(BaseModel):
    resource_name: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


def _service_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "service_id": str(row["service_id"]),
        "service_code": row["service_code"],
        "service_name": row["service_name"],
        "default_duration_minutes": row["default_duration_minutes"],
        "default_price_irr": row["default_price_irr"],
        "is_active": row["is_active"],
        "aggregate_version": int(row["aggregate_version"]),
        **({"requirement_count": int(row["requirement_count"])} if "requirement_count" in row else {}),
    }


def _resource_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": str(row["resource_id"]),
        "resource_type": row["resource_type"],
        "resource_name": row["resource_name"],
        "is_active": row["is_active"],
    }


async def _commit(uow: SqlAlchemyUnitOfWork, work):
    try:
        result = await work
        await uow.commit()
        return result
    except BaseException:
        await uow.rollback()
        raise


def _flag(value: str) -> bool | None:
    return {"active": True, "inactive": False, "all": None}[value]


@router.get("/services")
async def list_services(
    principal: Principal,
    uow: Uow,
    q: Annotated[str | None, Query(max_length=120)] = None,
    status_filter: Annotated[str, Query(alias="status", pattern=_STATUS)] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_SERVICES_MANAGE)
    rows, total = await SqlCatalogAdmin(uow.session).list_services(
        tenant_id=principal.claims.tenant_id, q=(q or "").strip() or None,
        is_active=_flag(status_filter), limit=limit, offset=offset,
    )
    return {"items": [_service_view(r) for r in rows], "total": total,
            "limit": limit, "offset": offset}


@router.get("/services/{service_id}")
async def get_service(service_id: UUID, principal: Principal, uow: Uow, response: Response) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_SERVICES_MANAGE)
    catalog = SqlCatalogAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    row = await catalog.get_service(tenant_id=tenant_id, service_id=service_id)
    if row is None:
        raise NotFound("Service not found", code="service_not_found")
    requirements = await catalog.list_requirements(tenant_id=tenant_id, service_id=service_id)
    set_etag(response, int(row["aggregate_version"]))
    return {
        **_service_view(row),
        "requirements": [
            {
                "requirement_id": str(r["requirement_id"]),
                "requirement_group": r["requirement_group"],
                "required_resource_type": r["required_resource_type"],
                "specific_resource_id": str(r["specific_resource_id"]) if r["specific_resource_id"] else None,
                "specific_resource_name": r["specific_resource_name"],
                "quantity_required": r["quantity_required"],
            }
            for r in requirements
        ],
    }


@router.post("/services", status_code=status.HTTP_201_CREATED)
async def create_service(
    body: ServiceCreate, principal: Principal, uow: Uow, response: Response,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_SERVICES_MANAGE)
    key = validate_key(idempotency_key)
    actor = actor_of(principal)
    service = CatalogAdminService(uow)
    fields = body.model_dump()
    result, replayed = await run_idempotent(
        uow, tenant_id=actor.tenant_id, principal_id=actor.account_id,
        scope="catalog.service.create", key=key, request_payload=fields,
        action=lambda: service.create_service(actor, fields),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.patch("/services/{service_id}")
async def patch_service(
    service_id: UUID, body: ServicePatch, principal: Principal, uow: Uow, response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_SERVICES_MANAGE)
    expected = parse_if_match(if_match)
    fields = {k: getattr(body, k) for k in body.model_fields_set}
    result = await _commit(
        uow, CatalogAdminService(uow).update_service(actor_of(principal), service_id, expected, fields)
    )
    set_etag(response, result["aggregate_version"])
    return result


@router.put("/services/{service_id}/requirements")
async def put_requirements(
    service_id: UUID, body: RequirementsBody, principal: Principal, uow: Uow, response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_SERVICES_MANAGE)
    expected = parse_if_match(if_match)
    items = [i.model_dump() for i in body.items]
    result = await _commit(
        uow,
        CatalogAdminService(uow).replace_requirements(
            actor_of(principal), service_id, expected, items
        ),
    )
    set_etag(response, result["aggregate_version"])
    return result


@router.get("/resources")
async def list_resources(
    principal: Principal,
    uow: Uow,
    q: Annotated[str | None, Query(max_length=120)] = None,
    resource_type: Annotated[str | None, Query(max_length=40)] = None,
    status_filter: Annotated[str, Query(alias="status", pattern=_STATUS)] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_RESOURCES_MANAGE)
    rows, total = await SqlCatalogAdmin(uow.session).list_resources(
        tenant_id=principal.claims.tenant_id, q=(q or "").strip() or None,
        resource_type=resource_type if resource_type in RESOURCE_TYPES else None,
        is_active=_flag(status_filter), limit=limit, offset=offset,
    )
    return {"items": [_resource_view(r) for r in rows], "total": total,
            "limit": limit, "offset": offset}


@router.post("/resources", status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ResourceCreate, principal: Principal, uow: Uow, response: Response,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_RESOURCES_MANAGE)
    key = validate_key(idempotency_key)
    actor = actor_of(principal)
    service = CatalogAdminService(uow)
    result, replayed = await run_idempotent(
        uow, tenant_id=actor.tenant_id, principal_id=actor.account_id,
        scope="catalog.resource.create", key=key, request_payload=body.model_dump(),
        action=lambda: service.create_resource(actor, body.resource_type, body.resource_name),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.patch("/resources/{resource_id}")
async def patch_resource(
    resource_id: UUID, body: ResourcePatch, principal: Principal, uow: Uow
) -> dict:
    require(await load_granted(principal, uow), perm.CATALOG_RESOURCES_MANAGE)
    fields = {k: getattr(body, k) for k in body.model_fields_set}
    return await _commit(
        uow, CatalogAdminService(uow).update_resource(actor_of(principal), resource_id, fields)
    )
