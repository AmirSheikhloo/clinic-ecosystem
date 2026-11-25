"""Dashboard metrics and global search over authorized data only (Workstream F)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from clinic_ecosystem.application.shared.errors import ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.overview_queries import SqlOverviewQueries
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1", tags=["overview"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise ValidationFailed(f"{field} must include a timezone offset", code="invalid_datetime")
    return value.astimezone(timezone.utc)


@router.get("/dashboard/summary")
async def dashboard_summary(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
) -> dict:
    """Each section is null when the caller lacks the matching permission."""
    granted = await load_granted(principal, uow)
    start, end = _aware(start_at_utc, "start_at_utc"), _aware(end_at_utc, "end_at_utc")
    if end <= start or (end - start).days > 31:
        raise ValidationFailed("Invalid summary range", code="invalid_time_range")
    queries = SqlOverviewQueries(uow.session)
    tenant_id = principal.claims.tenant_id
    appointments = None
    tomorrow_appointments = None
    if perm.APPOINTMENTS_LIST in granted:
        by_status = await queries.appointment_status_counts(
            tenant_id=tenant_id, start_at_utc=start, end_at_utc=end
        )
        appointments = {"total": sum(by_status.values()), "by_status": by_status}
        # Next calendar period of equal length (for "tomorrow" when the range is one Tehran day).
        span = end - start
        if span.total_seconds() > 0 and span <= timedelta(days=31):
            tomorrow_by = await queries.appointment_status_counts(
                tenant_id=tenant_id, start_at_utc=end, end_at_utc=end + span
            )
            tomorrow_appointments = {
                "total": sum(tomorrow_by.values()),
                "by_status": tomorrow_by,
            }
    return {
        "appointments": appointments,
        "tomorrow_appointments": tomorrow_appointments,
        "patients_active": await queries.active_patients(tenant_id)
        if perm.PATIENTS_SEARCH in granted else None,
        "staff_active": await queries.active_staff(tenant_id)
        if perm.STAFF_VIEW in granted else None,
        "services_active": await queries.active_services(tenant_id)
        if perm.CATALOG_SERVICES_READ in granted else None,
        "resources_active": await queries.active_resources(tenant_id)
        if perm.CATALOG_RESOURCES_READ in granted else None,
    }


@router.get("/search")
async def global_search(
    principal: Principal,
    uow: Uow,
    q: Annotated[str, Query(min_length=2, max_length=120)],
) -> dict:
    granted = await load_granted(principal, uow)
    queries = SqlOverviewQueries(uow.session)
    tenant_id = principal.claims.tenant_id
    term = q.strip()
    if len(term) < 2:
        raise ValidationFailed("Search term is too short", code="query_too_short")
    results: list[dict] = []
    if perm.PATIENTS_SEARCH in granted:
        for r in await queries.search_patients(tenant_id=tenant_id, q=term, limit=5):
            results.append({
                "kind": "patient", "id": str(r["id"]),
                "title": f"{r['first_name']} {r['last_name']}",
                "subtitle": r["dossier_number"],
            })
    if perm.STAFF_VIEW in granted:
        for r in await queries.search_staff(tenant_id=tenant_id, q=term, limit=5):
            results.append({
                "kind": "staff", "id": str(r["id"]),
                "title": f"{r['first_name']} {r['last_name']}", "subtitle": r["staff_kind"],
            })
    if perm.CATALOG_SERVICES_READ in granted:
        for r in await queries.search_services(tenant_id=tenant_id, q=term, limit=5):
            results.append({
                "kind": "service", "id": str(r["id"]),
                "title": r["service_name"], "subtitle": r["service_code"],
            })
    return {"items": results}
