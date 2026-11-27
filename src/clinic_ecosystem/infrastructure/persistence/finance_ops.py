"""SQL access for disposable ACR-D0.11 finance tables (synthetic ops only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlFinanceOps:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schema_ready(self) -> bool:
        row = await self._session.execute(
            text("SELECT to_regclass('public.invoice_documents') IS NOT NULL AS ok")
        )
        return bool(row.mappings().one()["ok"])

    async def list_invoices(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "limit": limit,
            "offset": offset,
        }
        if patient_id is not None:
            clauses.append("beneficiary_patient_id = :patient_id")
            params["patient_id"] = patient_id
        if status:
            clauses.append("status = :status")
            params["status"] = status
        where = " AND ".join(clauses)
        result = await self._session.execute(
            text(
                f"""
                SELECT id, invoice_number, status, beneficiary_patient_id, department_id,
                       issued_at_utc, posted_at_utc, aggregate_version, created_at_utc
                FROM invoice_documents
                WHERE {where}
                ORDER BY created_at_utc DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r) for r in result.mappings().all()]

    async def invoice_balance(self, *, tenant_id: UUID, invoice_id: UUID) -> dict[str, Any]:
        payable = await self._session.execute(
            text(
                """
                SELECT COALESCE(SUM(patient_payable_amount), 0) AS payable
                FROM invoice_lines
                WHERE tenant_id = :tenant_id AND invoice_id = :invoice_id
                  AND line_status = 'ACTIVE'
                """
            ),
            {"tenant_id": tenant_id, "invoice_id": invoice_id},
        )
        allocated = await self._session.execute(
            text(
                """
                SELECT COALESCE(SUM(
                  CASE WHEN allocation_kind = 'APPLY' THEN amount_irr
                       WHEN allocation_kind = 'REVERSE' THEN -amount_irr
                       ELSE 0 END
                ), 0) AS paid
                FROM receipt_allocations
                WHERE tenant_id = :tenant_id AND invoice_id = :invoice_id
                """
            ),
            {"tenant_id": tenant_id, "invoice_id": invoice_id},
        )
        p = int(payable.mappings().one()["payable"])
        paid = int(allocated.mappings().one()["paid"])
        outstanding = max(0, p - paid)
        if paid <= 0:
            financial_status = "UNPAID"
        elif outstanding == 0:
            financial_status = "PAID"
        else:
            financial_status = "PARTIAL"
        return {
            "patient_payable_total": p,
            "allocated_total": paid,
            "outstanding": outstanding,
            "financial_status": financial_status,
        }

    async def balances_for_appointments(
        self, *, tenant_id: UUID, appointment_ids: list[UUID]
    ) -> dict[UUID, dict[str, Any]]:
        """Aggregate payable/allocated/outstanding per appointment (fail-closed if empty)."""
        if not appointment_ids:
            return {}
        # Map appointment → distinct invoices first, then reuse invoice_balance.
        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT il.appointment_id AS appointment_id, il.invoice_id AS invoice_id
                FROM invoice_lines il
                WHERE il.tenant_id = :tenant_id
                  AND il.appointment_id = ANY(:ids)
                  AND il.appointment_id IS NOT NULL
                """
            ),
            {"tenant_id": tenant_id, "ids": appointment_ids},
        )
        by_appt: dict[UUID, list[UUID]] = {}
        for row in result.mappings().all():
            by_appt.setdefault(row["appointment_id"], []).append(row["invoice_id"])
        out: dict[UUID, dict[str, Any]] = {}
        for appt_id, invoice_ids in by_appt.items():
            payable = paid = 0
            for invoice_id in invoice_ids:
                bal = await self.invoice_balance(tenant_id=tenant_id, invoice_id=invoice_id)
                payable += int(bal["patient_payable_total"])
                paid += int(bal["allocated_total"])
            outstanding = max(0, payable - paid)
            if paid <= 0:
                status = "UNPAID"
            elif outstanding == 0:
                status = "PAID"
            else:
                status = "PARTIAL"
            out[appt_id] = {
                "patient_payable_total": payable,
                "allocated_total": paid,
                "outstanding": outstanding,
                "financial_status": status,
            }
        return out

    async def get_invoice(self, *, tenant_id: UUID, invoice_id: UUID) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, invoice_number, status, beneficiary_patient_id, department_id,
                       reception_group_id, issued_at_utc, posted_at_utc, aggregate_version,
                       created_at_utc, updated_at_utc
                FROM invoice_documents
                WHERE tenant_id = :tenant_id AND id = :invoice_id
                """
            ),
            {"tenant_id": tenant_id, "invoice_id": invoice_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list_lines(self, *, tenant_id: UUID, invoice_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, line_no, line_status, line_kind, description_snapshot, code_snapshot,
                       service_id, billable_item_id, appointment_id, unit_price_irr,
                       gross_service_amount, discount_amount, patient_payable_amount,
                       quantity_scaled, quantity_scale
                FROM invoice_lines
                WHERE tenant_id = :tenant_id AND invoice_id = :invoice_id
                ORDER BY line_no
                """
            ),
            {"tenant_id": tenant_id, "invoice_id": invoice_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def default_department(self, *, tenant_id: UUID) -> UUID | None:
        result = await self._session.execute(
            text(
                """
                SELECT id FROM departments
                WHERE tenant_id = :tenant_id AND is_active = TRUE
                ORDER BY department_code LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().one_or_none()
        return row["id"] if row else None

    async def open_shift(self, *, tenant_id: UUID) -> UUID | None:
        result = await self._session.execute(
            text(
                """
                SELECT id FROM cashier_shifts
                WHERE tenant_id = :tenant_id AND closed_at_utc IS NULL
                ORDER BY opened_at_utc DESC LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().one_or_none()
        return row["id"] if row else None

    async def create_draft_invoice(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        department_id: UUID | None,
        reception_group_id: UUID | None,
        lines: list[dict[str, Any]],
        now: datetime,
    ) -> UUID:
        invoice_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO invoice_documents (
                  id, tenant_id, status, beneficiary_patient_id, department_id,
                  reception_group_id, currency_code, aggregate_version,
                  created_at_utc, updated_at_utc
                ) VALUES (
                  :id, :tenant_id, 'DRAFT', :patient_id, :department_id,
                  :reception_group_id, 'IRR', 1, :now, :now
                )
                """
            ),
            {
                "id": invoice_id,
                "tenant_id": tenant_id,
                "patient_id": patient_id,
                "department_id": department_id,
                "reception_group_id": reception_group_id,
                "now": now,
            },
        )
        for idx, line in enumerate(lines, start=1):
            gross = int(line["unit_price_irr"]) * int(line.get("quantity_scaled", 1))
            discount = int(line.get("discount_amount", 0))
            payable = gross - discount
            await self._session.execute(
                text(
                    """
                    INSERT INTO invoice_lines (
                      id, tenant_id, invoice_id, beneficiary_patient_id, line_no, line_status,
                      department_id, service_id, billable_item_id, appointment_id, line_kind,
                      description_snapshot, code_snapshot, quantity_scaled, quantity_scale,
                      unit_code_snapshot, unit_price_irr, gross_service_amount, discount_amount,
                      patient_payable_amount, pricing_rule_version, payer_policy_version,
                      revenue_policy_version, charge_without_service_reason, created_at_utc
                    ) VALUES (
                      :id, :tenant_id, :invoice_id, :patient_id, :line_no, 'ACTIVE',
                      :department_id, :service_id, :billable_item_id, :appointment_id, :line_kind,
                      :description, :code, :qty, :scale, :unit, :unit_price, :gross, :discount,
                      :payable, 'price-v1', 'payer-v1', 'rev-v1', :charge_reason, :now
                    )
                    """
                ),
                {
                    "id": new_uuid7(),
                    "tenant_id": tenant_id,
                    "invoice_id": invoice_id,
                    "patient_id": patient_id,
                    "line_no": idx,
                    "department_id": department_id,
                    "service_id": line.get("service_id"),
                    "billable_item_id": line.get("billable_item_id"),
                    "appointment_id": line.get("appointment_id"),
                    "line_kind": line["line_kind"],
                    "description": line["description"],
                    "code": line["code"],
                    "qty": int(line.get("quantity_scaled", 1)),
                    "scale": int(line.get("quantity_scale", 0)),
                    "unit": line.get("unit_code", "EA"),
                    "unit_price": int(line["unit_price_irr"]),
                    "gross": gross,
                    "discount": discount,
                    "payable": payable,
                    "charge_reason": line.get("charge_without_service_reason"),
                    "now": now,
                },
            )
        return invoice_id

    async def post_invoice(
        self, *, tenant_id: UUID, invoice_id: UUID, user_id: UUID, now: datetime
    ) -> str:
        number = f"I{str(invoice_id).replace('-', '')[:31]}"
        await self._session.execute(
            text(
                """
                UPDATE invoice_documents SET
                  status = 'POSTED',
                  invoice_number = :number,
                  issued_at_utc = :now,
                  posted_at_utc = :now,
                  posted_by_user_id = :user_id,
                  aggregate_version = aggregate_version + 1,
                  updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :invoice_id AND status = 'DRAFT'
                """
            ),
            {
                "number": number,
                "now": now,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
            },
        )
        return number

    async def record_cash_or_pos_receipt(
        self,
        *,
        tenant_id: UUID,
        patient_id: UUID,
        amount_irr: int,
        payment_method: str,
        department_id: UUID | None,
        shift_id: UUID | None,
        user_id: UUID,
        invoice_id: UUID,
        allocations: list[dict[str, Any]],
        now: datetime,
        receipt_number: str | None = None,
    ) -> UUID:
        receipt_id = new_uuid7()
        number = receipt_number or f"R{str(receipt_id).replace('-', '')[:31]}"
        evidence = f"pos-sim-{receipt_id}" if payment_method == "POS" else None
        terminal = "SETTLED" if payment_method == "POS" else None
        # POS requires an active POS_TERMINAL instrument; CASH uses shift only.
        instrument_id = None
        if payment_method == "POS":
            row = await self._session.execute(
                text(
                    """
                    SELECT id FROM clinic_payment_instruments
                    WHERE tenant_id = :tenant_id AND instrument_kind = 'POS_TERMINAL'
                      AND is_active = TRUE
                    ORDER BY created_at_utc LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            )
            inst = row.mappings().one_or_none()
            instrument_id = inst["id"] if inst else None
        await self._session.execute(
            text(
                """
                INSERT INTO payment_receipts (
                  id, tenant_id, receipt_number, amount_irr, currency_code, payment_method,
                  occurred_at_utc, operator_user_id, actor_type, actor_id, correlation_id,
                  payer_patient_id, credit_beneficiary_patient_id, payer_source,
                  department_id, shift_id, instrument_id, verification_evidence_ref,
                  terminal_state, verified_at_utc, created_at_utc
                ) VALUES (
                  :id, :tenant_id, :number, :amount, 'IRR', :method,
                  :now, :user_id, 'STAFF_USER', :user_id, :corr,
                  :patient_id, :patient_id, 'patient',
                  :department_id, :shift_id, :instrument_id, :evidence,
                  :terminal, :now, :now
                )
                """
            ),
            {
                "id": receipt_id,
                "tenant_id": tenant_id,
                "number": number,
                "amount": amount_irr,
                "method": payment_method,
                "now": now,
                "user_id": user_id,
                "corr": new_uuid7(),
                "patient_id": patient_id,
                "department_id": department_id,
                "shift_id": shift_id,
                "instrument_id": instrument_id,
                "evidence": evidence,
                "terminal": terminal,
            },
        )
        for alloc in allocations:
            await self._session.execute(
                text(
                    """
                    INSERT INTO receipt_allocations (
                      id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
                      amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
                    ) VALUES (
                      :id, :tenant_id, :receipt_id, :invoice_id, :line_id, 'APPLY',
                      :amount, :user_id, :corr, :now, :now
                    )
                    """
                ),
                {
                    "id": new_uuid7(),
                    "tenant_id": tenant_id,
                    "receipt_id": receipt_id,
                    "invoice_id": invoice_id,
                    "line_id": alloc["invoice_line_id"],
                    "amount": int(alloc["amount_irr"]),
                    "user_id": user_id,
                    "corr": new_uuid7(),
                    "now": now,
                },
            )
        return receipt_id

    async def financial_summary(
        self, *, tenant_id: UUID, start_at_utc: datetime, end_at_utc: datetime
    ) -> dict[str, Any]:
        inv = await self._session.execute(
            text(
                """
                SELECT
                  COUNT(*) FILTER (WHERE status = 'POSTED') AS posted_count,
                  COUNT(*) FILTER (WHERE status = 'DRAFT') AS draft_count
                FROM invoice_documents
                WHERE tenant_id = :tenant_id
                  AND created_at_utc >= :start_at AND created_at_utc < :end_at
                """
            ),
            {"tenant_id": tenant_id, "start_at": start_at_utc, "end_at": end_at_utc},
        )
        receipts = await self._session.execute(
            text(
                """
                SELECT COALESCE(SUM(amount_irr), 0) AS receipt_total,
                       COUNT(*) AS receipt_count
                FROM payment_receipts
                WHERE tenant_id = :tenant_id
                  AND occurred_at_utc >= :start_at AND occurred_at_utc < :end_at
                """
            ),
            {"tenant_id": tenant_id, "start_at": start_at_utc, "end_at": end_at_utc},
        )
        refunds = await self._session.execute(
            text(
                """
                SELECT COALESCE(SUM(amount_irr), 0) AS refund_total,
                       COUNT(*) AS refund_count
                FROM clinic_payment_refunds
                WHERE tenant_id = :tenant_id
                  AND occurred_at_utc >= :start_at AND occurred_at_utc < :end_at
                """
            ),
            {"tenant_id": tenant_id, "start_at": start_at_utc, "end_at": end_at_utc},
        )
        i = inv.mappings().one()
        r = receipts.mappings().one()
        rf = refunds.mappings().one()
        return {
            "posted_invoices": int(i["posted_count"]),
            "draft_invoices": int(i["draft_count"]),
            "receipt_count": int(r["receipt_count"]),
            "receipt_total_irr": int(r["receipt_total"]),
            "refund_count": int(rf["refund_count"]),
            "refund_total_irr": int(rf["refund_total"]),
            "net_collected_irr": int(r["receipt_total"]) - int(rf["refund_total"]),
        }
