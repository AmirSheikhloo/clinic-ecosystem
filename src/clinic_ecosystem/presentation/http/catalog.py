"""Read-only clinic catalog HTTP routes for BETA-01A."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from clinic_ecosystem.infrastructure.auth.settings import CATALOG_SERVICES_READ
from clinic_ecosystem.infrastructure.persistence.services_catalog import (
    SqlServicesCatalogRepository,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
    require_permission,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


class ServiceItemResponse(BaseModel):
    id: str
    service_code: str | None
    service_name: str
    default_duration_minutes: int
    default_price_irr: int
    is_active: bool


class ServiceListResponse(BaseModel):
    items: list[ServiceItemResponse]


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> ServiceListResponse:
    await require_permission(
        CATALOG_SERVICES_READ,
        principal=principal,
        uow=uow,
    )
    repo = SqlServicesCatalogRepository(uow.session)
    rows = await repo.list_active_services(tenant_id=principal.claims.tenant_id)
    return ServiceListResponse(
        items=[
            ServiceItemResponse(
                id=str(item.id),
                service_code=item.service_code,
                service_name=item.service_name,
                default_duration_minutes=item.default_duration_minutes,
                default_price_irr=item.default_price_irr,
                is_active=item.is_active,
            )
            for item in rows
        ]
    )
