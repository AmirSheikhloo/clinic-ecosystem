"""Supporting ops management: departments, eligibility, online closures, inventory view."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from clinic_ecosystem.application.shared.errors import Conflict, ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/ops", tags=["ops-management"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


async def _ops_table(uow: Uow, name: str) -> bool:
    row = await uow.session.execute(
        text("SELECT to_regclass(:q) IS NOT NULL AS ok"),
        {"q": f"public.{name}"},
    )
    return bool(row.mappings().one()["ok"])


class DepartmentIn(BaseModel):
    department_code: str = Field(min_length=1, max_length=64)
    department_name: str = Field(min_length=1, max_length=200)


class EligibilityIn(BaseModel):
    practitioner_mapping_id: UUID
    service_id: UUID
    is_active: bool = True


class OnlineClosureIn(BaseModel):
    service_id: UUID
    closure_date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD Tehran calendar day")
    starts_at_utc: datetime
    ends_at_utc: datetime
    reason: str = Field(min_length=1, max_length=200)


@router.get("/departments")
async def list_departments(principal: Principal, uow: Uow) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.DEPARTMENTS_VIEW)
    if not await _ops_table(uow, "departments"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    result = await uow.session.execute(
        text(
            """
            SELECT id, department_code, department_name, is_active, aggregate_version
            FROM departments
            WHERE tenant_id = :tenant_id
            ORDER BY department_code
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "department_code": r["department_code"],
                "department_name": r["department_name"],
                "is_active": r["is_active"],
                "aggregate_version": r["aggregate_version"],
            }
            for r in result.mappings().all()
        ]
    }


@router.post("/departments")
async def create_department(principal: Principal, uow: Uow, body: DepartmentIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.DEPARTMENTS_MANAGE)
    if not await _ops_table(uow, "departments"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    dept_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO departments (
              id, tenant_id, department_code, department_name, is_active,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES (:id, :tenant_id, :code, :name, TRUE, 1, :now, :now)
            """
        ),
        {
            "id": dept_id,
            "tenant_id": principal.claims.tenant_id,
            "code": body.department_code,
            "name": body.department_name,
            "now": now,
        },
    )
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="ops.department_created",
        target_type="department",
        target_id=dept_id,
        details={"department_code": body.department_code},
    )
    await uow.commit()
    return {"id": str(dept_id), "department_code": body.department_code}


@router.get("/eligibility")
async def list_eligibility(
    principal: Principal,
    uow: Uow,
    service_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ELIGIBILITY_MANAGE)
    if not await _ops_table(uow, "staff_service_links"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    clauses = ["ssl.tenant_id = :tenant_id"]
    params: dict[str, Any] = {"tenant_id": principal.claims.tenant_id}
    if service_id:
        clauses.append("ssl.service_id = :service_id")
        params["service_id"] = service_id
    where = " AND ".join(clauses)
    result = await uow.session.execute(
        text(
            f"""
            SELECT ssl.id, ssl.service_id, ssl.practitioner_mapping_id, ssl.is_active,
                   s.service_name, spr.bookable_resource_id
            FROM staff_service_links ssl
            JOIN services s ON s.tenant_id = ssl.tenant_id AND s.id = ssl.service_id
            JOIN staff_practitioner_resources spr
              ON spr.tenant_id = ssl.tenant_id AND spr.id = ssl.practitioner_mapping_id
            WHERE {where}
            ORDER BY s.service_name, ssl.id
            """
        ),
        params,
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "service_id": str(r["service_id"]),
                "service_name": r["service_name"],
                "practitioner_mapping_id": str(r["practitioner_mapping_id"]),
                "bookable_resource_id": str(r["bookable_resource_id"]),
                "is_active": r["is_active"],
            }
            for r in result.mappings().all()
        ]
    }


@router.post("/eligibility")
async def upsert_eligibility(principal: Principal, uow: Uow, body: EligibilityIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ELIGIBILITY_MANAGE)
    if not await _ops_table(uow, "staff_service_links"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    link_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO staff_service_links (
              id, tenant_id, practitioner_mapping_id, service_id, is_active,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES (:id, :tenant_id, :mapping, :service_id, :active, 1, :now, :now)
            ON CONFLICT (tenant_id, practitioner_mapping_id, service_id)
            DO UPDATE SET
              is_active = EXCLUDED.is_active,
              updated_at_utc = EXCLUDED.updated_at_utc,
              aggregate_version = staff_service_links.aggregate_version + 1
            """
        ),
        {
            "id": link_id,
            "tenant_id": principal.claims.tenant_id,
            "mapping": body.practitioner_mapping_id,
            "service_id": body.service_id,
            "active": body.is_active,
            "now": now,
        },
    )
    await uow.commit()
    return {
        "practitioner_mapping_id": str(body.practitioner_mapping_id),
        "service_id": str(body.service_id),
        "is_active": body.is_active,
    }


@router.get("/inventory/items")
async def list_inventory(principal: Principal, uow: Uow) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.INVENTORY_VIEW)
    if not await _ops_table(uow, "inventory_items"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    result = await uow.session.execute(
        text(
            """
            SELECT i.id, i.item_code, i.item_name, i.unit_code, i.is_active,
                   COALESCE((
                     SELECT SUM(m.quantity_delta)
                     FROM stock_movements m
                     JOIN inventory_lots l ON l.tenant_id = m.tenant_id AND l.id = m.lot_id
                     WHERE m.tenant_id = i.tenant_id AND m.item_id = i.id
                       AND l.lot_status = 'AVAILABLE'
                   ), 0) AS on_hand
            FROM inventory_items i
            WHERE i.tenant_id = :tenant_id
            ORDER BY i.item_code
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "unit_code": r["unit_code"],
                "is_active": r["is_active"],
                "quantity_on_hand": int(r["on_hand"]),
            }
            for r in result.mappings().all()
        ]
    }


@router.post("/online-closures")
async def create_online_closure(principal: Principal, uow: Uow, body: OnlineClosureIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.ONLINE_CLOSURE_MANAGE)
    if not await _ops_table(uow, "online_availability_closures"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    if body.ends_at_utc <= body.starts_at_utc:
        raise ValidationFailed("Invalid closure window", code="invalid_time_range")
    now = datetime.now(timezone.utc)
    closure_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO online_availability_closures (
              id, tenant_id, service_id, closure_date, starts_at_utc, ends_at_utc,
              reason, created_by_user_id, aggregate_version, created_at_utc
            ) VALUES (
              :id, :tenant_id, :service_id, CAST(:closure_date AS date),
              :starts_at, :ends_at, :reason, :user_id, 1, :now
            )
            """
        ),
        {
            "id": closure_id,
            "tenant_id": principal.claims.tenant_id,
            "service_id": body.service_id,
            "closure_date": body.closure_date,
            "starts_at": body.starts_at_utc.astimezone(timezone.utc),
            "ends_at": body.ends_at_utc.astimezone(timezone.utc),
            "reason": body.reason,
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await uow.commit()
    return {"id": str(closure_id)}


class InventoryWriteOffIn(BaseModel):
    item_id: UUID
    lot_id: UUID
    quantity: int = Field(ge=1)
    reason_code: str = Field(min_length=1, max_length=64)


class InventoryReturnIn(BaseModel):
    item_id: UUID
    lot_id: UUID
    original_movement_id: UUID
    quantity: int = Field(ge=1)
    disposition: str = Field(pattern="^(REUSABLE|QUARANTINE|WRITE_OFF)$")
    reason_code: str = Field(min_length=1, max_length=64)


class InventoryQuarantineIn(BaseModel):
    item_id: UUID
    lot_id: UUID
    reason_code: str = Field(min_length=1, max_length=64)


@router.post("/inventory/write-off")
async def inventory_write_off(principal: Principal, uow: Uow, body: InventoryWriteOffIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.INVENTORY_ADJUST)
    if not await _ops_table(uow, "stock_movements"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    movement_id = new_uuid7()
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO stock_movements (
                  id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
                  reason_code, operator_user_id, actor_type, actor_id, correlation_id,
                  occurred_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :item_id, :lot_id, 'WRITE_OFF', :qty, 0, :reason,
                  :user_id, 'STAFF_USER', :user_id, :corr, :now, :now
                )
                """
            ),
            {
                "id": movement_id,
                "tenant_id": principal.claims.tenant_id,
                "item_id": body.item_id,
                "lot_id": body.lot_id,
                "qty": -abs(body.quantity),
                "reason": body.reason_code,
                "user_id": principal.account.id,
                "corr": new_uuid7(),
                "now": now,
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise Conflict(
            "Write-off rejected",
            code="inventory_write_off_rejected",
            extra={"detail": str(exc.__class__.__name__)},
        ) from exc
    await uow.commit()
    return {"id": str(movement_id), "movement_kind": "WRITE_OFF"}


@router.post("/inventory/return")
async def inventory_return(principal: Principal, uow: Uow, body: InventoryReturnIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.INVENTORY_ADJUST)
    if not await _ops_table(uow, "stock_movements"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    movement_id = new_uuid7()
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO stock_movements (
                  id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
                  original_movement_id, return_disposition, reason_code, operator_user_id,
                  actor_type, actor_id, correlation_id, occurred_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :item_id, :lot_id, 'RETURN', :qty, 0, :orig, :disp, :reason,
                  :user_id, 'STAFF_USER', :user_id, :corr, :now, :now
                )
                """
            ),
            {
                "id": movement_id,
                "tenant_id": principal.claims.tenant_id,
                "item_id": body.item_id,
                "lot_id": body.lot_id,
                "qty": abs(body.quantity),
                "orig": body.original_movement_id,
                "disp": body.disposition,
                "reason": body.reason_code,
                "user_id": principal.account.id,
                "corr": new_uuid7(),
                "now": now,
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise Conflict(
            "Return rejected",
            code="inventory_return_rejected",
            extra={"detail": str(exc.__class__.__name__)},
        ) from exc
    await uow.commit()
    return {"id": str(movement_id), "movement_kind": "RETURN"}


@router.post("/inventory/quarantine")
async def inventory_quarantine(
    principal: Principal, uow: Uow, body: InventoryQuarantineIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.INVENTORY_ADJUST)
    if not await _ops_table(uow, "inventory_lot_state_events"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    event_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO inventory_lot_state_events (
              id, tenant_id, item_id, lot_id, old_status, new_status, reason_code,
              operator_user_id, occurred_at_utc, created_at_utc
            ) VALUES (
              :id, :tenant_id, :item_id, :lot_id, 'AVAILABLE', 'QUARANTINE', :reason,
              :user_id, :now, :now
            )
            """
        ),
        {
            "id": event_id,
            "tenant_id": principal.claims.tenant_id,
            "item_id": body.item_id,
            "lot_id": body.lot_id,
            "reason": body.reason_code,
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await uow.session.execute(
        text(
            """
            UPDATE inventory_lots
            SET lot_status = 'QUARANTINE', aggregate_version = aggregate_version + 1,
                updated_at_utc = :now
            WHERE tenant_id = :tenant_id AND id = :lot_id AND item_id = :item_id
              AND lot_status = 'AVAILABLE'
            """
        ),
        {
            "now": now,
            "tenant_id": principal.claims.tenant_id,
            "lot_id": body.lot_id,
            "item_id": body.item_id,
        },
    )
    await uow.commit()
    return {"id": str(event_id), "lot_status": "QUARANTINE"}


@router.get("/inventory/lots")
async def list_lots(
    principal: Principal,
    uow: Uow,
    item_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.INVENTORY_VIEW)
    if not await _ops_table(uow, "inventory_lots"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    clauses = ["l.tenant_id = :tenant_id"]
    params: dict[str, Any] = {"tenant_id": principal.claims.tenant_id}
    if item_id:
        clauses.append("l.item_id = :item_id")
        params["item_id"] = item_id
    where = " AND ".join(clauses)
    result = await uow.session.execute(
        text(
            f"""
            SELECT l.id, l.item_id, l.lot_code, l.lot_status, l.expires_on,
                   i.item_code, i.item_name,
                   COALESCE((
                     SELECT SUM(m.quantity_delta) FROM stock_movements m
                     WHERE m.tenant_id = l.tenant_id AND m.lot_id = l.id
                   ), 0) AS on_hand
            FROM inventory_lots l
            JOIN inventory_items i ON i.tenant_id = l.tenant_id AND i.id = l.item_id
            WHERE {where}
            ORDER BY l.expires_on NULLS LAST, l.lot_code
            """
        ),
        params,
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "item_id": str(r["item_id"]),
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "lot_code": r["lot_code"],
                "lot_status": r["lot_status"],
                "expires_on": r["expires_on"].isoformat() if r["expires_on"] else None,
                "quantity_on_hand": int(r["on_hand"]),
            }
            for r in result.mappings().all()
        ]
    }


@router.get("/billable-items")
async def list_billable_items(principal: Principal, uow: Uow) -> dict:
    granted = await load_granted(principal, uow)
    if perm.FINANCE_INVOICE_VIEW not in granted and perm.INVENTORY_VIEW not in granted:
        require(granted, perm.FINANCE_INVOICE_VIEW)
    if not await _ops_table(uow, "billable_items"):
        raise Conflict("Ops schema unavailable", code="ops_schema_unavailable")
    result = await uow.session.execute(
        text(
            """
            SELECT id, item_code, item_name, unit_code, default_price_irr, is_active
            FROM billable_items
            WHERE tenant_id = :tenant_id
            ORDER BY item_code
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "unit_code": r["unit_code"],
                "default_price_irr": r["default_price_irr"],
                "is_active": r["is_active"],
            }
            for r in result.mappings().all()
        ]
    }
