"""Pre-handler tenant-scoped service/resource validation for BETA-01B scheduling."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from clinic_ecosystem.application.scheduling.exceptions import ServiceRequirementsNotMet
from clinic_ecosystem.application.scheduling.ports import validate_resource_set
from clinic_ecosystem.infrastructure.persistence.resources_catalog import (
    SqlResourcesCatalogRepository,
)
from clinic_ecosystem.infrastructure.persistence.services_catalog import (
    SqlServicesCatalogRepository,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


async def validate_schedule_catalog(
    *,
    uow: SqlAlchemyUnitOfWork,
    tenant_id: UUID,
    service_id: UUID,
    resource_ids: list[UUID],
) -> None:
    """Reject unknown/inactive/cross-tenant services and incompatible resources with 4xx.

    Empty requirement lists are allowed only when the service exists and is active
    (approved domain contract via validate_resource_set). Missing services must never
    fall through to foreign-key failures.
    """
    services = SqlServicesCatalogRepository(uow.session)
    service = await services.get_by_id(tenant_id=tenant_id, service_id=service_id)
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

    unique_ids = list(dict.fromkeys(resource_ids))
    if len(unique_ids) != len(resource_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_resources",
                "message": "Duplicate resource ids are not allowed",
            },
        )

    resources_repo = SqlResourcesCatalogRepository(uow.session)
    found = await resources_repo.get_resources_by_ids(
        tenant_id=tenant_id, resource_ids=unique_ids
    )
    found_by_id = {item.id: item for item in found}
    missing = [rid for rid in unique_ids if rid not in found_by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "resource_not_found",
                "message": "One or more resources were not found",
            },
        )
    inactive = [rid for rid in unique_ids if not found_by_id[rid].is_active]
    if inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "resource_inactive",
                "message": "One or more resources are not active",
            },
        )

    requirements = await resources_repo.list_requirements_for_service(
        tenant_id=tenant_id, service_id=service_id
    )
    req_dicts = [
        {
            "requirement_group": item.requirement_group,
            "required_resource_type": item.required_resource_type,
            "specific_resource_id": item.specific_resource_id,
            "quantity_required": item.quantity_required,
        }
        for item in requirements
    ]
    resource_types = {item.id: item.resource_type for item in found}
    try:
        validate_resource_set(req_dicts, resource_types, unique_ids)
    except ServiceRequirementsNotMet as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_resources", "message": str(exc)},
        ) from None
