"""Shared fixtures and arithmetic helpers for ACR-D0.9 deep disposable validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

import asyncpg

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.m1_seed import seed_scheduling_graph


def largest_remainder_allocate(
    total: int, weights: list[int], order_keys: list[tuple]
) -> list[int]:
    """Distribute `total` across weights by largest remainder; tie-break by order_keys."""
    if total < 0:
        raise ValueError("total must be >= 0")
    if not weights:
        return []
    wsum = sum(weights)
    if wsum <= 0:
        raise ValueError("weights must sum > 0")
    exact = [Decimal(total) * Decimal(w) / Decimal(wsum) for w in weights]
    floors = [int(x.to_integral_value(rounding=ROUND_HALF_UP) if False else x.to_integral_value(rounding="ROUND_FLOOR")) for x in exact]
    # use floor then largest remainder
    floors = [int(x) for x in (e.to_integral_value(rounding="ROUND_FLOOR") for e in exact)]
    rem = total - sum(floors)
    frac = [(exact[i] - floors[i], order_keys[i], i) for i in range(len(weights))]
    frac.sort(key=lambda t: (-t[0], t[1]))
    out = floors[:]
    for k in range(rem):
        out[frac[k][2]] += 1
    return out


@dataclass
class DeepIds:
    tenant_id: UUID
    patient_id: UUID
    user_id: UUID
    role_id: UUID
    service_id: UUID
    room_id: UUID
    staff_id: UUID
    pract_resource_id: UUID
    pract_mapping_id: UUID
    dept_id: UUID
    rpa_id: UUID
    billable_item_id: UUID
    shift_id: UUID
    cash_instrument_id: UUID
    pos_instrument_id: UUID


async def seed_ops_graph(conn: asyncpg.Connection) -> DeepIds:
    """Seed scheduling graph + practitioner/dept/instruments/shift needed by ops packages."""
    now = datetime.now(timezone.utc)
    base = await seed_scheduling_graph(conn)
    staff_person = new_uuid7()
    staff_id = new_uuid7()
    pract = new_uuid7()
    mapping = new_uuid7()
    dept = new_uuid7()
    billable = new_uuid7()
    shift = new_uuid7()
    cash_inst = new_uuid7()
    pos_inst = new_uuid7()

    await conn.execute(
        """
        INSERT INTO tenant_persons (
          id, tenant_id, first_name, last_name, birth_date, gender,
          aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'Dr','Deep',NULL,NULL,1,$3,$3)
        """,
        staff_person,
        base.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO staff_profiles (
          id, tenant_id, person_id, staff_kind, is_active, created_at_utc
        ) VALUES ($1,$2,$3,'DOCTOR',TRUE,$4)
        """,
        staff_id,
        base.tenant_id,
        staff_person,
        now,
    )
    await conn.execute(
        """
        INSERT INTO bookable_resources (
          id, tenant_id, resource_type, resource_name, is_active, created_at_utc
        ) VALUES ($1,$2,'PRACTITIONER','Dr Deep',TRUE,$3)
        """,
        pract,
        base.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO staff_practitioner_resources (
          id, tenant_id, staff_profile_id, bookable_resource_id,
          is_active, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
        """,
        mapping,
        base.tenant_id,
        staff_id,
        pract,
        now,
    )
    await conn.execute(
        """
        INSERT INTO staff_service_links (
          id, tenant_id, practitioner_mapping_id, service_id, is_active,
          aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,$4,TRUE,1,$5,$5)
        """,
        new_uuid7(),
        base.tenant_id,
        mapping,
        base.service_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO departments (
          id, tenant_id, department_code, department_name, is_active,
          aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'GEN','General',TRUE,1,$3,$3)
        """,
        dept,
        base.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO department_service_links (
          id, tenant_id, department_id, service_id, is_active, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
        """,
        new_uuid7(),
        base.tenant_id,
        dept,
        base.service_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO department_practitioner_links (
          id, tenant_id, department_id, practitioner_mapping_id, is_active,
          created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
        """,
        new_uuid7(),
        base.tenant_id,
        dept,
        mapping,
        now,
    )
    # permission assignment for scope tests
    rpa = new_uuid7()
    await conn.execute(
        """
        INSERT INTO role_permission_assignments (
          id, tenant_id, role_id, permission_code, granted_at_utc
        ) VALUES ($1,$2,$3,'APPOINTMENT_VIEW',$4)
        ON CONFLICT DO NOTHING
        """,
        rpa,
        base.tenant_id,
        base.role_id,
        now,
    )
    # if conflict, fetch existing
    rpa_id = await conn.fetchval(
        """
        SELECT id FROM role_permission_assignments
        WHERE tenant_id=$1 AND role_id=$2 AND permission_code='APPOINTMENT_VIEW'
        """,
        base.tenant_id,
        base.role_id,
    )
    # Fail-closed scopes: backfill explicit ALL for every grant in this tenant.
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
        base.tenant_id,
    )
    for row in grant_rows:
        await conn.execute(
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
            """,
            new_uuid7(),
            base.tenant_id,
            row["grant_id"],
            base.user_account_id,
            now,
        )
    await conn.execute(
        """
        INSERT INTO billable_items (
          id, tenant_id, item_code, item_name, unit_code, quantity_scale,
          default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,'FEE','Procedure fee','EA',0,50000,TRUE,1,$3,$3)
        """,
        billable,
        base.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO clinic_payment_instruments (
          id, tenant_id, instrument_kind, instrument_label, external_reference,
          department_id, is_active, created_at_utc
        ) VALUES
          ($1,$2,'CASH_REGISTER','Cash drawer','CASH-1',$3,TRUE,$4),
          ($5,$2,'POS_TERMINAL','POS sim','POS-SIM-1',$3,TRUE,$4)
        """,
        cash_inst,
        base.tenant_id,
        dept,
        now,
        pos_inst,
    )
    await conn.execute(
        """
        INSERT INTO cashier_shifts (
          id, tenant_id, department_id, shift_label, opened_by_user_id,
          opened_at_utc, opening_cash_irr
        ) VALUES ($1,$2,$3,'Morning',$4,$5,0)
        """,
        shift,
        base.tenant_id,
        dept,
        base.user_account_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO service_availability_guards (
          id, tenant_id, service_id, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1,$2,$3,1,$4,$4)
        """,
        new_uuid7(),
        base.tenant_id,
        base.service_id,
        now,
    )
    return DeepIds(
        tenant_id=base.tenant_id,
        patient_id=base.patient_id,
        user_id=base.user_account_id,
        role_id=base.role_id,
        service_id=base.service_id,
        room_id=base.resource_id,
        staff_id=staff_id,
        pract_resource_id=pract,
        pract_mapping_id=mapping,
        dept_id=dept,
        rpa_id=rpa_id,
        billable_item_id=billable,
        shift_id=shift,
        cash_instrument_id=cash_inst,
        pos_instrument_id=pos_inst,
    )


async def set_tenant(conn: asyncpg.Connection, tenant_id: UUID) -> None:
    await conn.execute("SET ROLE db_app_runtime")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )


async def create_posted_service_invoice(
    conn: asyncpg.Connection,
    ids: DeepIds,
    *,
    line_gross: int = 100_000,
    line_discount: int = 0,
    patient_payable: int | None = None,
) -> tuple[UUID, UUID]:
    """Create DRAFT invoice + ACTIVE SERVICE line (charge_without_service_reason) then POST."""
    now = datetime.now(timezone.utc)
    inv = new_uuid7()
    line = new_uuid7()
    payable = patient_payable if patient_payable is not None else (line_gross - line_discount)
    await conn.execute(
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
    await conn.execute(
        """
        INSERT INTO invoice_lines (
          id, tenant_id, invoice_id, beneficiary_patient_id, line_no, line_status,
          department_id, practitioner_mapping_id, service_id, line_kind,
          description_snapshot, code_snapshot, quantity_scaled, quantity_scale,
          unit_code_snapshot, unit_price_irr, gross_service_amount, discount_amount,
          patient_payable_amount, pricing_rule_version, payer_policy_version,
          revenue_policy_version, charge_without_service_reason, created_at_utc
        ) VALUES (
          $1,$2,$3,$4,1,'ACTIVE',$5,$6,$7,'SERVICE',
          'Consultation','CONSULT',1,0,'EA',$8,$8,$9,$10,
          'price-v1','payer-v1','rev-v1','desk_charge_without_linked_service',$11
        )
        """,
        line,
        ids.tenant_id,
        inv,
        ids.patient_id,
        ids.dept_id,
        ids.pract_mapping_id,
        ids.service_id,
        line_gross,
        line_discount,
        payable,
        now,
    )
    # POST
    await conn.execute(
        """
        UPDATE invoice_documents SET
          status='POSTED',
          invoice_number=$1,
          issued_at_utc=$2,
          posted_at_utc=$2,
          posted_by_user_id=$3,
          aggregate_version=2,
          updated_at_utc=$2
        WHERE id=$4
        """,
        f"I{str(inv).replace('-', '')[:31]}",
        now,
        ids.user_id,
        inv,
    )
    return inv, line


async def record_cash_receipt(
    conn: asyncpg.Connection,
    ids: DeepIds,
    *,
    amount: int,
    receipt_number: str,
) -> UUID:
    now = datetime.now(timezone.utc)
    rid = new_uuid7()
    await conn.execute(
        """
        INSERT INTO payment_receipts (
          id, tenant_id, receipt_number, amount_irr, currency_code, payment_method,
          occurred_at_utc, operator_user_id, actor_type, actor_id, correlation_id,
          payer_patient_id, credit_beneficiary_patient_id, payer_source,
          department_id, shift_id, verified_at_utc, created_at_utc
        ) VALUES (
          $1,$2,$3,$4,'IRR','CASH',$5,$6,'STAFF_USER',$6,$7,$8,$8,'patient',$9,$10,$5,$5
        )
        """,
        rid,
        ids.tenant_id,
        receipt_number,
        amount,
        now,
        ids.user_id,
        new_uuid7(),
        ids.patient_id,
        ids.dept_id,
        ids.shift_id,
    )
    return rid
