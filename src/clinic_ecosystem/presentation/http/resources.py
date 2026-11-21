"""Read-only bookable resources and service requirements (BETA-01B)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from clinic_ecosystem.infrastructure.auth.settings import CATALOG_RESOURCES_READ
from clinic_ecosystem.infrastructure.persistence.resources_catalog import (
    SqlResourcesCatalogRepository,
)
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


class ResourceItemResponse(BaseModel):
    id: str
    resource_type: str
    resource_name: str
    is_active: bool


class ResourceListResponse(BaseModel):
    items: list[ResourceItemResponse]


class RequirementItemResponse(BaseModel):
    id: str
    service_id: str
    requirement_group: str
    required_resource_type: str
    specific_resource_id: str | None
    quantity_required: int


class RequirementListResponse(BaseModel):
    items: list[RequirementItemResponse]


@router.get("/resources", response_model=ResourceListResponse)
async def list_resources(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> ResourceListResponse:
    await require_permission(CATALOG_RESOURCES_READ, principal=principal, uow=uow)
    repo = SqlResourcesCatalogRepository(uow.session)
    rows = await repo.list_active_resources(tenant_id=principal.claims.tenant_id)
    return ResourceListResponse(
        items=[
            ResourceItemResponse(
                id=str(item.id),
                resource_type=item.resource_type,
                resource_name=item.resource_name,
                is_active=item.is_active,
            )
            for item in rows
        ]
    )


@router.get(
    "/services/{service_id}/resource-requirements",
    response_model=RequirementListResponse,
)
async def list_service_requirements(
    service_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> RequirementListResponse:
    await require_permission(CATALOG_RESOURCES_READ, principal=principal, uow=uow)
    services = SqlServicesCatalogRepository(uow.session)
    service = await services.get_by_id(
        tenant_id=principal.claims.tenant_id,
        service_id=service_id,
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "service_not_found", "message": "Service not found"},
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "service_inactive",
                "message": "Service is not active",
            },
        )

    repo = SqlResourcesCatalogRepository(uow.session)
    rows = await repo.list_requirements_for_service(
        tenant_id=principal.claims.tenant_id,
        service_id=service_id,
    )
    # Empty list is valid for an existing active service with no requirements.
    return RequirementListResponse(
        items=[
            RequirementItemResponse(
                id=str(item.id),
                service_id=str(item.service_id),
                requirement_group=item.requirement_group,
                required_resource_type=item.required_resource_type,
                specific_resource_id=(
                    str(item.specific_resource_id)
                    if item.specific_resource_id is not None
                    else None
                ),
                quantity_required=item.quantity_required,
            )
            for item in rows
        ]
    )
