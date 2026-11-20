"""Unit tests for pre-handler schedule catalog validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from clinic_ecosystem.infrastructure.persistence.resources_catalog import (
    ResourceRecord,
    ServiceRequirementRecord,
)
from clinic_ecosystem.infrastructure.persistence.services_catalog import ServiceCatalogItem
from clinic_ecosystem.presentation.http import schedule_validation as sv


def _service(*, active: bool = True, service_id=None):
    return ServiceCatalogItem(
        id=service_id or uuid4(),
        service_code="X",
        service_name="Svc",
        default_duration_minutes=30,
        default_price_irr=1,
        is_active=active,
    )


def _resource(*, resource_id=None, rtype="ROOM", active=True):
    return ResourceRecord(
        id=resource_id or uuid4(),
        resource_type=rtype,
        resource_name="R",
        is_active=active,
    )


@pytest.mark.asyncio
async def test_missing_service_404(monkeypatch) -> None:
    uow = MagicMock()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=None),
    )
    with pytest.raises(HTTPException) as exc:
        await sv.validate_schedule_catalog(
            uow=uow,
            tenant_id=uuid4(),
            service_id=uuid4(),
            resource_ids=[uuid4()],
        )
    assert exc.value.status_code == 404
    assert exc.value.detail["error"] == "service_not_found"


@pytest.mark.asyncio
async def test_inactive_service_400(monkeypatch) -> None:
    uow = MagicMock()
    sid = uuid4()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=_service(active=False, service_id=sid)),
    )
    with pytest.raises(HTTPException) as exc:
        await sv.validate_schedule_catalog(
            uow=uow,
            tenant_id=uuid4(),
            service_id=sid,
            resource_ids=[uuid4()],
        )
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "service_inactive"


@pytest.mark.asyncio
async def test_missing_resource_404(monkeypatch) -> None:
    uow = MagicMock()
    sid = uuid4()
    rid = uuid4()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=_service(service_id=sid)),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "get_resources_by_ids",
        AsyncMock(return_value=[]),
    )
    with pytest.raises(HTTPException) as exc:
        await sv.validate_schedule_catalog(
            uow=uow,
            tenant_id=uuid4(),
            service_id=sid,
            resource_ids=[rid],
        )
    assert exc.value.status_code == 404
    assert exc.value.detail["error"] == "resource_not_found"


@pytest.mark.asyncio
async def test_inactive_resource_400(monkeypatch) -> None:
    uow = MagicMock()
    sid = uuid4()
    rid = uuid4()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=_service(service_id=sid)),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "get_resources_by_ids",
        AsyncMock(return_value=[_resource(resource_id=rid, active=False)]),
    )
    with pytest.raises(HTTPException) as exc:
        await sv.validate_schedule_catalog(
            uow=uow,
            tenant_id=uuid4(),
            service_id=sid,
            resource_ids=[rid],
        )
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "resource_inactive"


@pytest.mark.asyncio
async def test_empty_requirements_allowed_when_service_active(monkeypatch) -> None:
    uow = MagicMock()
    sid = uuid4()
    rid = uuid4()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=_service(service_id=sid)),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "get_resources_by_ids",
        AsyncMock(return_value=[_resource(resource_id=rid)]),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "list_requirements_for_service",
        AsyncMock(return_value=[]),
    )
    await sv.validate_schedule_catalog(
        uow=uow,
        tenant_id=uuid4(),
        service_id=sid,
        resource_ids=[rid],
    )


@pytest.mark.asyncio
async def test_requirement_mismatch_400(monkeypatch) -> None:
    uow = MagicMock()
    sid = uuid4()
    rid = uuid4()
    monkeypatch.setattr(
        sv.SqlServicesCatalogRepository,
        "get_by_id",
        AsyncMock(return_value=_service(service_id=sid)),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "get_resources_by_ids",
        AsyncMock(return_value=[_resource(resource_id=rid, rtype="ROOM")]),
    )
    monkeypatch.setattr(
        sv.SqlResourcesCatalogRepository,
        "list_requirements_for_service",
        AsyncMock(
            return_value=[
                ServiceRequirementRecord(
                    id=uuid4(),
                    service_id=sid,
                    requirement_group="primary",
                    required_resource_type="PRACTITIONER",
                    specific_resource_id=None,
                    quantity_required=1,
                )
            ]
        ),
    )
    with pytest.raises(HTTPException) as exc:
        await sv.validate_schedule_catalog(
            uow=uow,
            tenant_id=uuid4(),
            service_id=sid,
            resource_ids=[rid],
        )
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "invalid_resources"
