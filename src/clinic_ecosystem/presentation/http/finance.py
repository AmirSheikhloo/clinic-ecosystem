"""Finance workspace APIs against disposable ACR-D0.11 ledger tables."""

from __future__ import annotations

import json
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
from clinic_ecosystem.application.shared.idempotent import run_idempotent, validate_key
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.finance_ops import SqlFinanceOps
from clinic_ecosystem.infrastructure.persistence.services_catalog import (
    SqlServicesCatalogRepository,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.presentation.http.scope_access import (
    filter_rows_by_scope,
    load_scopes,
    require_object_scope,
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
    scopes = await load_scopes(principal, uow, perm.FINANCE_INVOICE_VIEW)
    if not scopes:
        return {"items": [], "limit": limit, "offset": offset, "total": 0}
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    # Fetch a bounded window then apply object-level scopes before pagination slice.
    fetch_limit = min(500, max(limit + offset, limit) * 4)
    rows = await finance.list_invoices(
        tenant_id=principal.claims.tenant_id,
        patient_id=patient_id,
        status=status,
        limit=fetch_limit,
        offset=0,
    )
    scoped = filter_rows_by_scope(
        scopes,
        [dict(r) for r in rows],
        department_key="department_id",
        service_key="service_id",
        provider_key="provider_resource_id",
    )
    total = len(scoped)
    page = scoped[offset : offset + limit]
    items = []
    for row in page:
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
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/invoices/{invoice_id}")
async def get_invoice(principal: Principal, uow: Uow, invoice_id: UUID) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    scopes = await load_scopes(principal, uow, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    row = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    if row is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    require_object_scope(
        scopes,
        department_id=row.get("department_id"),
        service_id=row.get("service_id"),
        provider_resource_id=row.get("provider_resource_id"),
    )
    lines = await finance.list_lines(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    # Every line must independently pass scope (OR across lines is not enough to expose extras).
    for ln in lines:
        require_object_scope(
            scopes,
            department_id=ln.get("department_id") or row.get("department_id"),
            service_id=ln.get("service_id"),
            provider_resource_id=ln.get("provider_resource_id"),
        )
    bal = await finance.invoice_balance(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    from sqlalchemy import text

    alloc_rows = await uow.session.execute(
        text(
            """
            SELECT ra.id, ra.receipt_id, ra.invoice_line_id, ra.allocation_kind,
                   ra.amount_irr, pr.payment_method, pr.receipt_number
            FROM receipt_allocations ra
            JOIN payment_receipts pr
              ON pr.tenant_id = ra.tenant_id AND pr.id = ra.receipt_id
            WHERE ra.tenant_id = :tenant_id AND ra.invoice_id = :invoice_id
            ORDER BY ra.created_at_utc
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "invoice_id": invoice_id},
    )
    allocations = [
        {
            "id": str(a["id"]),
            "receipt_id": str(a["receipt_id"]),
            "invoice_line_id": str(a["invoice_line_id"]),
            "allocation_kind": a["allocation_kind"],
            "amount_irr": int(a["amount_irr"]),
            "payment_method": a["payment_method"],
            "receipt_number": a["receipt_number"],
        }
        for a in alloc_rows.mappings().all()
    ]
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
        "allocations": allocations,
        **bal,
    }


def _gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Compact civil Jalali conversion for receipt labels (presentation only)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + g_d_m[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + (days % 31)
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def _jalali_label_from_utc(dt: datetime | None) -> str:
    from clinic_ecosystem.infrastructure.timezones import require_tehran_zoneinfo

    tehran = require_tehran_zoneinfo()
    local = (dt or datetime.now(timezone.utc)).astimezone(tehran)
    jy, jm, jd = _gregorian_to_jalali(local.year, local.month, local.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


@router.get("/invoices/{invoice_id}/print-snapshot")
async def invoice_print_snapshot(
    principal: Principal, uow: Uow, invoice_id: UUID
) -> dict:
    """Immutable authorized thermal receipt fields from posted invoice snapshots."""
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    scopes = await load_scopes(principal, uow, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    row = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    if row is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    require_object_scope(
        scopes,
        department_id=row.get("department_id"),
        service_id=row.get("service_id"),
        provider_resource_id=row.get("provider_resource_id"),
    )
    if row["status"] not in {"POSTED", "VOIDED"}:
        raise Conflict(
            "Print snapshot requires a posted (or voided historical) invoice",
            code="invoice_not_posted",
        )
    lines = await finance.list_lines(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    for ln in lines:
        require_object_scope(
            scopes,
            department_id=ln.get("department_id") or row.get("department_id"),
            service_id=ln.get("service_id"),
            provider_resource_id=ln.get("provider_resource_id"),
        )
    bal = await finance.invoice_balance(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    from clinic_ecosystem.infrastructure.persistence.patient_display import (
        SqlPatientDisplayDirectory,
    )

    names = await SqlPatientDisplayDirectory(uow.session).display_safe_names(
        tenant_id=principal.claims.tenant_id,
        patient_ids=[row["beneficiary_patient_id"]],
    )
    patient_display = names.get(row["beneficiary_patient_id"]) or "بیمار"
    # Privacy: never include national ID, phone, bank, or clinical notes.
    discount_irr = sum(int(ln["discount_amount"] or 0) for ln in lines)
    paid_irr = int(bal.get("allocated_total") or 0)
    from sqlalchemy import text

    method_row = await uow.session.execute(
        text(
            """
            SELECT pr.payment_method
            FROM receipt_allocations ra
            JOIN payment_receipts pr
              ON pr.tenant_id = ra.tenant_id AND pr.id = ra.receipt_id
            WHERE ra.tenant_id = :tenant_id AND ra.invoice_id = :invoice_id
            ORDER BY ra.created_at_utc
            LIMIT 1
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "invoice_id": invoice_id},
    )
    method = method_row.mappings().one_or_none()
    method_label = None
    if method:
        method_label = "نقدی" if method["payment_method"] == "CASH" else "کارتخوان"

    # Optional course / next-visit hints from disposable course tables when present.
    course_hint = None
    next_hint = None
    course_tbl = await uow.session.execute(
        text("SELECT to_regclass('public.treatment_courses') IS NOT NULL AS ok")
    )
    if course_tbl.mappings().one()["ok"]:
        course = await uow.session.execute(
            text(
                """
                SELECT completed_sessions, planned_sessions, next_suggested_date_tehran
                FROM treatment_courses
                WHERE tenant_id = :tenant_id
                  AND patient_id = :patient_id
                  AND status = 'ACTIVE'
                ORDER BY updated_at_utc DESC
                LIMIT 1
                """
            ),
            {
                "tenant_id": principal.claims.tenant_id,
                "patient_id": row["beneficiary_patient_id"],
            },
        )
        crow = course.mappings().one_or_none()
        if crow:
            course_hint = (
                f"جلسه {int(crow['completed_sessions'])} از {int(crow['planned_sessions'])}"
            )
            if crow["next_suggested_date_tehran"]:
                next_hint = (
                    f"پیشنهاد مراجعه بعدی: {crow['next_suggested_date_tehran']}"
                )

    return {
        "invoice_id": str(row["id"]),
        "invoice_number": row["invoice_number"] or str(row["id"]),
        "jalali_date": _jalali_label_from_utc(row.get("posted_at_utc")),
        "patient_display": patient_display,
        "lines": [
            {
                "description": ln["description_snapshot"],
                "amount_irr": int(ln["patient_payable_amount"]),
                "quantity_scaled": int(ln.get("quantity_scaled") or 1),
            }
            for ln in lines
            if ln.get("line_status", "ACTIVE") == "ACTIVE"
        ],
        "discount_irr": discount_irr,
        "total_payable_irr": int(bal.get("patient_payable_total") or 0),
        "paid_irr": paid_irr,
        "method_label": method_label,
        "financial_status": bal.get("financial_status"),
        "course_session_hint": course_hint,
        "next_suggested_hint": next_hint,
        "synthetic": True,
        "snapshot_immutable": True,
    }


class PrintJobIn(BaseModel):
    invoice_id: UUID
    workstation_id: str = Field(min_length=1, max_length=64)
    width_mm: Literal[58, 80] = 80
    job_kind: Literal["RECEIPT", "TEST", "BATCH_ITEM", "REPRINT"] = "RECEIPT"
    rendered_text: str = Field(min_length=1, max_length=8000)
    snapshot: dict[str, Any]
    status: Literal["QUEUED", "SPOOLED", "FAILED", "UNKNOWN", "CANCELLED"] = "SPOOLED"
    adapter_mode: Literal["simulated", "browser_fallback", "qz_blocked"] = "simulated"
    hardware_claim: Literal["none", "browser_dialog", "blocked_pending_approval"] = "none"
    adapter_detail: str = Field(default="", max_length=400)
    parent_job_id: UUID | None = None
    batch_id: UUID | None = None
    auto_intent_key: str | None = Field(default=None, max_length=200)
    attempt: int = Field(default=1, ge=1, le=20)


@router.post("/print-jobs")
async def record_print_job(principal: Principal, uow: Uow, body: PrintJobIn) -> dict:
    """Persist print-job identity separate from checkout; never mutates finance."""
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from clinic_ecosystem.infrastructure.persistence.print_jobs import SqlPrintJobs

    jobs = SqlPrintJobs(uow.session)
    await jobs.ensure_schema()
    inv = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if inv is None and body.job_kind != "TEST":
        raise NotFound("Invoice not found", code="invoice_not_found")
    # Reject privacy-sensitive keys if a client tries to stash them in snapshot.
    banned = ("national_id", "nationalId", "phone", "iban", "card", "cvv", "کد ملی")
    snap_blob = json.dumps(body.snapshot, ensure_ascii=False)
    if any(b in snap_blob for b in banned):
        raise ValidationFailed(
            "Print snapshot contains disallowed privacy fields",
            code="print_privacy_blocked",
        )
    if body.adapter_mode == "simulated" and body.hardware_claim != "none":
        raise ValidationFailed(
            "Simulated adapter cannot claim hardware success",
            code="false_hardware_claim",
        )
    now = datetime.now(timezone.utc)
    try:
        job_id = await jobs.insert_job(
            tenant_id=principal.claims.tenant_id,
            job_kind=body.job_kind,
            status=body.status,
            invoice_id=None if body.job_kind == "TEST" else body.invoice_id,
            invoice_number=inv["invoice_number"] if inv else "TEST",
            beneficiary_patient_id=inv["beneficiary_patient_id"] if inv else None,
            workstation_id=body.workstation_id,
            width_mm=body.width_mm,
            batch_id=body.batch_id,
            parent_job_id=body.parent_job_id,
            attempt=body.attempt,
            adapter_mode=body.adapter_mode,
            hardware_claim=body.hardware_claim,
            snapshot=body.snapshot,
            rendered_text=body.rendered_text,
            adapter_detail=body.adapter_detail
            or "simulated — no physical hardware claim",
            user_id=principal.account.id,
            now=now,
            auto_intent_key=body.auto_intent_key,
        )
    except ValueError as exc:
        if str(exc) == "auto_print_duplicate":
            raise Conflict(
                "Automatic reprint on refresh blocked; use explicit reprint",
                code="auto_print_duplicate",
            ) from exc
        raise
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.print_job_recorded",
        target_type="thermal_print_job",
        target_id=job_id,
        details={
            "invoice_id": str(body.invoice_id),
            "status": body.status,
            "job_kind": body.job_kind,
            "adapter_mode": body.adapter_mode,
            "hardware_claim": body.hardware_claim,
        },
    )
    return {
        "id": str(job_id),
        "status": body.status,
        "finance_mutated": False,
        "hardware_claim": body.hardware_claim,
    }


@router.get("/invoices/{invoice_id}/print-jobs")
async def list_print_jobs(
    principal: Principal, uow: Uow, invoice_id: UUID
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from clinic_ecosystem.infrastructure.persistence.print_jobs import SqlPrintJobs

    jobs = SqlPrintJobs(uow.session)
    await jobs.ensure_schema()
    rows = await jobs.list_for_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "job_kind": r["job_kind"],
                "status": r["status"],
                "invoice_number": r["invoice_number"],
                "workstation_id": r["workstation_id"],
                "width_mm": r["width_mm"],
                "batch_id": str(r["batch_id"]) if r["batch_id"] else None,
                "parent_job_id": str(r["parent_job_id"]) if r["parent_job_id"] else None,
                "attempt": r["attempt"],
                "adapter_mode": r["adapter_mode"],
                "hardware_claim": r["hardware_claim"],
                "adapter_detail": r["adapter_detail"],
                "created_at_utc": r["created_at_utc"].isoformat(),
            }
            for r in rows
        ]
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
    shift = await finance.open_shift(tenant_id=principal.claims.tenant_id)
    dept = await finance.default_department(tenant_id=principal.claims.tenant_id)
    receipt = await uow.session.execute(
        text(
            """
            SELECT id, payment_method, instrument_id, verification_evidence_ref
            FROM payment_receipts
            WHERE tenant_id = :tenant_id AND id = :receipt_id
            """
        ),
        {
            "tenant_id": principal.claims.tenant_id,
            "receipt_id": body.original_receipt_id,
        },
    )
    receipt_row = receipt.mappings().one_or_none()
    if receipt_row is None:
        raise NotFound("Original receipt not found", code="receipt_not_found")
    instrument_id = None
    evidence = None
    if body.refund_method == "POS":
        instrument_id = receipt_row["instrument_id"]
        if instrument_id is None:
            raise ValidationFailed(
                "POS refund requires original POS instrument",
                code="missing_pos_instrument",
            )
        evidence = f"pos-refund-evidence-{refund_id}"
    # Domain errors surface as SQLSTATE from ledger guards (exact codes asserted in deep suite).
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO clinic_payment_refunds (
                  id, tenant_id, refund_number, original_receipt_id, invoice_id,
                  invoice_line_id, original_allocation_id, amount_irr, currency_code,
                  refund_method, instrument_id, verification_evidence_ref, reason_code,
                  operator_user_id, actor_type, actor_id, department_id, shift_id,
                  correlation_id, occurred_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :number, :receipt_id, :invoice_id, :line_id, :alloc_id,
                  :amount, 'IRR', :method, :instrument, :evidence, :reason,
                  :user_id, 'STAFF_USER', :user_id, :dept, :shift,
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
                "instrument": instrument_id,
                "evidence": evidence,
                "reason": body.reason_code,
                "user_id": principal.account.id,
                "dept": dept,
                "shift": shift,
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


class DiscountIn(BaseModel):
    invoice_id: UUID
    invoice_line_id: UUID | None = None
    discount_scope: Literal["INVOICE", "LINE"]
    calculation_kind: Literal["FIXED_IRR", "PERCENT_BPS"]
    requested_value: int = Field(gt=0)
    reason_code: str = Field(min_length=1, max_length=64)


class AdjustmentIn(BaseModel):
    invoice_id: UUID
    invoice_line_id: UUID
    adjustment_kind: Literal[
        "POST_PAYMENT_DISCOUNT",
        "CORRECTION",
        "WRITE_OFF",
        "CHARGE_CANCELLATION",
        "SUBSIDY_CORRECTION",
        "ROUNDING_CORRECTION",
    ]
    patient_delta_irr: int
    reason_code: str = Field(min_length=1, max_length=64)
    reason_text: str | None = Field(default=None, max_length=500)


class DeskCheckoutLineIn(BaseModel):
    service_id: UUID
    appointment_id: UUID | None = None
    description: str | None = Field(default=None, max_length=200)
    code: str | None = Field(default=None, max_length=64)
    # Client hint only — server catalog price is authoritative.
    unit_price_irr: int | None = Field(default=None, ge=0)
    discount_amount: int = Field(default=0, ge=0)
    discount_percent_bps: int | None = Field(default=None, ge=0, le=10_000)
    # Required when appointment_id is omitted — never auto-fabricated.
    charge_without_service_reason: str | None = Field(default=None, max_length=200)


class DeskCheckoutIn(BaseModel):
    patient_id: UUID
    lines: list[DeskCheckoutLineIn] = Field(min_length=1, max_length=40)
    post: bool = True
    payment_method: Literal["CASH", "POS"] | None = None
    payment_amount_irr: int | None = Field(default=None, ge=0)
    accept_unapplied_credit: bool = False


@router.post("/discounts")
async def apply_discount(principal: Principal, uow: Uow, body: DiscountIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_DISCOUNT)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from sqlalchemy import text

    inv = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if inv is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    if inv["status"] != "DRAFT":
        raise Conflict("Discounts only apply to DRAFT invoices", code="invoice_not_draft")
    if body.discount_scope == "LINE" and body.invoice_line_id is None:
        raise ValidationFailed("LINE discount requires invoice_line_id", code="missing_line")
    if body.discount_scope == "INVOICE" and body.invoice_line_id is not None:
        raise ValidationFailed("INVOICE discount must omit line", code="line_not_allowed")
    if body.calculation_kind == "PERCENT_BPS" and body.requested_value > 10_000:
        raise ValidationFailed("Percent bps exceeds 100%", code="discount_bps_invalid")

    now = datetime.now(timezone.utc)
    lines = await finance.list_lines(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if body.discount_scope == "LINE":
        target = next((ln for ln in lines if ln["id"] == body.invoice_line_id), None)
        if target is None:
            raise NotFound("Invoice line not found", code="line_not_found")
        gross = int(target["gross_service_amount"])
        discount = (
            body.requested_value
            if body.calculation_kind == "FIXED_IRR"
            else (gross * body.requested_value) // 10_000
        )
        discount = min(discount, gross)
        payable = gross - discount
        await uow.session.execute(
            text(
                """
                UPDATE invoice_lines
                SET discount_amount = :discount, patient_payable_amount = :payable
                WHERE tenant_id = :tenant_id AND id = :line_id AND invoice_id = :invoice_id
                """
            ),
            {
                "discount": discount,
                "payable": payable,
                "tenant_id": principal.claims.tenant_id,
                "line_id": body.invoice_line_id,
                "invoice_id": body.invoice_id,
            },
        )
    else:
        active = [ln for ln in lines if ln["line_status"] == "ACTIVE"]
        total_gross = sum(int(ln["gross_service_amount"]) for ln in active)
        if total_gross <= 0:
            raise ValidationFailed("No gross to discount", code="empty_invoice")
        total_discount = (
            body.requested_value
            if body.calculation_kind == "FIXED_IRR"
            else (total_gross * body.requested_value) // 10_000
        )
        total_discount = min(total_discount, total_gross)
        # Exact integer largest-remainder (no floating point).
        shares: list[list[Any]] = []
        allocated = 0
        for ln in active:
            gross = int(ln["gross_service_amount"])
            base = (total_discount * gross) // total_gross
            remainder = (total_discount * gross) % total_gross
            shares.append([ln, base, remainder])
            allocated += base
        rem = total_discount - allocated
        shares.sort(key=lambda s: (s[2], int(s[0]["gross_service_amount"]), str(s[0]["id"])), reverse=True)
        for i in range(rem):
            shares[i % len(shares)][1] += 1
        for ln, disc, _rem in shares:
            payable = int(ln["gross_service_amount"]) - disc
            await uow.session.execute(
                text(
                    """
                    UPDATE invoice_lines
                    SET discount_amount = :discount, patient_payable_amount = :payable
                    WHERE tenant_id = :tenant_id AND id = :line_id
                    """
                ),
                {
                    "discount": disc,
                    "payable": payable,
                    "tenant_id": principal.claims.tenant_id,
                    "line_id": ln["id"],
                },
            )

    await uow.session.execute(
        text(
            """
            INSERT INTO draft_discount_actions (
              id, tenant_id, invoice_id, invoice_line_id, discount_scope,
              calculation_kind, requested_value, reason_code, operator_user_id,
              policy_version, occurred_at_utc, created_at_utc
            ) VALUES (
              :id, :tenant_id, :invoice_id, :line_id, :scope, :kind, :value, :reason,
              :user_id, 'disc-v1', :now, :now
            )
            """
        ),
        {
            "id": new_uuid7(),
            "tenant_id": principal.claims.tenant_id,
            "invoice_id": body.invoice_id,
            "line_id": body.invoice_line_id,
            "scope": body.discount_scope,
            "kind": body.calculation_kind,
            "value": body.requested_value,
            "reason": body.reason_code,
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.discount_applied",
        target_type="invoice",
        target_id=body.invoice_id,
        details={"scope": body.discount_scope, "value": body.requested_value},
    )
    await uow.commit()
    return {"invoice_id": str(body.invoice_id), "status": "DRAFT"}


@router.post("/adjustments")
async def create_adjustment(principal: Principal, uow: Uow, body: AdjustmentIn) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_ADJUSTMENT)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from sqlalchemy import text

    inv = await finance.get_invoice(
        tenant_id=principal.claims.tenant_id, invoice_id=body.invoice_id
    )
    if inv is None:
        raise NotFound("Invoice not found", code="invoice_not_found")
    if inv["status"] != "POSTED":
        raise Conflict("Adjustments require a POSTED invoice", code="invoice_not_posted")
    if body.patient_delta_irr == 0:
        raise ValidationFailed("patient_delta_irr must be non-zero", code="zero_adjustment")
    if body.adjustment_kind in {
        "POST_PAYMENT_DISCOUNT",
        "WRITE_OFF",
        "CHARGE_CANCELLATION",
    } and body.patient_delta_irr > 0:
        raise ValidationFailed(
            "This adjustment kind requires non-positive patient delta",
            code="invalid_adjustment_sign",
        )
    now = datetime.now(timezone.utc)
    adj_id = new_uuid7()
    shift = await finance.open_shift(tenant_id=principal.claims.tenant_id)
    try:
        await uow.session.execute(
            text(
                """
                INSERT INTO financial_adjustments (
                  id, tenant_id, invoice_id, invoice_line_id, adjustment_kind,
                  patient_delta_irr, reason_code, reason_text, operator_user_id,
                  actor_type, actor_id, department_id, shift_id, correlation_id,
                  occurred_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :invoice_id, :line_id, :kind, :delta, :reason, :text,
                  :user_id, 'STAFF_USER', :user_id, :dept, :shift, :corr, :now, :now
                )
                """
            ),
            {
                "id": adj_id,
                "tenant_id": principal.claims.tenant_id,
                "invoice_id": body.invoice_id,
                "line_id": body.invoice_line_id,
                "kind": body.adjustment_kind,
                "delta": body.patient_delta_irr,
                "reason": body.reason_code,
                "text": body.reason_text,
                "user_id": principal.account.id,
                "dept": inv["department_id"],
                "shift": shift,
                "corr": new_uuid7(),
                "now": now,
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise Conflict(
            "Adjustment rejected by ledger guards",
            code="adjustment_rejected",
            extra={"detail": str(exc.__class__.__name__)},
        ) from exc
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="finance.adjustment_recorded",
        target_type="financial_adjustment",
        target_id=adj_id,
        details={
            "kind": body.adjustment_kind,
            "patient_delta_irr": body.patient_delta_irr,
            "invoice_id": str(body.invoice_id),
        },
    )
    await uow.commit()
    return {"id": str(adj_id), "invoice_id": str(body.invoice_id)}


@router.post("/desk-checkout")
async def desk_checkout(
    principal: Principal,
    uow: Uow,
    body: DeskCheckoutIn,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    """Reception one-shot: draft (+ optional discounts) → post → optional CASH/POS pay."""
    key = validate_key(idempotency_key)

    async def _action() -> dict:
        granted = await load_granted(principal, uow)
        require(granted, perm.FINANCE_INVOICE_DRAFT)
        if body.post:
            require(granted, perm.FINANCE_INVOICE_POST)
        if body.payment_method is not None:
            require(granted, perm.FINANCE_RECEIPT_RECORD)
            if body.payment_amount_irr is None or body.payment_amount_irr <= 0:
                raise ValidationFailed(
                    "payment_amount_irr required", code="missing_payment_amount"
                )
        has_fixed = any(int(ln.discount_amount or 0) > 0 for ln in body.lines)
        has_bps = any(ln.discount_percent_bps for ln in body.lines)
        if has_fixed or has_bps:
            require(granted, perm.FINANCE_DISCOUNT)
        if has_fixed and has_bps:
            raise ValidationFailed(
                "Cannot combine FIXED_IRR and PERCENT_BPS discounts on one checkout",
                code="discount_types_combined",
            )

        finance = SqlFinanceOps(uow.session)
        await _require_ops(finance)
        catalog = SqlServicesCatalogRepository(uow.session)
        now = datetime.now(timezone.utc)
        dept = await finance.default_department(tenant_id=principal.claims.tenant_id)
        scopes = await load_scopes(principal, uow, perm.FINANCE_INVOICE_DRAFT)
        draft_lines = []
        for ln in body.lines:
            svc = await catalog.get_by_id(
                tenant_id=principal.claims.tenant_id, service_id=ln.service_id
            )
            if svc is None or not svc.is_active:
                raise NotFound("Service not found", code="service_not_found")
            require_object_scope(
                scopes,
                department_id=dept,
                service_id=ln.service_id,
            )
            server_price = int(svc.default_price_irr)
            if ln.unit_price_irr is not None and ln.unit_price_irr != server_price:
                raise ValidationFailed(
                    "Client price does not match server tariff",
                    code="price_mismatch",
                    extra={
                        "service_id": str(ln.service_id),
                        "server_price_irr": server_price,
                        "client_price_irr": ln.unit_price_irr,
                    },
                )
            if ln.appointment_id is None:
                reason = (ln.charge_without_service_reason or "").strip()
                if not reason:
                    raise ValidationFailed(
                        "SERVICE lines need appointment_id or explicit charge_without_service_reason",
                        code="missing_charge_authority",
                        extra={"service_id": str(ln.service_id)},
                    )
            else:
                reason = None
            discount = int(ln.discount_amount or 0)
            if ln.discount_percent_bps:
                discount = (server_price * int(ln.discount_percent_bps)) // 10_000
            if discount > server_price:
                raise ValidationFailed(
                    "Discount exceeds line gross",
                    code="discount_exceeds_gross",
                    extra={
                        "service_id": str(ln.service_id),
                        "gross_irr": server_price,
                        "discount_irr": discount,
                    },
                )
            draft_lines.append(
                {
                    "line_kind": "SERVICE",
                    "description": svc.service_name[:200],
                    "code": (svc.service_code or str(svc.id)[:8])[:64],
                    "unit_price_irr": server_price,
                    "quantity_scaled": 1,
                    "quantity_scale": 0,
                    "unit_code": "EA",
                    "discount_amount": discount,
                    "service_id": ln.service_id,
                    "appointment_id": ln.appointment_id,
                    "charge_without_service_reason": reason,
                }
            )
        invoice_id = await finance.create_draft_invoice(
            tenant_id=principal.claims.tenant_id,
            patient_id=body.patient_id,
            department_id=dept,
            reception_group_id=None,
            lines=draft_lines,
            now=now,
        )
        invoice_number = None
        receipt_id = None
        received_irr = 0
        applied_irr = 0
        unapplied_credit_irr = 0
        if body.post:
            invoice_number = await finance.post_invoice(
                tenant_id=principal.claims.tenant_id,
                invoice_id=invoice_id,
                user_id=principal.account.id,
                now=now,
            )
            if body.payment_method and body.payment_amount_irr:
                lines = await finance.list_lines(
                    tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
                )
                active = [ln for ln in lines if ln["line_status"] == "ACTIVE"]
                if not active:
                    raise Conflict("Posted invoice has no lines", code="empty_invoice")
                bal = await finance.invoice_balance(
                    tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
                )
                outstanding = int(bal["outstanding"])
                received_irr = int(body.payment_amount_irr)
                if received_irr > outstanding and not body.accept_unapplied_credit:
                    raise ValidationFailed(
                        "Payment exceeds outstanding; set accept_unapplied_credit",
                        code="payment_exceeds_outstanding",
                        extra={
                            "outstanding_irr": outstanding,
                            "payment_amount_irr": received_irr,
                        },
                    )
                applied_irr = min(received_irr, outstanding)
                unapplied_credit_irr = received_irr - applied_irr
                if applied_irr <= 0 and received_irr > 0:
                    raise ValidationFailed("Nothing outstanding to pay", code="nothing_due")
                allocations = []
                remaining = applied_irr
                for ln in active:
                    if remaining <= 0:
                        break
                    slice_amt = min(remaining, int(ln["patient_payable_amount"]))
                    if slice_amt <= 0:
                        continue
                    allocations.append(
                        {"invoice_line_id": ln["id"], "amount_irr": slice_amt}
                    )
                    remaining -= slice_amt
                if applied_irr > 0 and not allocations:
                    raise ValidationFailed("Could not allocate payment", code="alloc_failed")
                shift = await finance.open_shift(tenant_id=principal.claims.tenant_id)
                # Receipt records the full amount received; allocations cover applied only.
                # Unapplied remainder is patient credit (allocations < receipt amount).
                receipt_id = await finance.record_cash_or_pos_receipt(
                    tenant_id=principal.claims.tenant_id,
                    patient_id=body.patient_id,
                    amount_irr=received_irr,
                    payment_method=body.payment_method,
                    department_id=dept,
                    shift_id=shift,
                    user_id=principal.account.id,
                    invoice_id=invoice_id,
                    allocations=allocations,
                    now=now,
                )

        await SqlAuditStore(uow.session).append(
            tenant_id=principal.claims.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=principal.account.id,
            operation="finance.desk_checkout",
            target_type="invoice",
            target_id=invoice_id,
            details={
                "posted": body.post,
                "payment_method": body.payment_method,
                "line_count": len(body.lines),
                "received_irr": received_irr,
                "applied_irr": applied_irr,
                "unapplied_credit_irr": unapplied_credit_irr,
            },
        )
        bal = await finance.invoice_balance(
            tenant_id=principal.claims.tenant_id, invoice_id=invoice_id
        )
        return {
            "id": str(invoice_id),
            "invoice_number": invoice_number,
            "status": "POSTED" if body.post else "DRAFT",
            "receipt_id": str(receipt_id) if receipt_id else None,
            "received_irr": received_irr,
            "applied_irr": applied_irr,
            "unapplied_credit_irr": unapplied_credit_irr,
            "replayed": False,
            **bal,
        }

    result, replayed = await run_idempotent(
        uow,
        tenant_id=principal.claims.tenant_id,
        principal_id=principal.claims.principal_id,
        scope="finance.desk_checkout",
        key=key,
        request_payload=body.model_dump(mode="json"),
        action=_action,
    )
    result = dict(result)
    result["replayed"] = replayed
    return result


@router.get("/patients/{patient_id}/balance")
async def patient_balance(principal: Principal, uow: Uow, patient_id: UUID) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.FINANCE_INVOICE_VIEW)
    finance = SqlFinanceOps(uow.session)
    await _require_ops(finance)
    from sqlalchemy import text

    rows = await finance.list_invoices(
        tenant_id=principal.claims.tenant_id,
        patient_id=patient_id,
        status="POSTED",
        limit=200,
        offset=0,
    )
    outstanding = 0
    paid = 0
    for row in rows:
        bal = await finance.invoice_balance(
            tenant_id=principal.claims.tenant_id, invoice_id=row["id"]
        )
        outstanding += bal["outstanding"]
        paid += bal["allocated_total"]
    # Unapplied patient credit = verified receipts minus net allocations minus refunds.
    credit = await uow.session.execute(
        text(
            """
            SELECT COALESCE(SUM(pr.amount_irr), 0) AS receipt_total,
                   COALESCE((
                     SELECT SUM(
                       CASE WHEN ra.allocation_kind = 'APPLY' THEN ra.amount_irr
                            WHEN ra.allocation_kind = 'REVERSE' THEN -ra.amount_irr
                            ELSE 0 END
                     )
                     FROM receipt_allocations ra
                     JOIN payment_receipts pr2
                       ON pr2.tenant_id = ra.tenant_id AND pr2.id = ra.receipt_id
                     WHERE pr2.tenant_id = :tenant_id
                       AND pr2.credit_beneficiary_patient_id = :patient_id
                   ), 0) AS allocated_total,
                   COALESCE((
                     SELECT SUM(rf.amount_irr)
                     FROM clinic_payment_refunds rf
                     JOIN payment_receipts pr3
                       ON pr3.tenant_id = rf.tenant_id AND pr3.id = rf.original_receipt_id
                     WHERE pr3.tenant_id = :tenant_id
                       AND pr3.credit_beneficiary_patient_id = :patient_id
                   ), 0) AS refunded_total
            FROM payment_receipts pr
            WHERE pr.tenant_id = :tenant_id
              AND pr.credit_beneficiary_patient_id = :patient_id
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "patient_id": patient_id},
    )
    crow = credit.mappings().one()
    patient_credit = max(
        0,
        int(crow["receipt_total"]) - int(crow["allocated_total"]) - int(crow["refunded_total"]),
    )
    return {
        "patient_id": str(patient_id),
        "posted_invoices": len(rows),
        "outstanding_irr": outstanding,
        "allocated_irr": paid,
        "patient_credit_irr": patient_credit,
    }


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
