"""Read-only bookable resources and service requirements (BETA-01B)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    id: UUID
    resource_type: str
    resource_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class ServiceRequirementRecord:
    id: UUID
    service_id: UUID
    requirement_group: str
    required_resource_type: str
    specific_resource_id: UUID | None
    quantity_required: int


class SqlResourcesCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_resources(self, *, tenant_id: UUID) -> list[ResourceRecord]:
        result = await self._session.execute(
            text(
                """
                SELECT id, resource_type, resource_name, is_active
                FROM bookable_resources
                WHERE tenant_id = :tenant_id AND is_active = TRUE
                ORDER BY resource_name ASC, id ASC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            ResourceRecord(
                id=row["id"],
                resource_type=row["resource_type"],
                resource_name=row["resource_name"],
                is_active=bool(row["is_active"]),
            )
            for row in result.mappings().all()
        ]

    async def list_requirements_for_service(
        self, *, tenant_id: UUID, service_id: UUID
    ) -> list[ServiceRequirementRecord]:
        result = await self._session.execute(
            text(
                """
                SELECT id, service_id, requirement_group, required_resource_type,
                       specific_resource_id, quantity_required
                FROM service_resource_requirements
                WHERE tenant_id = :tenant_id AND service_id = :service_id
                ORDER BY requirement_group ASC, id ASC
                """
            ),
            {"tenant_id": tenant_id, "service_id": service_id},
        )
        return [
            ServiceRequirementRecord(
                id=row["id"],
                service_id=row["service_id"],
                requirement_group=row["requirement_group"],
                required_resource_type=row["required_resource_type"],
                specific_resource_id=row["specific_resource_id"],
                quantity_required=int(row["quantity_required"]),
            )
            for row in result.mappings().all()
        ]

    async def get_active_resources_by_ids(
        self, *, tenant_id: UUID, resource_ids: list[UUID]
    ) -> list[ResourceRecord]:
        rows = await self.get_resources_by_ids(
            tenant_id=tenant_id, resource_ids=resource_ids
        )
        return [row for row in rows if row.is_active]

    async def get_resources_by_ids(
        self, *, tenant_id: UUID, resource_ids: list[UUID]
    ) -> list[ResourceRecord]:
        """Tenant-scoped lookup including inactive rows (for explicit 4xx mapping)."""
        if not resource_ids:
            return []
        result = await self._session.execute(
            text(
                """
                SELECT id, resource_type, resource_name, is_active
                FROM bookable_resources
                WHERE tenant_id = :tenant_id
                  AND id = ANY(:ids)
                """
            ),
            {"tenant_id": tenant_id, "ids": list(resource_ids)},
        )
        return [
            ResourceRecord(
                id=row["id"],
                resource_type=row["resource_type"],
                resource_name=row["resource_name"],
                is_active=bool(row["is_active"]),
            )
            for row in result.mappings().all()
        ]
