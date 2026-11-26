"""Catalog (services + rooms) fixture builders for the demo dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.infrastructure.demo.ids import demo_uuid
from clinic_ecosystem.infrastructure.demo.names import ROOM_NAMES, SERVICE_CATALOG
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets


@dataclass(frozen=True)
class ServiceRow:
    id: UUID
    code: str
    name: str
    duration_minutes: int
    price_irr: int


@dataclass(frozen=True)
class ResourceRow:
    id: UUID
    resource_type: str
    name: str
    is_active: bool = True


@dataclass(frozen=True)
class RequirementRow:
    id: UUID
    service_id: UUID
    group: str
    resource_type: str
    specific_resource_id: UUID | None
    quantity: int = 1


@dataclass(frozen=True)
class CatalogBundle:
    services: list[ServiceRow]
    rooms: list[ResourceRow]
    requirements: list[RequirementRow]


def build_catalog(targets: DemoTargets, *, now: datetime) -> CatalogBundle:
    _ = now
    services: list[ServiceRow] = []
    for i in range(targets.services):
        code, name, duration, price = SERVICE_CATALOG[i % len(SERVICE_CATALOG)]
        # Disambiguate when cycling the catalog.
        suffix = f"-{i // len(SERVICE_CATALOG) + 1}" if i >= len(SERVICE_CATALOG) else ""
        services.append(
            ServiceRow(
                id=demo_uuid(targets.seed, "service", i),
                code=f"{code}{suffix}" if suffix else code,
                name=f"{name}{suffix}",
                duration_minutes=duration,
                price_irr=price,
            )
        )
    rooms: list[ResourceRow] = []
    for i in range(targets.resources_rooms):
        rooms.append(
            ResourceRow(
                id=demo_uuid(targets.seed, "room", i),
                resource_type="ROOM",
                name=ROOM_NAMES[i % len(ROOM_NAMES)]
                + (f" #{i}" if i >= len(ROOM_NAMES) else ""),
            )
        )
    requirements: list[RequirementRow] = []
    for i, svc in enumerate(services):
        requirements.append(
            RequirementRow(
                id=demo_uuid(targets.seed, "svc_req", i),
                service_id=svc.id,
                group="primary",
                resource_type="ROOM",
                specific_resource_id=None,
            )
        )
    return CatalogBundle(services=services, rooms=rooms, requirements=requirements)
