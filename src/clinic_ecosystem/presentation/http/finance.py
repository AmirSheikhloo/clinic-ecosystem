"""Finance workspace APIs against disposable ACR-D0.11 ledger tables."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field

from clinic_ecosystem.application.shared.errors import (
    Conflict,
    Forbidden,
    NotFound,
    ValidationFailed,
)
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.finance_ops import SqlFinanceOps
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class DraftLineIn(BaseModel):
    line_kind: Literal["SERVICE", "ITEM"]
    description: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=64)
    unit_price_irr: int = Field(ge=0)
    quantity_scaled: int = Field(default=1, ge=1)
    quantity_scale: int = Field(default=0, ge=0, le=6)
    unit_code: str = "EA"
    discount_amount: int = Field(default=0, ge=0)
    service_id: UUID | None = None
    billable_item_id: UUID | None = None
    appointment_id: UUID | None = None
    charge_without_service_reason: str | None = Field(default=None, max_length=200)


class DraftInvoiceIn(BaseModel):
    patient_id: UUID
    department_id: UUID | None = None
    reception_group_id: UUID | None = None
    lines: list[DraftLineIn] = Field(min_length=1, max_length=40)


class PostInvoiceIn(BaseModel):
    expected_version: int = Field(ge=1)


class AllocationIn(BaseModel):
    invoice_line_id: UUID
    amount_irr: int = Field(gt=0)


class ReceiptIn(BaseModel):
    invoice_id: UUID
    amount_irr: int = Field(gt=0)
    payment_method: Literal["CASH", "POS"]
    allocations: list[AllocationIn] = Field(min_length=1, max_length=40)
    idempotency_key: str | None = Field(default=None, max_length=64)


class RefundIn(BaseModel):
    original_receipt_id: UUID
    invoice_id: UUID
    invoice_line_id: UUID
    original_allocation_id: UUID
    amount_irr: int = Field(gt=0)
    refund_method: Literal["CASH", "POS"]
    reason_code: str = Field(min_length=1, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=64)


async def _require_ops(finance: SqlFinanceOps) -> None:
    if not await finance.schema_ready():
        raise Conflict(
            "Ops finance schema is not installed in this database",
            code="ops_schema_unavailable",
        )


@router.get("/invoices")
async def list_invoices(
    principal: Principal,
    uow: Uow,
    patient_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    rows = await finance.list_invoices(
        tenant_id=principal.claims.tenant_id,
        patient_id=patient_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    items = []
    for row in rows:
        bal = await finance.invoice_balance(
            tenant_id=principal.claims.tenant_id, invoice_id=row["id"]
        )
        items.append(
            {
                "id": str(row["id"]),
                "invoice_number": row["invoice_number"],
                "status": row["status"],
                "patient_id": str(row["beneficiary_patient_id"]),
                "department_id": str(row["department_id"]) if row["department_id"] else None,
                "aggregate_version": row["aggregate_version"],
                "issued_at_utc": row["issued_at_utc"].isoformat() if row["issued_at_utc"] else None,
                "posted_at_utc": row["posted_at_utc"].isoformat() if row["posted_at_utc"] else None,
                **bal,
            }
        )
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/invoices/{invoice_id}")
async def get_invoice(principal: Principal, uow: Uow, invoice_id: UUID) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    row = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    if row is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    lines = await finance.list_lines(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    bal = await finance.invoice_balance(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    return {
        "id": str(row["id"]),
        "invoice_number": row["invoice_number"],
        "status": row["status"],
        "patient_id": str(row["beneficiary_patient_id"]),
        "department_id": str(row["department_id"]) if row["department_id"] else None,
        "reception_group_id": str(row["reception_group_id"])
        if row["reception_group_id"]
        else None,
        "aggregate_version": row["aggregate_version"],
        "lines": [
            {
                "id": str(ln["id"]),
                "line_no": ln["line_no"],
                "line_status": ln["line_status"],
                "line_kind": ln["line_kind"],
                "description": ln["description_snapshot"],
                "code": ln["code_snapshot"],
                "unit_price_irr": ln["unit_price_irr"],
                "gross_service_amount": ln["gross_service_amount"],
                "discount_amount": ln["discount_amount"],
                "patient_payable_amount": ln["patient_payable_amount"],
                "service_id": str(ln["service_id"]) if ln["service_id"] else None,
                "appointment_id": str(ln["appointment_id"]) if ln["appointment_id"] else None,
            }
            for ln in lines
        ],
        **bal,
    }


@router.post("/invoices/draft")
async def create_draft(
    principal: Principal,
    uow: Uow,
    body: DraftInvoiceIn,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_DRAFT)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    for line in body.lines:
        if line.line_kind == "SERVICE":
            if line.service_id is None:
                raise ValidationFailed("SERVICE lines require service_id", code="missing_service")
            if (
                line.appointment_id is None
                and not (line.charge_without_service_reason or "").strip()
            ):
                raise ValidationFailed(
                    "SERVICE lines need appointment_id or charge_without_service_reason",
                    code="missing_service_link",
                )
        else:
            if line.billable_item_id is None:
                raise ValidationFailed("ITEM lines require billable_item_id", code="missing_item")
        if line.discount_amount > line.unit_price_irr * line.quantity_scaled:
            raise ValidationFailed("Discount exceeds gross", code="discount_exceeds_gross")
        if line.discount_amount and perm.FINANCE_DISCOUNT not in granted:
            raise Forbidden("Discount not authorized", code="permission_denied")

    now = datetime.now(timezone.utc)
    dept = body.department_id or await finance.default_department(
        tenant_id=principal.claims.tenant_id
    )
    invoice_id = await finance.create_draft_invoice(
        tenant_id=principal.claims.tenant_id,
        patient_id=body.patient_id,
        department_id=dept,
        reception_group_id=body.reception_group_id,
        lines=[ln.model_dump() for ln in body.lines],
        now=now,
    )
    audit = SqlAuditStore(uow.session)
    await audit.append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.invoice_drafted",
        target_type="invoice",
        target_id=invoice_id,
        details={
            "line_count": len(body.lines),
            "patient_id": str(body.patient_id),
            "idempotency_key": idempotency_key,
        },
    )
    await uow.commit()
    return {"id": str(invoice_id), "status": "DRAFT", "aggregate_version": 1}


@router.post("/invoices/{invoice_id}/post")
async def post_invoice(
    principal: Principal, uow: Uow, invoice_id: UUID, body: PostInvoiceIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_POST)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    row = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    if row is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    if row["status"] != "DRAFT":
        raise Conflict("Only DRAFT invoices can be posted", code="invalid_invoice_status")
    if row["aggregate_version"] != body.expected_version:
        raise Conflict("Invoice version mismatch", code="version_conflict")
    now = datetime.now(timezone.utc)
    number = await finance.post_invoice(
        tenant_id=principal.claims.tenant_id,
        invoice_id=invoice_id,
        user_id=principal.account.id,
        now=now,
    )
    audit = SqlAuditStore(uow.session)
    await audit.append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.invoice_posted",
        target_type="invoice",
        target_id=invoice_id,
        details={"invoice_number": number},
    )
    await uow.commit()
    return {"id": str(invoice_id), "status": "POSTED", "invoice_number": number}


@router.post("/receipts")
async def record_receipt(principal: Principal, uow: Uow, body: ReceiptIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_RECEIPT_RECORD)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    inv = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if inv is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    if inv["status"] != "POSTED":
        raise Conflict("Receipts require a POSTED invoice", code="invoice_not_posted")
    alloc_sum = sum(a.amount_irr for a in body.allocations)
    if alloc_sum != body.amount_irr:
        raise ValidationFailed(
            "Allocation sum must equal receipt amount", code="allocation_mismatch"
        )
    bal = await finance.invoice_balance(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if body.amount_irr > bal["outstanding"]:
        raise ValidationFailed(
            "Receipt exceeds outstanding balance", code="receipt_exceeds_outstanding"
        )
    now = datetime.now(timezone.utc)
    shift = await finance.open_shift(tenant_id=principal.claims.tenant_id)
    receipt_id = await finance.record_cash_or_pos_receipt(
        tenant_id=principal.claims.tenant_id,
        patient_id=inv["beneficiary_patient_id"],
        amount_irr=body.amount_irr,
        payment_method=body.payment_method,
        department_id=inv["department_id"],
        shift_id=shift,
        user_id=principal.account.id,
        invoice_id=body.invoice_id,
        allocations=[a.model_dump() for a in body.allocations],
        now=now,
    )
    audit = SqlAuditStore(uow.session)
    await audit.append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.receipt_recorded",
        target_type="payment_receipt",
        target_id=receipt_id,
        details={
            "invoice_id": str(body.invoice_id),
            "amount_irr": body.amount_irr,
            "payment_method": body.payment_method,
            "idempotency_key": body.idempotency_key,
        },
    )
    await uow.commit()
    return {
        "id": str(receipt_id),
        "invoice_id": str(body.invoice_id),
        "amount_irr": body.amount_irr,
        "payment_method": body.payment_method,
    }


@router.post("/refunds")
async def record_refund(principal: Principal, uow: Uow, body: RefundIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_REFUND)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from sqlalchemy import text

    now = datetime.now(timezone.utc)
    refund_id = new_uuid7()
    number = f"RF{str(refund_id).replace('-', '')[:30]}"
    # Domain errors surface as SQLSTATE from ledger guards (exact codes asserted in deep suite).
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO clinic_payment_refunds (
                  id, tenant_id, refund_number, original_receipt_id, invoice_id,
                  invoice_line_id, original_allocation_id, amount_irr, currency_code,
                  refund_method, reason_code, operator_user_id, actor_type, actor_id,
                  correlation_id, occurred_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :number, :receipt_id, :invoice_id, :line_id, :alloc_id,
                  :amount, 'IRR', :method, :reason, :user_id, 'STAFF_USER', :user_id,
                  :corr, :now, :now
                )
                """
            ),
            {
                "id": refund_id,
                "tenant_id": principal.claims.tenant_id,
                "number": number,
                "receipt_id": body.original_receipt_id,
                "invoice_id": body.invoice_id,
                "line_id": body.invoice_line_id,
                "alloc_id": body.original_allocation_id,
                "amount": body.amount_irr,
                "method": body.refund_method,
                "reason": body.reason_code,
                "user_id": principal.account.id,
                "corr": new_uuid7(),
                "now": now,
            },
        )
    except Exception as exc:  # noqa: BLE001 — map DB guard failures
        raise Conflict(
            "Refund rejected by ledger guards",
            code="refund_rejected",
            extra={"detail": str(exc.__class__.__name__)},
        ) from exc
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.refund_recorded",
        target_type="payment_refund",
        target_id=refund_id,
        details={
            "amount_irr": body.amount_irr,
            "original_receipt_id": str(body.original_receipt_id),
            "idempotency_key": body.idempotency_key,
        },
    )
    await uow.commit()
    return {"id": str(refund_id), "refund_number": number, "amount_irr": body.amount_irr}


@router.get("/summary")
async def finance_summary(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
) -> dict[str, Any]:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_SUMMARY)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    if end_at_utc <= start_at_utc or (end_at_utc - start_at_utc).days > 31:
        raise ValidationFailed("Invalid summary range", code="invalid_time_range")
    return await finance.financial_summary(
        tenant_id=principal.claims.tenant_id,
        start_at_utc=start_at_utc.astimezone(timezone.utc),
        end_at_utc=end_at_utc.astimezone(timezone.utc),
    )
