"""Persist ACR-D0.11 disposable ops demo rows through valid contracts."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.demo.builders_appointments import AppointmentBundle
from clinic_ecosystem.infrastructure.demo.builders_catalog import CatalogBundle
from clinic_ecosystem.infrastructure.demo.builders_people import PeopleBundle
from clinic_ecosystem.infrastructure.demo.ids import demo_uuid
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets
from clinic_ecosystem.infrastructure.timezones import require_tehran_zoneinfo

TEHRAN = require_tehran_zoneinfo()


async def ops_schema_present(conn: asyncpg.Connection) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass('public.invoice_documents') IS NOT NULL"))


async def persist_ops_demo(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    targets: DemoTargets,
    people: PeopleBundle,
    staff: PeopleBundle,
    catalog: CatalogBundle,
    appts: AppointmentBundle,
    operator_account_id: UUID,
    now: datetime,
) -> dict[str, Any]:
    """Seed departments, eligibility, waitlist, finance, inventory when schema exists."""
    if not await ops_schema_present(conn):
        return {"skipped": True, "reason": "ops_schema_absent"}

    seed = targets.seed
    dept_id = demo_uuid(seed, "department", 0)
    await conn.execute(
        """
        INSERT INTO departments (
          id, tenant_id, department_code, department_name, is_active,
          aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'GEN','عمومی',TRUE,1,$3,$3)
        ON CONFLICT (tenant_id, department_code) DO NOTHING
        """,
        dept_id,
        tenant_id,
        now,
    )
    # Resolve actual id if conflict
    dept_id = await conn.fetchval(
        "SELECT id FROM departments WHERE tenant_id=$1 AND department_code='GEN'",
        tenant_id,
    )

    # Department ↔ services
    for i, svc in enumerate(catalog.services):
        await conn.execute(
            """
            INSERT INTO department_service_links (
              id, tenant_id, department_id, service_id, is_active, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
            ON CONFLICT (tenant_id, department_id, service_id) DO NOTHING
            """,
            demo_uuid(seed, "dept_svc", i),
            tenant_id,
            dept_id,
            svc.id,
            now,
        )

    # Practitioner resources for practitioner staff + eligibility for all services
    pract_mappings: list[UUID] = []
    pract_staff = [
        s for s in staff.staff if s.staff_kind in {"PRACTITIONER", "MULTI_PRACTITIONER"}
    ]
    rooms = catalog.rooms
    for i, st in enumerate(pract_staff):
        resource_id = st.resource_id or (rooms[i % len(rooms)].id if rooms else None)
        if resource_id is None:
            continue
        mapping_id = demo_uuid(seed, "pract_map", i)
        await conn.execute(
            """
            INSERT INTO staff_practitioner_resources (
              id, tenant_id, staff_profile_id, bookable_resource_id, is_active,
              created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
            ON CONFLICT (tenant_id, staff_profile_id) DO NOTHING
            """,
            mapping_id,
            tenant_id,
            st.id,
            resource_id,
            now,
        )
        actual = await conn.fetchval(
            "SELECT id FROM staff_practitioner_resources WHERE tenant_id=$1 AND staff_profile_id=$2",
            tenant_id,
            st.id,
        )
        if actual:
            pract_mappings.append(actual)
            await conn.execute(
                """
                INSERT INTO department_practitioner_links (
                  id, tenant_id, department_id, practitioner_mapping_id, is_active,
                  created_at_utc, updated_at_utc
                ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
                ON CONFLICT (tenant_id, department_id, practitioner_mapping_id) DO NOTHING
                """,
                demo_uuid(seed, "dept_pract", i),
                tenant_id,
                dept_id,
                actual,
                now,
            )
            for j, svc in enumerate(catalog.services):
                await conn.execute(
                    """
                    INSERT INTO staff_service_links (
                      id, tenant_id, practitioner_mapping_id, service_id, is_active,
                      aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES ($1,$2,$3,$4,TRUE,1,$5,$5)
                    ON CONFLICT (tenant_id, practitioner_mapping_id, service_id) DO NOTHING
                    """,
                    demo_uuid(seed, "elig", i * 1000 + j),
                    tenant_id,
                    actual,
                    svc.id,
                    now,
                )

    # Cashier shift + instruments
    cash_inst = demo_uuid(seed, "cash_inst", 0)
    pos_inst = demo_uuid(seed, "pos_inst", 0)
    await conn.execute(
        """
        INSERT INTO clinic_payment_instruments (
          id, tenant_id, instrument_kind, instrument_label, external_reference,
          department_id, is_active, created_at_utc
        ) VALUES
          ($1,$2,'CASH_REGISTER','صندوق نقدی','CASH-DEMO-1',$3,TRUE,$4),
          ($5,$2,'POS_TERMINAL','کارتخوان شبیه‌سازی','POS-SIM-DEMO',$3,TRUE,$4)
        ON CONFLICT DO NOTHING
        """,
        cash_inst,
        tenant_id,
        dept_id,
        now,
        pos_inst,
    )
    shift_id = demo_uuid(seed, "shift", 0)
    # Open well before historical demo receipts so shift-window guards pass.
    shift_opened = now - timedelta(days=120)
    await conn.execute(
        """
        INSERT INTO cashier_shifts (
          id, tenant_id, department_id, shift_label, opened_by_user_id,
          opened_at_utc, opening_cash_irr
        ) VALUES ($1,$2,$3,'شیفت نمایشی',$4,$5,0)
        ON CONFLICT (tenant_id, id) DO NOTHING
        """,
        shift_id,
        tenant_id,
        dept_id,
        operator_account_id,
        shift_opened,
    )

    # Billable + inventory items
    item_count = targets.billable_or_inventory_items
    billable_ids: list[UUID] = []
    for i in range(item_count):
        bid = demo_uuid(seed, "billable", i)
        billable_ids.append(bid)
        await conn.execute(
            """
            INSERT INTO billable_items (
              id, tenant_id, item_code, item_name, unit_code, quantity_scale,
              default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,'EA',0,$5,TRUE,1,$6,$6)
            ON CONFLICT (tenant_id, item_code) DO NOTHING
            """,
            bid,
            tenant_id,
            f"ITM-{i:04d}",
            f"قلم مصرفی {i + 1}",
            10_000 + (i % 50) * 500,
            now,
        )
        # Half linked to inventory
        if i % 2 == 0:
            iid = demo_uuid(seed, "inv_item", i)
            await conn.execute(
                """
                INSERT INTO inventory_items (
                  id, tenant_id, billable_item_id, item_code, item_name, unit_code,
                  quantity_scale, is_lot_tracked, requires_expiry, is_active,
                  aggregate_version, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,$3,$4,$5,'EA',0,TRUE,TRUE,TRUE,1,$6,$6)
                ON CONFLICT (tenant_id, item_code) DO NOTHING
                """,
                iid,
                tenant_id,
                bid,
                f"INV-{i:04d}",
                f"موجودی {i + 1}",
                now,
            )
            lot = demo_uuid(seed, "inv_lot", i)
            expires = date.today() + timedelta(days=90 + i)
            await conn.execute(
                """
                INSERT INTO inventory_lots (
                  id, tenant_id, item_id, lot_code, is_lot_tracked, requires_expiry,
                  expires_on, lot_status, received_at_utc, created_at_utc, updated_at_utc,
                  aggregate_version
                ) VALUES ($1,$2,$3,$4,TRUE,TRUE,$5,'AVAILABLE',$6,$6,$6,1)
                ON CONFLICT (tenant_id, item_id, lot_code) DO NOTHING
                """,
                lot,
                tenant_id,
                iid,
                f"LOT-{i:04d}",
                expires,
                now,
            )
            await conn.execute(
                """
                INSERT INTO stock_movements (
                  id, tenant_id, item_id, lot_id, movement_kind, quantity_delta, quantity_scale,
                  reason_code, operator_user_id, actor_type, actor_id, correlation_id,
                  occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,'PURCHASE_RECEIPT',100,0,'RECV',$5,'STAFF_USER',$5,$6,$7,$7)
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                demo_uuid(seed, "stock_recv", i),
                tenant_id,
                iid,
                lot,
                operator_account_id,
                demo_uuid(seed, "stock_corr", i),
                now,
            )

    # Future waitlist
    waitlist_n = targets.future_waitlist_entries
    patients = [p for p in people.patients if p.is_active]
    for i in range(waitlist_n):
        patient = patients[i % len(patients)]
        svc = catalog.services[i % len(catalog.services)]
        await conn.execute(
            """
            INSERT INTO appointment_waitlist_entries (
              id, tenant_id, patient_id, service_id, department_id, priority,
              status, contact_state, notes, created_by_user_id, updated_by_user_id,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,$5,$6,'OPEN','NONE',$7,$8,$8,1,$9,$9)
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            demo_uuid(seed, "waitlist", i),
            tenant_id,
            patient.id,
            svc.id,
            dept_id,
            50 + (i % 200),
            f"لیست انتظار نمایشی {i + 1}",
            operator_account_id,
            now,
        )

    # Physical waiting + completed history via required side facts (same UoW as status).
    today = now.astimezone(TEHRAN).date()
    confirmed_today = [
        a
        for a in appts.appointments
        if a.status == "CONFIRMED" and a.start_utc.astimezone(TEHRAN).date() == today
    ]
    confirmed_past = [
        a
        for a in appts.appointments
        if a.status == "CONFIRMED" and a.start_utc.astimezone(TEHRAN).date() < today
    ]
    target_waiting = targets.checked_in_waiting_today
    arrival_count = 0
    completed_count = 0

    async def _check_in(i: int, appt: Any, *, complete_after: bool = False) -> None:
        nonlocal arrival_count, completed_count
        visit_id = demo_uuid(seed, "visit", i)
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO clinic_visits (
                  id, tenant_id, patient_id, admission_at_utc, arrived_at_utc,
                  registered_by_user_id, aggregate_version, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,$3,$4,$4,$5,1,$4,$4)
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                visit_id,
                tenant_id,
                appt.patient_id,
                appt.start_utc,
                operator_account_id,
            )
            await conn.execute(
                """
                INSERT INTO visit_appointments (
                  id, tenant_id, visit_id, patient_id, appointment_id, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (tenant_id, appointment_id) DO NOTHING
                """,
                demo_uuid(seed, "visit_appt", i),
                tenant_id,
                visit_id,
                appt.patient_id,
                appt.id,
                appt.start_utc,
            )
            await conn.execute(
                """
                INSERT INTO appointment_arrival_facts (
                  id, tenant_id, visit_id, appointment_id, checked_in_at_utc,
                  operator_user_id, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,$5)
                ON CONFLICT (tenant_id, appointment_id) DO NOTHING
                """,
                demo_uuid(seed, "arrival", i),
                tenant_id,
                visit_id,
                appt.id,
                appt.start_utc,
                operator_account_id,
            )
            await conn.execute(
                """
                UPDATE appointments
                SET status = 'CHECKED_IN', updated_at_utc = $3,
                    aggregate_version = aggregate_version + 1
                WHERE tenant_id = $1 AND id = $2 AND status = 'CONFIRMED'
                """,
                tenant_id,
                appt.id,
                appt.start_utc,
            )
            await conn.execute(
                """
                UPDATE appointment_resource_allocations
                SET allocation_status = 'CHECKED_IN'
                WHERE tenant_id = $1 AND appointment_id = $2
                """,
                tenant_id,
                appt.id,
            )
            if complete_after:
                sr_id = demo_uuid(seed, "svc_rec", i)
                await conn.execute(
                    """
                    INSERT INTO service_records (
                      id, tenant_id, patient_id, service_id, appointment_id, visit_id,
                      department_id, record_kind, occurred_at_utc, operator_user_id,
                      created_at_utc
                    ) VALUES (
                      $1,$2,$3,$4,$5,$6,$7,'PERFORMED',$8,$9,$8
                    )
                    ON CONFLICT (tenant_id, id) DO NOTHING
                    """,
                    sr_id,
                    tenant_id,
                    appt.patient_id,
                    appt.service_id,
                    appt.id,
                    visit_id,
                    dept_id,
                    appt.end_utc,
                    operator_account_id,
                )
                await conn.execute(
                    """
                    UPDATE appointments
                    SET status = 'COMPLETED', updated_at_utc = $3,
                        aggregate_version = aggregate_version + 1
                    WHERE tenant_id = $1 AND id = $2 AND status = 'CHECKED_IN'
                    """,
                    tenant_id,
                    appt.id,
                    appt.end_utc,
                )
                await conn.execute(
                    """
                    UPDATE appointment_resource_allocations
                    SET allocation_status = 'COMPLETED'
                    WHERE tenant_id = $1 AND appointment_id = $2
                    """,
                    tenant_id,
                    appt.id,
                )
                appt.status = "COMPLETED"
                appt.allocation_status = "COMPLETED"
                completed_count += 1
            else:
                appt.status = "CHECKED_IN"
                appt.allocation_status = "CHECKED_IN"
            arrival_count += 1

    for i, appt in enumerate(confirmed_today[:target_waiting]):
        await _check_in(i, appt, complete_after=False)

    # Complete a slice of past CONFIRMED appointments with PERFORMED service records.
    complete_target = min(len(confirmed_past), max(targets.appointments // 5, 10))
    for j, appt in enumerate(confirmed_past[:complete_target]):
        await _check_in(10_000 + j, appt, complete_after=True)

    # Invoices: mix of unpaid / partial / paid / discounted / refunded
    invoice_n = targets.invoices
    discount_budget = targets.discounts
    refund_budget = targets.refunds
    discounts_made = 0
    refunds_made = 0
    receipts_made = 0
    pract = pract_mappings[0] if pract_mappings else None
    completed_appts = [a for a in appts.appointments if a.status in {"COMPLETED", "CHECKED_IN", "CONFIRMED"}]

    for i in range(invoice_n):
        patient = patients[i % len(patients)]
        svc = catalog.services[i % len(catalog.services)]
        # Link appointment only when patient+service match (FK MATCH SIMPLE).
        linked_appt = None
        if completed_appts:
            candidate = completed_appts[i % len(completed_appts)]
            if candidate.patient_id == patient.id and candidate.service_id == svc.id:
                linked_appt = candidate.id
            else:
                for a in completed_appts[i : i + 20]:
                    if a.patient_id == patient.id and a.service_id == svc.id:
                        linked_appt = a.id
                        break
        inv_id = demo_uuid(seed, "invoice", i)
        line_id = demo_uuid(seed, "inv_line", i)
        unit_price = 80_000 + (i % 40) * 2_500
        discount = 0
        if discounts_made < discount_budget and i % max(1, invoice_n // max(1, discount_budget)) == 0:
            discount = min(10_000 + (i % 5) * 1_000, unit_price // 4)
            discounts_made += 1
        payable = unit_price - discount
        created = now - timedelta(days=(i % 60), hours=(i % 12))
        # Cycle: unpaid, partial, paid, paid+refund
        mode = i % 10
        inv_number = f"DI{str(inv_id).replace('-', '')[:30]}"
        # Guards require DRAFT birth then POST transition.
        await conn.execute(
            """
            INSERT INTO invoice_documents (
              id, tenant_id, status, beneficiary_patient_id, department_id,
              currency_code, aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,'DRAFT',$3,$4,'IRR',1,$5,$5)
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            inv_id,
            tenant_id,
            patient.id,
            dept_id,
            created,
        )
        charge_reason = None if linked_appt else "demo_charge_without_linked_service"
        await conn.execute(
            """
            INSERT INTO invoice_lines (
              id, tenant_id, invoice_id, beneficiary_patient_id, line_no, line_status,
              department_id, practitioner_mapping_id, appointment_id, service_id, line_kind,
              description_snapshot, code_snapshot, quantity_scaled, quantity_scale,
              unit_code_snapshot, unit_price_irr, gross_service_amount, discount_amount,
              patient_payable_amount, pricing_rule_version, payer_policy_version,
              revenue_policy_version, charge_without_service_reason, created_at_utc
            ) VALUES (
              $1,$2,$3,$4,1,'ACTIVE',$5,$6,$7,$8,'SERVICE',
              $9,$10,1,0,'EA',$11,$11,$12,$13,
              'price-v1','payer-v1','rev-v1',$14,$15
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            line_id,
            tenant_id,
            inv_id,
            patient.id,
            dept_id,
            pract,
            linked_appt,
            svc.id,
            svc.name,
            svc.code,
            unit_price,
            discount,
            payable,
            charge_reason,
            created,
        )
        if discount > 0:
            await conn.execute(
                """
                INSERT INTO draft_discount_actions (
                  id, tenant_id, invoice_id, invoice_line_id, discount_scope,
                  calculation_kind, requested_value, reason_code, operator_user_id,
                  policy_version, occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,'LINE','FIXED_IRR',$5,'DEMO',$6,'disc-v1',$7,$7)
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                demo_uuid(seed, "discount", i),
                tenant_id,
                inv_id,
                line_id,
                discount,
                operator_account_id,
                created,
            )
        await conn.execute(
            """
            UPDATE invoice_documents SET
              status='POSTED', invoice_number=$1, issued_at_utc=$2, posted_at_utc=$2,
              posted_by_user_id=$3, aggregate_version=2, updated_at_utc=$2
            WHERE tenant_id=$4 AND id=$5 AND status='DRAFT'
            """,
            inv_number,
            created,
            operator_account_id,
            tenant_id,
            inv_id,
        )

        pay_amount = 0
        if mode in {1, 2, 3, 4, 5, 6, 7}:  # partial or paid
            pay_amount = payable if mode >= 3 else max(1, payable // 2)
        if pay_amount > 0:
            receipt_id = demo_uuid(seed, "receipt", i)
            method = "CASH" if i % 2 == 0 else "POS"
            evidence = None if method == "CASH" else f"pos-sim-evidence-{i}"
            instrument = None if method == "CASH" else pos_inst
            terminal = None if method == "CASH" else "SETTLED"
            await conn.execute(
                """
                INSERT INTO payment_receipts (
                  id, tenant_id, receipt_number, amount_irr, currency_code, payment_method,
                  occurred_at_utc, operator_user_id, actor_type, actor_id, correlation_id,
                  payer_patient_id, credit_beneficiary_patient_id, payer_source,
                  department_id, shift_id, instrument_id, verification_evidence_ref,
                  terminal_state, verified_at_utc, created_at_utc
                ) VALUES (
                  $1,$2,$3,$4,'IRR',$5,$6,$7,'STAFF_USER',$7,$8,$9,$9,'patient',
                  $10,$11,$12,$13,$14,$6,$6
                )
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                receipt_id,
                tenant_id,
                f"DR{str(receipt_id).replace('-', '')[:30]}",
                pay_amount,
                method,
                created + timedelta(minutes=5),
                operator_account_id,
                demo_uuid(seed, "rcpt_corr", i),
                patient.id,
                dept_id,
                shift_id,
                instrument,
                evidence,
                terminal,
            )
            alloc_id = demo_uuid(seed, "alloc", i)
            await conn.execute(
                """
                INSERT INTO receipt_allocations (
                  id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
                  amount_irr, operator_user_id, correlation_id, occurred_at_utc, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,'APPLY',$6,$7,$8,$9,$9)
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                alloc_id,
                tenant_id,
                receipt_id,
                inv_id,
                line_id,
                pay_amount,
                operator_account_id,
                demo_uuid(seed, "alloc_corr", i),
                created + timedelta(minutes=5),
            )
            receipts_made += 1

            if mode == 7 and refunds_made < refund_budget and pay_amount >= 10_000:
                # Full reverse then refund linked to original allocation
                rev_id = demo_uuid(seed, "alloc_rev", i)
                await conn.execute(
                    """
                    INSERT INTO receipt_allocations (
                      id, tenant_id, receipt_id, invoice_id, invoice_line_id, allocation_kind,
                      reverses_allocation_id, amount_irr, operator_user_id, correlation_id,
                      reason_code, occurred_at_utc, created_at_utc
                    ) VALUES ($1,$2,$3,$4,$5,'REVERSE',$6,$7,$8,$9,'FULL',$10,$10)
                    ON CONFLICT (tenant_id, id) DO NOTHING
                    """,
                    rev_id,
                    tenant_id,
                    receipt_id,
                    inv_id,
                    line_id,
                    alloc_id,
                    pay_amount,
                    operator_account_id,
                    demo_uuid(seed, "rev_corr", i),
                    created + timedelta(minutes=30),
                )
                refund_amt = min(pay_amount, 50_000 + (i % 10) * 1_000)
                refund_evidence = None if method == "CASH" else f"pos-refund-evidence-{i}"
                refund_instrument = None if method == "CASH" else pos_inst
                await conn.execute(
                    """
                    INSERT INTO clinic_payment_refunds (
                      id, tenant_id, refund_number, original_receipt_id, invoice_id,
                      invoice_line_id, original_allocation_id, amount_irr, currency_code,
                      refund_method, instrument_id, verification_evidence_ref, reason_code,
                      operator_user_id, actor_type, actor_id, department_id, shift_id,
                      correlation_id, occurred_at_utc, created_at_utc
                    ) VALUES (
                      $1,$2,$3,$4,$5,$6,$7,$8,'IRR',$9,$10,$11,'DEMO_REFUND',
                      $12,'STAFF_USER',$12,$13,$14,$15,$16,$16
                    )
                    ON CONFLICT (tenant_id, id) DO NOTHING
                    """,
                    demo_uuid(seed, "refund", i),
                    tenant_id,
                    f"RF{str(demo_uuid(seed, 'refund', i)).replace('-', '')[:30]}",
                    receipt_id,
                    inv_id,
                    line_id,
                    alloc_id,
                    refund_amt,
                    method,
                    refund_instrument,
                    refund_evidence,
                    operator_account_id,
                    dept_id,
                    shift_id,
                    demo_uuid(seed, "refund_corr", i),
                    created + timedelta(hours=1),
                )
                refunds_made += 1

    # ACR-D0.11: backfill explicit ALL scopes for existing flat grants (demo cutover).
    # Without scope rows the scope-aware resolver default-denies every permission.
    scope_rows = 0
    grant_rows = await conn.fetch(
        """
        SELECT rpa.id AS grant_id
        FROM role_permission_assignments rpa
        WHERE rpa.tenant_id = $1
          AND NOT EXISTS (
            SELECT 1 FROM role_permission_scopes rps
            WHERE rps.tenant_id = rpa.tenant_id
              AND rps.role_permission_assignment_id = rpa.id
          )
        """,
        tenant_id,
    )
    for idx, row in enumerate(grant_rows):
        inserted = await conn.fetchval(
            """
            INSERT INTO role_permission_scopes (
              id, tenant_id, role_permission_assignment_id, scope_mode,
              department_id, service_id, provider_resource_id,
              created_by_user_id, created_at_utc
            )
            SELECT $1,$2,$3,'ALL',NULL,NULL,NULL,$4,$5
            WHERE NOT EXISTS (
              SELECT 1 FROM role_permission_scopes
              WHERE tenant_id = $2 AND role_permission_assignment_id = $3
            )
            RETURNING id
            """,
            demo_uuid(seed, "scope_all", idx),
            tenant_id,
            row["grant_id"],
            operator_account_id,
            now,
        )
        if inserted is not None:
            scope_rows += 1

    # Scoped receptionist demo: FILTER department grant for PATIENTS_VIEW_PROFILE only
    # on a dedicated role so ALL vs FILTER mutual exclusivity stays intact.
    scoped_role_id = demo_uuid(seed, "scoped_recv_role", 0)
    await conn.execute(
        """
        INSERT INTO tenant_roles (
          id, tenant_id, role_code, role_name, is_system_defined, created_at_utc
        ) VALUES ($1,$2,'SCOPED_RECEPTIONIST','پذیرش محدود بخش',FALSE,$3)
        ON CONFLICT (tenant_id, role_code) DO NOTHING
        """,
        scoped_role_id,
        tenant_id,
        now,
    )
    scoped_role_id = await conn.fetchval(
        "SELECT id FROM tenant_roles WHERE tenant_id=$1 AND role_code='SCOPED_RECEPTIONIST'",
        tenant_id,
    )
    scoped_grant_id = demo_uuid(seed, "scoped_recv_grant", 0)
    await conn.execute(
        """
        INSERT INTO role_permission_assignments (
          id, tenant_id, role_id, permission_code, granted_at_utc
        ) VALUES ($1,$2,$3,'BETA02_PATIENTS_VIEW_PROFILE',$4)
        ON CONFLICT (tenant_id, role_id, permission_code) DO NOTHING
        """,
        scoped_grant_id,
        tenant_id,
        scoped_role_id,
        now,
    )
    scoped_grant_id = await conn.fetchval(
        """
        SELECT id FROM role_permission_assignments
        WHERE tenant_id=$1 AND role_id=$2 AND permission_code='BETA02_PATIENTS_VIEW_PROFILE'
        """,
        tenant_id,
        scoped_role_id,
    )
    if scoped_grant_id is not None:
        await conn.execute(
            """
            INSERT INTO role_permission_scopes (
              id, tenant_id, role_permission_assignment_id, scope_mode,
              department_id, service_id, provider_resource_id,
              created_by_user_id, created_at_utc
            ) VALUES ($1,$2,$3,'FILTER',$4,NULL,NULL,$5,$6)
            ON CONFLICT DO NOTHING
            """,
            demo_uuid(seed, "scope_filter", 0),
            tenant_id,
            scoped_grant_id,
            dept_id,
            operator_account_id,
            now,
        )

    # Online booking reviews + staff notifications (dashboard R2 disposable tables).
    reviews_made = 0
    notifications_made = 0
    reviews_ok = await conn.fetchval(
        "SELECT to_regclass('public.online_booking_reviews') IS NOT NULL"
    )
    notif_ok = await conn.fetchval(
        "SELECT to_regclass('public.clinic_staff_notifications') IS NOT NULL"
    )
    online_confirmed = [
        a
        for a in appts.appointments
        if a.status == "CONFIRMED"
        and a.booking_channel in {"ONLINE_WEB", "ONLINE_BOT"}
    ]
    if reviews_ok and online_confirmed:
        # Review a minority so online_unreviewed_count stays visible.
        review_n = max(1, min(len(online_confirmed) // 4, 40))
        for i, appt in enumerate(online_confirmed[:review_n]):
            await conn.execute(
                """
                INSERT INTO online_booking_reviews (
                  id, tenant_id, appointment_id, reviewed_by_user_id,
                  reviewed_at_utc, note, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,$5)
                ON CONFLICT (tenant_id, appointment_id) DO NOTHING
                """,
                demo_uuid(seed, "online_review", i),
                tenant_id,
                appt.id,
                operator_account_id,
                now,
                "بررسی نمایشی نوبت آنلاین",
            )
            reviews_made += 1
    if notif_ok:
        samples = [
            ("ONLINE_BOOKING", "نوبت آنلاین جدید", "یک نوبت از وب‌سایت ثبت شد."),
            ("ONLINE_BOOKING", "نوبت ربات", "یک نوبت از ربات ثبت شد."),
            ("OPS", "یادآوری شیفت", "شیفت صندوق نمایشی باز است."),
        ]
        for i, (kind, title, body) in enumerate(samples):
            related = online_confirmed[i].id if i < len(online_confirmed) else None
            await conn.execute(
                """
                INSERT INTO clinic_staff_notifications (
                  id, tenant_id, notification_kind, title, body,
                  related_appointment_id, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                demo_uuid(seed, "staff_notif", i),
                tenant_id,
                kind,
                title,
                body,
                related,
                now - timedelta(hours=i + 1),
            )
            notifications_made += 1
        # Mark the oldest sample as read for the operator.
        if notifications_made:
            await conn.execute(
                """
                INSERT INTO clinic_notification_reads (
                  id, tenant_id, notification_id, reader_user_id, read_at_utc
                ) VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (tenant_id, notification_id, reader_user_id) DO NOTHING
                """,
                demo_uuid(seed, "notif_read", 0),
                tenant_id,
                demo_uuid(seed, "staff_notif", len(samples) - 1),
                operator_account_id,
                now,
            )

    return {
        "skipped": False,
        "department_id": str(dept_id),
        "practitioner_mappings": len(pract_mappings),
        "billable_items": item_count,
        "waitlist_entries": waitlist_n,
        "arrival_facts": arrival_count,
        "completed_via_service_records": completed_count,
        "invoices": invoice_n,
        "discounts": discounts_made,
        "receipts": receipts_made,
        "refunds": refunds_made,
        "permission_scopes_all_backfill": scope_rows,
        "scoped_receptionist_role_id": str(scoped_role_id) if scoped_role_id else None,
        "online_booking_reviews": reviews_made,
        "staff_notifications": notifications_made,
    }
