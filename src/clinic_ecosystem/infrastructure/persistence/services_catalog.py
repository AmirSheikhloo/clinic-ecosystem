"""Read-only services catalog queries under verified tenant context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ServiceCatalogItem:
    id: UUID
    service_code: str | None
    service_name: str
    default_duration_minutes: int
    default_price_irr: int
    is_active: bool


class SqlServicesCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_services(self, *, tenant_id: UUID) -> list[ServiceCatalogItem]:
        result = await self._session.execute(
            text(
                """
                SELECT id, service_code, service_name, default_duration_minutes,
                       default_price_irr, is_active
                FROM services
                WHERE tenant_id = :tenant_id
                  AND is_active = TRUE
                ORDER BY service_name ASC, id ASC
                """
            ),
            {"tenant_id": tenant_id},
        )
        items: list[ServiceCatalogItem] = []
        for row in result.mappings().all():
            items.append(
                ServiceCatalogItem(
                    id=row["id"],
                    service_code=row["service_code"],
                    service_name=row["service_name"],
                    default_duration_minutes=int(row["default_duration_minutes"]),
                    default_price_irr=int(row["default_price_irr"]),
                    is_active=bool(row["is_active"]),
                )
            )
        return items

    async def get_by_id(
        self, *, tenant_id: UUID, service_id: UUID
    ) -> ServiceCatalogItem | None:
        """Tenant-scoped lookup including inactive rows (for explicit 4xx mapping)."""
        result = await self._session.execute(
            text(
                """
                SELECT id, service_code, service_name, default_duration_minutes,
                       default_price_irr, is_active
                FROM services
                WHERE tenant_id = :tenant_id AND id = :service_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "service_id": service_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return ServiceCatalogItem(
            id=row["id"],
            service_code=row["service_code"],
            service_name=row["service_name"],
            default_duration_minutes=int(row["default_duration_minutes"]),
            default_price_irr=int(row["default_price_irr"]),
            is_active=bool(row["is_active"]),
        )
