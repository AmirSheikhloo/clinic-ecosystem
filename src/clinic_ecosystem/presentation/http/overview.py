"""Dashboard metrics and global search over authorized data only (Workstream F)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from clinic_ecosystem.application.shared.errors import ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.finance_ops import SqlFinanceOps
from clinic_ecosystem.infrastructure.persistence.overview_queries import SqlOverviewQueries
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.infrastructure.persistence.waitlist_ops import SqlWaitlistOps
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
    allowed_services: set[UUID] | None = set()
    if perm.APPOINTMENTS_LIST in granted:
        from clinic_ecosystem.presentation.http.scope_access import (
            load_scopes,
            scope_service_ids,
        )

        appt_scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
        allowed_services = scope_service_ids(appt_scopes) if appt_scopes else set()
        by_status = await queries.appointment_status_counts(
            tenant_id=tenant_id,
            start_at_utc=start,
            end_at_utc=end,
            service_ids=allowed_services,
        )
        unique_patients = await queries.unique_patient_count(
            tenant_id=tenant_id,
            start_at_utc=start,
            end_at_utc=end,
            service_ids=allowed_services,
        )
        ops_metrics = await queries.operational_metric_counts(
            tenant_id=tenant_id,
            start_at_utc=start,
            end_at_utc=end,
            now_utc=datetime.now(timezone.utc),
            service_ids=allowed_services,
        )
        # Single scoped CHECKED_IN source — never diverge from waiting_room.
        waiting_checked_in = int(by_status.get("CHECKED_IN", 0))
        appointments = {
            "total": ops_metrics["today"],
            "by_status": by_status,
            "unique_patients": unique_patients,
            "waiting_checked_in": waiting_checked_in,
            "upcoming_count": ops_metrics["upcoming"],
            "needs_status_count": ops_metrics["needs_status"],
            "cancelled_count": ops_metrics["cancelled"],
        }
        # Next calendar period of equal length (for "tomorrow" when the range is one Tehran day).
        span = end - start
        if span.total_seconds() > 0 and span <= timedelta(days=31):
            tomorrow_by = await queries.appointment_status_counts(
                tenant_id=tenant_id,
                start_at_utc=end,
                end_at_utc=end + span,
                service_ids=allowed_services,
            )
            tomorrow_appointments = {
                "total": sum(tomorrow_by.values()),
                "by_status": tomorrow_by,
                "unique_patients": await queries.unique_patient_count(
                    tenant_id=tenant_id,
                    start_at_utc=end,
                    end_at_utc=end + span,
                    service_ids=allowed_services,
                ),
            }
    waiting_room = None
    future_waitlist = None
    if perm.WAITLIST_VIEW in granted or perm.APPOINTMENTS_LIST in granted:
        wait_ops = SqlWaitlistOps(uow.session)
        if await wait_ops.schema_ready():
            # Same scoped CHECKED_IN count as appointments.waiting_checked_in.
            if appointments is not None:
                wr_count = int(appointments["waiting_checked_in"])
            else:
                from clinic_ecosystem.presentation.http.scope_access import (
                    load_scopes,
                    scope_service_ids,
                )

                wr_scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
                wr_services = scope_service_ids(wr_scopes) if wr_scopes else set()
                wr_by = await queries.appointment_status_counts(
                    tenant_id=tenant_id,
                    start_at_utc=start,
                    end_at_utc=end,
                    service_ids=wr_services,
                )
                wr_count = int(wr_by.get("CHECKED_IN", 0))
            waiting_room = {"checked_in_count": wr_count}
            if perm.WAITLIST_VIEW in granted:
                future_waitlist = {
                    "open_count": await wait_ops.future_waitlist_open_count(tenant_id=tenant_id)
                }
    finance = None
    if perm.FINANCE_SUMMARY in granted:
        finance_ops = SqlFinanceOps(uow.session)
        if await finance_ops.schema_ready():
            finance = await finance_ops.financial_summary(
                tenant_id=tenant_id, start_at_utc=start, end_at_utc=end
            )
    return {
        "appointments": appointments,
        "tomorrow_appointments": tomorrow_appointments,
        "waiting_room": waiting_room,
        "future_waitlist": future_waitlist,
        "finance": finance,
        "patients_active": await queries.active_patients(tenant_id)
        if perm.PATIENTS_SEARCH in granted else None,
        "staff_active": await queries.active_staff(tenant_id)
        if perm.STAFF_VIEW in granted else None,
        "services_active": await queries.active_services(tenant_id)
        if perm.CATALOG_SERVICES_READ in granted else None,
        "resources_active": await queries.active_resources(tenant_id)
        if perm.CATALOG_RESOURCES_READ in granted else None,
    }


@router.get("/dashboard/day")
async def dashboard_day(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
    metric: Annotated[str, Query()] = "today",
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
) -> dict:
    """Authoritative operational day dataset with exact metric predicates + pagination."""
    granted = await load_granted(principal, uow)
    if perm.APPOINTMENTS_LIST not in granted:
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "metric": metric}
    from clinic_ecosystem.presentation.http.scope_access import load_scopes, scope_service_ids

    start, end = _aware(start_at_utc, "start_at_utc"), _aware(end_at_utc, "end_at_utc")
    if end <= start or (end - start).days > 31:
        raise ValidationFailed("Invalid day range", code="invalid_time_range")
    if metric not in {"today", "upcoming", "needs_status", "cancelled"}:
        raise ValidationFailed("Invalid metric filter", code="invalid_metric")
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
    allowed_services = scope_service_ids(scopes) if scopes else set()
    queries = SqlOverviewQueries(uow.session)
    tenant_id = principal.claims.tenant_id
    rows, total = await queries.list_operational_day(
        tenant_id=tenant_id,
        start_at_utc=start,
        end_at_utc=end,
        now_utc=datetime.now(timezone.utc),
        metric=metric,
        q=q,
        limit=limit,
        offset=offset,
        service_ids=allowed_services,
    )
    patient_ids = [r["patient_profile_id"] for r in rows]
    insurance_by_patient = await queries.insurance_labels_for_patients(
        tenant_id=tenant_id, patient_ids=patient_ids
    )
    finance_by_appt: dict[UUID, dict] = {}
    # Fail-closed: finance enrichment only with invoice-view permission + ops schema.
    if perm.FINANCE_INVOICE_VIEW in granted and rows:
        finance_ops = SqlFinanceOps(uow.session)
        if await finance_ops.schema_ready():
            finance_by_appt = await finance_ops.balances_for_appointments(
                tenant_id=tenant_id,
                appointment_ids=[r["appointment_id"] for r in rows],
            )
    items: list[dict] = []
    for r in rows:
        resources = list(r.get("resource_names") or [])
        fin = finance_by_appt.get(r["appointment_id"])
        item: dict = {
            "appointment_id": str(r["appointment_id"]),
            "patient_profile_id": str(r["patient_profile_id"]),
            "patient_first_name": r["patient_first_name"],
            "patient_last_name": r["patient_last_name"],
            "service_id": str(r["service_id"]),
            "service_name": r["service_name"],
            "status": r["status"],
            "scheduled_start_at_utc": r["scheduled_start_at_utc"].isoformat(),
            "scheduled_end_at_utc": r["scheduled_end_at_utc"].isoformat(),
            "booking_channel": r["booking_channel"],
            "capacity_pool": r["capacity_pool"],
            "aggregate_version": r["aggregate_version"],
            "resource_names": resources,
            "national_id_masked": r.get("national_id_masked"),
            "patient_phone_masked": r.get("patient_phone_masked"),
            "insurance_label": insurance_by_patient.get(r["patient_profile_id"]),
            "practitioner_name": resources[0] if resources else None,
        }
        if fin is not None:
            item["financial_status_label"] = fin.get("financial_status")
            item["outstanding_irr"] = fin.get("outstanding")
        items.append(item)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "metric": metric,
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
