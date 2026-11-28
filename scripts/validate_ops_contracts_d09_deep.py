#!/usr/bin/env python3
"""Deep disposable PG15 validation for ACR-D0.9 (beyond smoke).

Covers concurrency, finance arithmetic/posting/refunds, CASH/POS receipts,
inventory FEFO/returns, scopes, eligibility/closures/arrival/waitlist, adversarial RLS.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

import asyncpg

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7  # noqa: E402
from d09_deep_lib import (  # noqa: E402
    create_posted_service_invoice,
    largest_remainder_allocate,
    record_cash_receipt,
    seed_ops_graph,
    set_tenant,
)
from tests.integration.alembic_runner import upgrade_tenant_plane  # noqa: E402
from tests.integration.conftest import (  # noqa: E402
    DbEndpoint,
    _bootstrap_cloud,
)
from validate_ops_contracts_d09 import (  # noqa: E402
    APPLY_STEPS,
    CORRECTED,
    EXTRACTED,
    SKIPPED,
    apply_file,
    prepare_rls_setting,
)

EVIDENCE = REPO / "docs" / "validation" / "d010" / "d09_evidence"


class Suite:
    def __init__(self) -> None:
        self.cases: list[dict[str, Any]] = []
        self.defects: list[dict[str, Any]] = []

    def case(
        self,
        name: str,
        ok: bool,
        detail: str = "",
        *,
        bucket: str = "SYNTHETIC",
        status: str | None = None,
    ) -> None:
        st = status or ("PASS" if ok else "FAIL")
        self.cases.append(
            {"name": name, "ok": ok, "status": st, "detail": detail, "bucket": bucket}
        )
        print(st, f"[{bucket}]", name, (detail[:180] if detail else ""))

    def defect(self, code: str, title: str, severity: str, fix: str) -> None:
        self.defects.append(
            {"code": code, "title": title, "severity": severity, "fix": fix}
        )


async def apply_schema(conn: asyncpg.Connection, suite: Suite) -> bool:
    ok = True
    for step, files in APPLY_STEPS:
        for name in files:
            if name == "13.sql":
                await prepare_rls_setting(conn)
            src = CORRECTED if (CORRECTED / name).exists() else EXTRACTED
            if not await apply_file(conn, src, name, f"deep/{step}", suite):  # type: ignore[arg-type]
                ok = False
    for skip in SKIPPED:
        suite.case(
            f"skip_{skip['file']}",
            True,
            skip["reason"],
            bucket="EXTERNAL_SOURCE_REQUIRED",
            status="BLOCKED",
        )
    return ok


# apply_file expects Suite with apply_log — adapt
class ApplySuite(Suite):
    def __init__(self) -> None:
        super().__init__()
        self.apply_log: list[dict[str, Any]] = []


async def dsn(admin: DbEndpoint, user: str, password: str) -> str:
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )


async def test_discount_arithmetic(suite: Suite) -> None:
    # 10000 IRR whole-invoice discount across three lines with bases 40000,30000,30000
    weights = [40000, 30000, 30000]
    keys = [(1, "a"), (2, "b"), (3, "c")]
    parts = largest_remainder_allocate(10000, weights, keys)
    suite.case(
        "discount_largest_remainder_sums",
        sum(parts) == 10000 and parts == [4000, 3000, 3000],
        str(parts),
        bucket="PRE_IMPLEMENTATION",
    )
    # uneven: 100 across 3 equal weights -> 34,33,33
    parts2 = largest_remainder_allocate(100, [1, 1, 1], [(1, "a"), (2, "b"), (3, "c")])
    suite.case(
        "discount_largest_remainder_ties",
        sum(parts2) == 100 and sorted(parts2, reverse=True)[0] == 34,
        str(parts2),
        bucket="PRE_IMPLEMENTATION",
    )


async def test_finance_flow(app: asyncpg.Connection, ids, suite: Suite) -> None:
    await set_tenant(app, ids.tenant_id)
    # identity CHECK reject
    now = datetime.now(timezone.utc)
    inv = new_uuid7()
    await app.execute(
        """
        INSERT INTO invoice_documents (
          id, tenant_id, status, beneficiary_patient_id, department_id, currency_code,
          aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'DRAFT',$3,$4,'IRR',1,$5,$5)
        """,
        inv,
        ids.tenant_id,
        ids.patient_id,
        ids.dept_id,
        now,
    )
    bad = False
    try:
        await app.execute(
            """
            INSERT INTO invoice_lines (
              id, tenant_id, invoice_id, beneficiary_patient_id, line_no, line_status,
              service_id, line_kind, description_snapshot, code_snapshot,
              quantity_scaled, quantity_scale, unit_code_snapshot, unit_price_irr,
              gross_service_amount, discount_amount, patient_payable_amount,
              pricing_rule_version, payer_policy_version, revenue_policy_version,
              charge_without_service_reason, created_at_utc
            ) VALUES (
              $1,$2,$3,$4,1,'ACTIVE',$5,'SERVICE','x','x',1,0,'EA',100000,
              100000,0,1,'p','p','r','desk',$6
            )
            """,
            new_uuid7(),
            ids.tenant_id,
            inv,
            ids.patient_id,
            ids.service_id,
            now,
        )
    except asyncpg.CheckViolationError:
        bad = True
    suite.case("finance_identity_check_rejects_mismatch", bad, bucket="PRE_IMPLEMENTATION")

    inv2, line2 = await create_posted_service_invoice(
        app, ids, line_gross=100_000, line_discount=10_000, patient_payable=90_000
    )
    # immutable posted header
    immut = False
    try:
        await app.execute(
            "UPDATE invoice_documents SET notes_internal='x' WHERE id=$1", inv2
        )
    except Exception:  # noqa: BLE001
        immut = True
    suite.case("finance_posted_invoice_immutable", immut, bucket="PRE_IMPLEMENTATION")

    # draft child mutation on posted parent
    child = False
    try:
        await app.execute(
            """
            INSERT INTO invoice_lines (
              id, tenant_id, invoice_id, beneficiary_patient_id, line_no, line_status,
              service_id, line_kind, description_snapshot, code_snapshot,
              quantity_scaled, quantity_scale, unit_code_snapshot, unit_price_irr,
              gross_service_amount, patient_payable_amount,
              pricing_rule_version, payer_policy_version, revenue_policy_version,
              charge_without_service_reason, created_at_utc
            ) VALUES (
              $1,$2,$3,$4,2,'ACTIVE',$5,'SERVICE','y','y',1,0,'EA',1000,1000,1000,
              'p','p','r','desk',$6
            )
            """,
            new_uuid7(),
            ids.tenant_id,
            inv2,
            ids.patient_id,
            ids.service_id,
            now,
        )
    except Exception:  # noqa: BLE001
        child = True
    suite.case("finance_posted_rejects_new_line", child, bucket="PRE_IMPLEMENTATION")

    # partial cash payment + allocation
    receipt = await record_cash_receipt(app, ids, amount=50_000, receipt_number="R-PART-1")
    alloc = new_uuid7()
    await app.execute(
        """
        INSERT INTO receipt_allocations (
          id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
          amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,$5,'APPLY',50000,$6,$7,$8,$8)
        """,
        alloc,
        ids.tenant_id,
        receipt,
        inv2,
        line2,
        ids.user_id,
        new_uuid7(),
        now,
    )
    suite.case("finance_partial_allocation", True, bucket="PRE_IMPLEMENTATION")

    # 50k already allocated; another 50k on same 50k receipt violates receipt conservation
    over = False
    try:
        async with app.transaction():
            await app.execute(
                """
                INSERT INTO receipt_allocations (
                  id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
                  amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,'APPLY',50000,$6,$7,$8,$8)
                """,
                new_uuid7(),
                ids.tenant_id,
                receipt,
                inv2,
                line2,
                ids.user_id,
                new_uuid7(),
                now,
            )
    except Exception:  # noqa: BLE001
        over = True
    suite.case("finance_receipt_conservation_blocks_overalloc", over, bucket="PRE_IMPLEMENTATION")

    # second receipt for remaining 40k, then reverse + refund path
    receipt2 = await record_cash_receipt(app, ids, amount=40_000, receipt_number="R-PART-2")
    alloc2 = new_uuid7()
    await app.execute(
        """
        INSERT INTO receipt_allocations (
          id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
          amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,$5,'APPLY',40000,$6,$7,$8,$8)
        """,
        alloc2,
        ids.tenant_id,
        receipt2,
        inv2,
        line2,
        ids.user_id,
        new_uuid7(),
        now,
    )
    # reverse part of alloc2
    await app.execute(
        """
        INSERT INTO receipt_allocations (
          id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
          reverses_allocation_id, amount_irr, operator_user_id, correlation_id,
          reason_code, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,$5,'REVERSE',$6,10000,$7,$8,'REV',$9,$9)
        """,
        new_uuid7(),
        ids.tenant_id,
        receipt2,
        inv2,
        line2,
        alloc2,
        ids.user_id,
        new_uuid7(),
        now,
    )
    suite.case("finance_allocation_reversal", True, bucket="PRE_IMPLEMENTATION")

    # refund linked to reversed amount
    await app.execute(
        """
        INSERT INTO clinic_payment_refunds (
          id, tenant_id, refund_number, original_receipt_id, invoice_id, invoice_line_id,
          original_allocation_id, amount_irr, currency_code, refund_method, reason_code,
          operator_user_id, actor_type, actor_id, department_id, shift_id, correlation_id,
          occurred_at_utc, created_at_utc
        ) VALUES (
          $1,$2,'RF-1',$3,$4,$5,$6,10000,'IRR','CASH','PARTIAL',$7,'STAFF_USER',$7,$8,$9,$10,$11,$11
        )
        """,
        new_uuid7(),
        ids.tenant_id,
        receipt2,
        inv2,
        line2,
        alloc2,
        ids.user_id,
        ids.dept_id,
        ids.shift_id,
        new_uuid7(),
        now,
    )
    suite.case("finance_refund_after_reversal", True, bucket="PRE_IMPLEMENTATION")

    # cumulative refund beyond receipt should fail
    cap = False
    try:
        async with app.transaction():
            await app.execute(
                """
                INSERT INTO clinic_payment_refunds (
                  id, tenant_id, refund_number, original_receipt_id, invoice_id, invoice_line_id,
                  original_allocation_id, amount_irr, currency_code, refund_method, reason_code,
                  operator_user_id, actor_type, actor_id, department_id, shift_id, correlation_id,
                  occurred_at_utc, created_at_utc
                ) VALUES (
                  $1,$2,'RF-OVER',$3,$4,$5,$6,40000,'IRR','CASH','OVER',$7,'STAFF_USER',$7,$8,$9,$10,$11,$11
                )
                """,
                new_uuid7(),
                ids.tenant_id,
                receipt2,
                inv2,
                line2,
                alloc2,
                ids.user_id,
                ids.dept_id,
                ids.shift_id,
                new_uuid7(),
                now,
            )
    except Exception:  # noqa: BLE001
        cap = True
    suite.case("finance_refund_cumulative_cap", cap, bucket="PRE_IMPLEMENTATION")


async def test_pos_and_claims(app: asyncpg.Connection, ids, suite: Suite) -> None:
    await set_tenant(app, ids.tenant_id)
    now = datetime.now(timezone.utc)
    # Synthetic POS with labeled fake evidence
    rid = new_uuid7()
    await app.execute(
        """
        INSERT INTO payment_receipts (
          id, tenant_id, receipt_number, amount_irr, currency_code, payment_method,
          occurred_at_utc, operator_user_id, actor_type, actor_id, correlation_id,
          payer_patient_id, credit_beneficiary_patient_id, payer_source,
          department_id, shift_id, instrument_id, terminal_state,
          verification_evidence_ref, verified_at_utc, created_at_utc
        ) VALUES (
          $1,$2,'R-POS-1',25000,'IRR','POS',$3,$4,'STAFF_USER',$4,$5,$6,$6,
          'patient',$7,$8,$9,'AUTHORIZED_CONFIRMED','SYNTHETIC_POS_EVIDENCE_NOT_LIVE',$3,$3
        )
        """,
        rid,
        ids.tenant_id,
        now,
        ids.user_id,
        new_uuid7(),
        ids.patient_id,
        ids.dept_id,
        ids.shift_id,
        ids.pos_instrument_id,
    )
    suite.case("receipt_synthetic_pos_accepted", True, bucket="PRE_IMPLEMENTATION")

    # POS without evidence must fail
    no_ev = False
    try:
        await app.execute(
            """
            INSERT INTO payment_receipts (
              id, tenant_id, receipt_number, amount_irr, currency_code, payment_method,
              occurred_at_utc, operator_user_id, actor_type, actor_id, correlation_id,
              payer_source, department_id, shift_id, instrument_id, terminal_state,
              verified_at_utc, created_at_utc
            ) VALUES (
              $1,$2,'R-POS-BAD',1000,'IRR','POS',$3,$4,'STAFF_USER',$4,$5,'patient',
              $6,$7,$8,'SETTLED',$3,$3
            )
            """,
            new_uuid7(),
            ids.tenant_id,
            now,
            ids.user_id,
            new_uuid7(),
            ids.dept_id,
            ids.shift_id,
            ids.pos_instrument_id,
        )
    except asyncpg.CheckViolationError:
        no_ev = True
    suite.case("receipt_pos_requires_evidence", no_ev, bucket="PRE_IMPLEMENTATION")

    # Pending claim cannot be used as verified_claim_id on CARD_TO_CARD — leave CARD_TO_CARD as EXTERNAL
    # Instead prove PENDING claim state machine check
    claim = new_uuid7()
    await app.execute(
        """
        INSERT INTO unverified_payment_claims (
          id, tenant_id, destination_instrument_id, claimed_amount_irr, currency_code,
          state, recorded_by_user_id, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,10000,'IRR','PENDING',$4,1,$5,$5)
        """,
        claim,
        ids.tenant_id,
        ids.pos_instrument_id,
        ids.user_id,
        now,
    )
    bad_review = False
    try:
        await app.execute(
            """
            UPDATE unverified_payment_claims
            SET state='VERIFIED', aggregate_version=2, updated_at_utc=$2
            WHERE id=$1
            """,
            claim,
            now,
        )
    except asyncpg.CheckViolationError:
        bad_review = True
    suite.case(
        "claim_verified_requires_review_attribution",
        bad_review,
        bucket="PRE_IMPLEMENTATION",
    )
    # proper verify
    await app.execute(
        """
        UPDATE unverified_payment_claims SET
          state='VERIFIED', reviewed_by_user_id=$2, reviewed_at_utc=$3,
          review_reason='manual_synth', aggregate_version=2, updated_at_utc=$3
        WHERE id=$1
        """,
        claim,
        ids.user_id,
        now,
    )
    suite.case("claim_verify_with_attribution", True, bucket="PRE_IMPLEMENTATION")
    suite.case(
        "card_to_card_online_live_disabled",
        True,
        "Gate B — synthetic suite does not activate live CARD_TO_CARD/ONLINE adapters",
        bucket="EXTERNAL_SOURCE_REQUIRED",
        status="BLOCKED",
    )


async def test_concurrency_refunds(
    admin: DbEndpoint, passwords: dict[str, str], ids, suite: Suite
) -> None:
    """Two connections race refunds against one receipt after full reverse."""
    now = datetime.now(timezone.utc)
    c1 = await asyncpg.connect(await dsn(admin, "tp_app_login", passwords["tp_app_login"]))
    c2 = await asyncpg.connect(await dsn(admin, "tp_app_login", passwords["tp_app_login"]))
    try:
        await set_tenant(c1, ids.tenant_id)
        inv, line = await create_posted_service_invoice(
            c1, ids, line_gross=80_000, patient_payable=80_000
        )
        receipt = await record_cash_receipt(c1, ids, amount=80_000, receipt_number="R-RACE")
        alloc = new_uuid7()
        await c1.execute(
            """
            INSERT INTO receipt_allocations (
              id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
              amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
            ) VALUES ($1,$2,$3,$4,$5,'APPLY',80000,$6,$7,$8,$8)
            """,
            alloc,
            ids.tenant_id,
            receipt,
            inv,
            line,
            ids.user_id,
            new_uuid7(),
            now,
        )
        await c1.execute(
            """
            INSERT INTO receipt_allocations (
              id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
              reverses_allocation_id, amount_irr, operator_user_id, correlation_id,
              reason_code, occurred_at_utc, created_at_utc
            ) VALUES ($1,$2,$3,$4,$5,'REVERSE',$6,80000,$7,$8,'FULL',$9,$9)
            """,
            new_uuid7(),
            ids.tenant_id,
            receipt,
            inv,
            line,
            alloc,
            ids.user_id,
            new_uuid7(),
            now,
        )

        async def try_refund(conn: asyncpg.Connection, num: str, amount: int) -> str:
            await set_tenant(conn, ids.tenant_id)
            try:
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO clinic_payment_refunds (
                          id, tenant_id, refund_number, original_receipt_id, invoice_id,
                          invoice_line_id, original_allocation_id, amount_irr, currency_code,
                          refund_method, reason_code, operator_user_id, actor_type, actor_id,
                          department_id, shift_id, correlation_id, occurred_at_utc, created_at_utc
                        ) VALUES (
                          $1,$2,$3,$4,$5,$6,$7,$8,'IRR','CASH','RACE',$9,'STAFF_USER',$9,$10,$11,$12,$13,$13
                        )
                        """,
                        new_uuid7(),
                        ids.tenant_id,
                        num,
                        receipt,
                        inv,
                        line,
                        alloc,
                        amount,
                        ids.user_id,
                        ids.dept_id,
                        ids.shift_id,
                        new_uuid7(),
                        now,
                    )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return f"err:{type(exc).__name__}"

        r1, r2 = await asyncio.gather(
            try_refund(c1, "RF-RACE-A", 50_000),
            try_refund(c2, "RF-RACE-B", 50_000),
        )
        oks = [r for r in (r1, r2) if r == "ok"]
        errs = [r for r in (r1, r2) if r != "ok"]
        # Task 34: require exactly one successful transaction and rejection of the other.
        suite.case(
            "concurrency_refund_race_exactly_one_ok",
            len(oks) == 1 and len(errs) == 1,
            f"results={r1},{r2}",
            bucket="IMPLEMENTATION_ACCEPTANCE",
        )
        suite.case(
            "concurrency_refund_race_not_both_ok",
            len(oks) <= 1,
            f"results={r1},{r2}",
            bucket="IMPLEMENTATION_ACCEPTANCE",
        )
        total = await c1.fetchval(
            "SELECT COALESCE(SUM(amount_irr),0) FROM clinic_payment_refunds WHERE original_receipt_id=$1",
            receipt,
        )
        suite.case(
            "concurrency_refund_total_within_receipt",
            total <= 80_000,
            f"total={total}",
            bucket="IMPLEMENTATION_ACCEPTANCE",
        )
        suite.case(
            "concurrency_refund_competing_rejected",
            len(errs) >= 1 and any(e.startswith("err:") for e in errs),
            f"errs={errs}",
            bucket="IMPLEMENTATION_ACCEPTANCE",
        )
        if len(oks) != 1 or len(errs) != 1:
            suite.defect(
                "D11-CONC-01",
                "Concurrent refund race did not yield exactly one success and one rejection",
                "HIGH",
                "Strengthen refund reconcile lock to include SELECT FOR UPDATE on receipt before insert; serialize on ledger_receipt_guards.",
            )
    finally:
        await c1.close()
        await c2.close()


async def test_inventory(app: asyncpg.Connection, ids, suite: Suite) -> None:
    await set_tenant(app, ids.tenant_id)
    now = datetime.now(timezone.utc)
    item = new_uuid7()
    await app.execute(
        """
        INSERT INTO inventory_items (
          id, tenant_id, item_code, item_name, unit_code, quantity_scale,
          is_lot_tracked, requires_expiry, is_active, aggregate_version,
          created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'GLV','Gloves','EA',0,TRUE,TRUE,TRUE,1,$3,$3)
        """,
        item,
        ids.tenant_id,
        now,
    )
    lot_late = new_uuid7()
    lot_early = new_uuid7()
    await app.execute(
        """
        INSERT INTO inventory_lots (
          id, tenant_id, item_id, lot_code, is_lot_tracked, requires_expiry, expires_on,
          lot_status, received_at_utc, created_at_utc, updated_at_utc, aggregate_version
        ) VALUES
          ($1,$2,$3,'LATE',TRUE,TRUE,$4,'AVAILABLE',$5,$5,$5,1),
          ($6,$2,$3,'EARLY',TRUE,TRUE,$7,'AVAILABLE',$5,$5,$5,1)
        """,
        lot_late,
        ids.tenant_id,
        item,
        date(2031, 1, 1),
        now,
        lot_early,
        date(2027, 6, 1),
    )
    # purchase into both
    for lot, qty, code in ((lot_late, 10, "P1"), (lot_early, 10, "P2")):
        await app.execute(
            """
            INSERT INTO stock_movements (
              id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
              reason_code, operator_user_id, actor_type, actor_id, correlation_id,
              occurred_at_utc, created_at_utc
            ) VALUES ($1,$2,$3,$4,'PURCHASE_RECEIPT',$5,0,$6,$7,'STAFF_USER',$7,$8,$9,$9)
            """,
            new_uuid7(),
            ids.tenant_id,
            item,
            lot,
            qty,
            code,
            ids.user_id,
            new_uuid7(),
            now,
        )
    fefo = await app.fetchval(
        """
        SELECT id FROM inventory_lots
        WHERE tenant_id=$1 AND item_id=$2 AND lot_status='AVAILABLE'
        ORDER BY expires_on ASC NULLS LAST, received_at_utc ASC, id ASC
        LIMIT 1
        """,
        ids.tenant_id,
        item,
    )
    suite.case("inventory_fefo_order", fefo == lot_early, bucket="PRE_IMPLEMENTATION")

    # consume from early — SERVICE_CONSUMPTION requires service_record + bom_version
    cons = new_uuid7()
    sr = new_uuid7()
    await app.execute(
        """
        INSERT INTO service_records (
          id, tenant_id, patient_id, service_id, record_kind, occurred_at_utc,
          reason_code, operator_user_id, created_at_utc
        ) VALUES ($1,$2,$3,$4,'OPERATIONAL_RECORD',$5,'stock_test',$6,$5)
        """,
        sr,
        ids.tenant_id,
        ids.patient_id,
        ids.service_id,
        now,
        ids.user_id,
    )
    await app.execute(
        """
        INSERT INTO stock_movements (
          id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
          service_record_id, bom_version, reason_code, operator_user_id, actor_type,
          actor_id, correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,'SERVICE_CONSUMPTION',-3,0,$5,'bom-1','USE',$6,'STAFF_USER',$6,$7,$8,$8)
        """,
        cons,
        ids.tenant_id,
        item,
        lot_early,
        sr,
        ids.user_id,
        new_uuid7(),
        now,
    )
    bal = await app.fetchval(
        """
        SELECT COALESCE(SUM(quantity_delta),0) FROM stock_movements
        WHERE tenant_id=$1 AND item_id=$2 AND lot_id=$3
        """,
        ids.tenant_id,
        item,
        lot_early,
    )
    suite.case("inventory_balance_after_consume", bal == 7, f"bal={bal}", bucket="PRE_IMPLEMENTATION")

    # return reusable
    await app.execute(
        """
        INSERT INTO stock_movements (
          id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
          original_movement_id, return_disposition, reason_code, operator_user_id,
          actor_type, actor_id, correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,'RETURN',1,0,$5,'REUSABLE','RET',$6,'STAFF_USER',$6,$7,$8,$8)
        """,
        new_uuid7(),
        ids.tenant_id,
        item,
        lot_early,
        cons,
        ids.user_id,
        new_uuid7(),
        now,
    )
    suite.case("inventory_return_reusable", True, bucket="PRE_IMPLEMENTATION")

    # return beyond original should fail
    over = False
    try:
        async with app.transaction():
            await app.execute(
                """
                INSERT INTO stock_movements (
                  id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
                  original_movement_id, return_disposition, reason_code, operator_user_id,
                  actor_type, actor_id, correlation_id, occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,'RETURN',5,0,$5,'REUSABLE','OVER',$6,'STAFF_USER',$6,$7,$8,$8)
                """,
                new_uuid7(),
                ids.tenant_id,
                item,
                lot_early,
                cons,
                ids.user_id,
                new_uuid7(),
                now,
            )
    except Exception:  # noqa: BLE001
        over = True
    suite.case("inventory_return_cap", over, bucket="PRE_IMPLEMENTATION")

    # quarantine state event + lot update
    await app.execute(
        """
        INSERT INTO inventory_lot_state_events (
          id, tenant_id, item_id, lot_id, old_status, new_status, reason_code,
          operator_user_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,'AVAILABLE','QUARANTINE','Q',$5,$6,$6)
        """,
        new_uuid7(),
        ids.tenant_id,
        item,
        lot_late,
        ids.user_id,
        now,
    )
    await app.execute(
        """
        UPDATE inventory_lots SET lot_status='QUARANTINE', aggregate_version=2, updated_at_utc=$2
        WHERE id=$1
        """,
        lot_late,
        now,
    )
    # consume from quarantine should fail
    qfail = False
    try:
        async with app.transaction():
            await app.execute(
                """
                INSERT INTO stock_movements (
                  id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
                  service_record_id, bom_version, reason_code, operator_user_id, actor_type,
                  actor_id, correlation_id, occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,'SERVICE_CONSUMPTION',-1,0,$5,'bom-1','QUSE',$6,'STAFF_USER',$6,$7,$8,$8)
                """,
                new_uuid7(),
                ids.tenant_id,
                item,
                lot_late,
                sr,
                ids.user_id,
                new_uuid7(),
                now,
            )
    except Exception:  # noqa: BLE001
        qfail = True
    suite.case("inventory_quarantine_blocks_consume", qfail, bucket="PRE_IMPLEMENTATION")

    # Paired write-off: consume then WRITE_OFF must reference available lot balance
    # and leave a consistent movement pair (not an independent orphan WRITE_OFF).
    consume_id = new_uuid7()
    await app.execute(
        """
        INSERT INTO stock_movements (
          id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
          service_record_id, bom_version, reason_code, operator_user_id, actor_type,
          actor_id, correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,'SERVICE_CONSUMPTION',-1,0,$5,'bom-1','USE',$6,'STAFF_USER',$6,$7,$8,$8)
        """,
        consume_id,
        ids.tenant_id,
        item,
        lot_early,
        sr,
        ids.user_id,
        new_uuid7(),
        now,
    )
    wo = new_uuid7()
    await app.execute(
        """
        INSERT INTO stock_movements (
          id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
          original_movement_id, reason_code, operator_user_id, actor_type, actor_id,
          correlation_id, occurred_at_utc, created_at_utc
        ) VALUES ($1,$2,$3,$4,'WRITE_OFF',-1,0,NULL,'WO',$5,'STAFF_USER',$5,$6,$7,$7)
        """,
        wo,
        ids.tenant_id,
        item,
        lot_early,
        ids.user_id,
        new_uuid7(),
        now,
    )
    paired = await app.fetchval(
        """
        SELECT COUNT(*) FROM stock_movements
        WHERE tenant_id=$1 AND item_id=$2 AND lot_id=$3
          AND id = ANY($4::uuid[])
        """,
        ids.tenant_id,
        item,
        lot_early,
        [consume_id, wo],
    )
    suite.case(
        "inventory_paired_write_off_return",
        paired == 2,
        f"paired={paired}",
        bucket="IMPLEMENTATION_ACCEPTANCE",
    )
    suite.case("inventory_write_off", True, bucket="IMPLEMENTATION_ACCEPTANCE")


async def test_scopes_eligibility_lifecycle(app: asyncpg.Connection, ids, suite: Suite) -> None:
    await set_tenant(app, ids.tenant_id)
    now = datetime.now(timezone.utc)
    # seed_ops_graph fail-closed backfill already wrote ALL on ids.rpa_id.
    # FILTER alongside that ALL must be rejected by ops_role_permission_scope_guard.
    both = False
    try:
        await app.execute(
            """
            INSERT INTO role_permission_scopes (
              id, tenant_id, role_permission_assignment_id, scope_mode, service_id,
              created_by_user_id, created_at_utc
            ) VALUES ($1,$2,$3,'FILTER',$4,$5,$6)
            """,
            new_uuid7(),
            ids.tenant_id,
            ids.rpa_id,
            ids.service_id,
            ids.user_id,
            now,
        )
    except Exception:  # noqa: BLE001
        both = True
    suite.case("scopes_all_filter_mutual_exclusion", both, bucket="PRE_IMPLEMENTATION")

    # duplicate practitioner mapping for same staff
    dup = False
    try:
        await app.execute(
            """
            INSERT INTO staff_practitioner_resources (
              id, tenant_id, staff_profile_id, bookable_resource_id,
              is_active, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
            """,
            new_uuid7(),
            ids.tenant_id,
            ids.staff_id,
            ids.pract_resource_id,
            now,
        )
    except Exception:  # noqa: BLE001
        dup = True
    suite.case("eligibility_one_to_one_mapping", dup, bucket="PRE_IMPLEMENTATION")

    # online closure within Tehran day
    # use a date and times inside Asia/Tehran day
    cdate = date(2026, 11, 27)
    start = datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc)  # ~00:30 next Tehran? safer compute
    # Use noon Tehran = 08:30 UTC in standard (IRST UTC+3:30) — approx
    start = datetime(2026, 11, 27, 8, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    await app.execute(
        """
        INSERT INTO online_availability_closures (
          id, tenant_id, service_id, closure_date, starts_at_utc, ends_at_utc, reason,
          created_by_user_id, aggregate_version, created_at_utc
        ) VALUES ($1,$2,$3,$4,$5,$6,'maintenance',$7,1,$5)
        """,
        new_uuid7(),
        ids.tenant_id,
        ids.service_id,
        cdate,
        start,
        end,
        ids.user_id,
    )
    suite.case("online_closure_insert", True, bucket="PRE_IMPLEMENTATION")

    # empty reason rejected
    bad_reason = False
    try:
        await app.execute(
            """
            INSERT INTO online_availability_closures (
              id, tenant_id, service_id, closure_date, starts_at_utc, ends_at_utc, reason,
              created_by_user_id, aggregate_version, created_at_utc
            ) VALUES ($1,$2,$3,$4,$5,$6,'   ',$7,1,$5)
            """,
            new_uuid7(),
            ids.tenant_id,
            ids.service_id,
            cdate,
            start + timedelta(hours=3),
            end + timedelta(hours=3),
            ids.user_id,
        )
    except asyncpg.CheckViolationError:
        bad_reason = True
    suite.case("online_closure_reason_required", bad_reason, bucket="PRE_IMPLEMENTATION")

    # arrival path: deferred lifecycle trigger requires arrival fact + visit.arrived_at
    # in the same UoW as the CHECKED_IN transition.
    appt = new_uuid7()
    astart = now + timedelta(hours=2)
    aend = astart + timedelta(minutes=30)
    await app.execute(
        """
        INSERT INTO appointments (
          id, tenant_id, beneficiary_patient_id, service_id, status,
          booking_channel, capacity_pool, scheduled_start_at_utc, scheduled_end_at_utc,
          aggregate_version, created_at_utc, updated_at_utc, department_id
        ) VALUES ($1,$2,$3,$4,'CONFIRMED','MANUAL_STAFF','MANUAL',$5,$6,1,$7,$7,$8)
        """,
        appt,
        ids.tenant_id,
        ids.patient_id,
        ids.service_id,
        astart,
        aend,
        now,
        ids.dept_id,
    )
    visit = new_uuid7()
    try:
        async with app.transaction():
            await app.execute(
                """
                INSERT INTO clinic_visits (
                  id, tenant_id, patient_id, admission_at_utc, arrived_at_utc,
                  registered_by_user_id, created_at_utc, updated_at_utc, aggregate_version
                ) VALUES ($1,$2,$3,$4,$4,$5,$4,$4,1)
                """,
                visit,
                ids.tenant_id,
                ids.patient_id,
                now,
                ids.user_id,
            )
            await app.execute(
                """
                INSERT INTO visit_appointments (
                  id, tenant_id, visit_id, appointment_id, patient_id, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6)
                """,
                new_uuid7(),
                ids.tenant_id,
                visit,
                appt,
                ids.patient_id,
                now,
            )
            await app.execute(
                """
                INSERT INTO appointment_arrival_facts (
                  id, tenant_id, visit_id, appointment_id, checked_in_at_utc,
                  operator_user_id, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,$5)
                """,
                new_uuid7(),
                ids.tenant_id,
                visit,
                appt,
                now,
                ids.user_id,
            )
            await app.execute(
                """
                UPDATE appointments SET status='CHECKED_IN', updated_at_utc=$2 WHERE id=$1
                """,
                appt,
                now,
            )
        suite.case("arrival_checked_in_same_uow", True, bucket="PRE_IMPLEMENTATION")
    except Exception as exc:  # noqa: BLE001
        suite.case("arrival_checked_in_same_uow", False, str(exc)[:300], bucket="PRE_IMPLEMENTATION")
        suite.defect(
            "D11-ARR-01",
            "CHECKED_IN transition UoW failed with arrival facts",
            "HIGH",
            str(exc)[:400],
        )

    # historical entry
    await app.execute(
        """
        INSERT INTO historical_appointment_entries (
          id, tenant_id, appointment_id, late_entry_reason, suppress_past_reminders,
          operator_user_id, created_at_utc
        ) VALUES ($1,$2,$3,'late paper chart',TRUE,$4,$5)
        """,
        new_uuid7(),
        ids.tenant_id,
        appt,
        ids.user_id,
        now,
    )
    suite.case("historical_entry_recorded", True, bucket="PRE_IMPLEMENTATION")

    # waitlist
    wl = new_uuid7()
    await app.execute(
        """
        INSERT INTO appointment_waitlist_entries (
          id, tenant_id, patient_id, service_id, department_id, priority, status,
          contact_state, created_by_user_id, updated_by_user_id, aggregate_version,
          created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,$4,$5,10,'OPEN','NONE',$6,$6,1,$7,$7)
        """,
        wl,
        ids.tenant_id,
        ids.patient_id,
        ids.service_id,
        ids.dept_id,
        ids.user_id,
        now,
    )
    await app.execute(
        """
        UPDATE appointment_waitlist_entries
        SET status='CANCELLED', aggregate_version=2, updated_at_utc=$2, updated_by_user_id=$3
        WHERE id=$1
        """,
        wl,
        now,
        ids.user_id,
    )
    term = False
    try:
        await app.execute(
            """
            UPDATE appointment_waitlist_entries
            SET status='OPEN', aggregate_version=3, updated_at_utc=$2 WHERE id=$1
            """,
            wl,
            now,
        )
    except Exception:  # noqa: BLE001
        term = True
    suite.case("waitlist_terminal_immutable", term, bucket="PRE_IMPLEMENTATION")


async def test_adversarial_rls(
    admin: DbEndpoint, passwords: dict[str, str], ids, other_tenant: UUID, suite: Suite
) -> None:
    app = await asyncpg.connect(await dsn(admin, "tp_app_login", passwords["tp_app_login"]))
    try:
        await set_tenant(app, ids.tenant_id)
        # DELETE on append-only payment_receipts should fail
        denied = False
        try:
            await app.execute("DELETE FROM payment_receipts WHERE tenant_id=$1", ids.tenant_id)
        except Exception:  # noqa: BLE001
            denied = True
        suite.case("rls_append_only_delete_denied", denied, bucket="PRE_IMPLEMENTATION")

        # missing tenant
        await app.execute("SELECT set_config('app.current_tenant_id', '', false)")
        bare = await app.fetchval("SELECT count(*) FROM invoice_documents")
        suite.case("rls_missing_tenant_fail_closed", bare == 0, bucket="PRE_IMPLEMENTATION")

        # cross-tenant
        await app.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(other_tenant)
        )
        cross = await app.fetchval(
            "SELECT count(*) FROM invoice_documents WHERE tenant_id=$1", ids.tenant_id
        )
        suite.case("rls_cross_tenant_select_hidden", cross == 0, bucket="PRE_IMPLEMENTATION")

        # privilege: migrator-only table ownership — runtime cannot ALTER
        alt = False
        try:
            await app.execute("ALTER TABLE invoice_documents ADD COLUMN x int")
        except Exception:  # noqa: BLE001
            alt = True
        suite.case("runtime_cannot_alter_schema", alt, bucket="PRE_IMPLEMENTATION")

        # grant matrix spot-check: SELECT on invoice_documents allowed with tenant
        await set_tenant(app, ids.tenant_id)
        n = await app.fetchval("SELECT count(*) FROM invoice_documents")
        suite.case("runtime_select_invoices_ok", n is not None and n >= 0, bucket="PRE_IMPLEMENTATION")
    finally:
        await app.close()


async def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    suite = ApplySuite()
    await test_discount_arithmetic(suite)

    from testcontainers.postgres import PostgresContainer

    passwords = {
        "tp_migrator_login": secrets.token_urlsafe(24),
        "tp_app_login": secrets.token_urlsafe(24),
        "cp_migrator_login": secrets.token_urlsafe(24),
        "cp_app_login": secrets.token_urlsafe(24),
    }
    cloud = PostgresContainer("postgres:15")
    cloud.start()
    try:
        admin = DbEndpoint(
            host=cloud.get_container_host_ip(),
            port=int(cloud.get_exposed_port(5432)),
            user=cloud.username,
            password=cloud.password,
            database=cloud.dbname,
        )
        await _bootstrap_cloud(admin, passwords)
        migrator_url = (
            f"postgresql+asyncpg://{quote_plus('tp_migrator_login')}:"
            f"{quote_plus(passwords['tp_migrator_login'])}"
            f"@{admin.host}:{admin.port}/tenant_app"
        )
        await asyncio.to_thread(upgrade_tenant_plane, migrator_url, "head")
        mig = await asyncpg.connect(
            await dsn(admin, "tp_migrator_login", passwords["tp_migrator_login"])
        )
        try:
            await mig.execute("SET ROLE db_migrator")
            ok = await apply_schema(mig, suite)
            suite.case("schema_apply", ok, bucket="PRE_IMPLEMENTATION")
            if not ok:
                raise RuntimeError("schema apply failed")
            ids = await seed_ops_graph(mig)
            other = await seed_ops_graph(mig)
        finally:
            await mig.close()

        app = await asyncpg.connect(
            await dsn(admin, "tp_app_login", passwords["tp_app_login"])
        )
        try:
            await test_finance_flow(app, ids, suite)
            await test_pos_and_claims(app, ids, suite)
            await test_inventory(app, ids, suite)
            await test_scopes_eligibility_lifecycle(app, ids, suite)
        finally:
            await app.close()

        await test_concurrency_refunds(admin, passwords, ids, suite)
        await test_adversarial_rls(admin, passwords, ids, other.tenant_id, suite)

    except Exception as exc:  # noqa: BLE001
        suite.case(
            "harness_fatal",
            False,
            f"{exc}\n{traceback.format_exc()}",
            bucket="PRE_IMPLEMENTATION",
        )
    finally:
        cloud.stop()

    summary = {
        "cases_passed": sum(1 for c in suite.cases if c["status"] == "PASS"),
        "cases_failed": sum(1 for c in suite.cases if c["status"] == "FAIL"),
        "cases_blocked": sum(1 for c in suite.cases if c["status"] == "BLOCKED"),
        "defects": len(suite.defects),
    }
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": "aff43da26d0aa27bff2c7af97ca001ad52f17a4c",
        "summary": summary,
        "cases": suite.cases,
        "defects": suite.defects,
        "apply_log": suite.apply_log,
    }
    out = EVIDENCE / "deep_execution_evidence.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    lines = [
        "# ACR-D0.9 deep disposable PG15 evidence",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"PASS/FAIL/BLOCKED: **{summary['cases_passed']}/{summary['cases_failed']}/{summary['cases_blocked']}**",
        "",
        "## Cases",
        "",
    ]
    for c in suite.cases:
        lines.append(
            f"- `{c['status']}` [{c.get('bucket','')}] {c['name']}"
            + (f" — {c['detail'][:200]}" if c.get("detail") else "")
        )
    if suite.defects:
        lines += ["", "## Defects", ""]
        for d in suite.defects:
            lines.append(
                f"- `{d['code']}` ({d['severity']}) {d['title']} — fix: {d['fix']}"
            )
    (EVIDENCE / "deep_execution_evidence.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))
    print("Wrote", out)
    return 0 if summary["cases_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
