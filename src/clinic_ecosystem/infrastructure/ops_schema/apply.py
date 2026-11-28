"""Apply ACR-D0.9/D0.11 proposed ops DDL into a disposable Tenant Plane DB.

Governance: this is NOT an official Alembic revision. It may only run when
``CLINIC_OPS_SCHEMA_MODE=disposable`` (or explicit caller flag) after tp0007.
Never rewrite TP0001–TP0007 history.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[4]
EXTRACTED = REPO_ROOT / "docs" / "validation" / "d010" / "d09_extracted"
CORRECTED = REPO_ROOT / "docs" / "validation" / "d010" / "d09_corrected"

# Same topological order as Task 33 harness (FK-safe).
APPLY_STEPS: list[tuple[str, list[str]]] = [
    ("eligibility", ["05.sql"]),
    ("departments", ["06.sql"]),
    ("scopes", ["07.sql"]),
    ("notes", ["10.sql"]),
    ("identity_reviews", ["11.sql"]),
    ("arrival", ["08.sql"]),
    ("waitlist", ["04.sql"]),
    ("online_close", ["09.sql"]),
    ("ledger", ["00.sql", "01.sql", "02.sql"]),
    ("receipt_guards", ["15.sql"]),
    ("invoice_guards", ["14.sql"]),
    ("inventory", ["03.sql"]),
    ("crossrow", ["16.sql"]),
    ("misc_guards", ["17.sql"]),
    ("rls", ["13.sql"]),
]

SKIP = {"12.sql"}  # person_merge SOURCE_REQUIRED


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_dollar = False
    dollar_tag = ""
    in_line_comment = False
    in_block_comment = False
    in_single = False
    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""
        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append("/")
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue
        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":
                buf.append("'")
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_dollar:
            if script.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar = False
                dollar_tag = ""
                continue
            buf.append(ch)
            i += 1
            continue
        if ch == "-" and nxt == "-":
            buf.append(ch)
            buf.append(nxt)
            i += 2
            in_line_comment = True
            continue
        if ch == "/" and nxt == "*":
            buf.append(ch)
            buf.append(nxt)
            i += 2
            in_block_comment = True
            continue
        if ch == "'":
            buf.append(ch)
            i += 1
            in_single = True
            continue
        if ch == "$":
            m_end = script.find("$", i + 1)
            if m_end != -1 and all(
                c.isalnum() or c == "_" for c in script[i + 1 : m_end]
            ):
                dollar_tag = script[i : m_end + 1]
                buf.append(dollar_tag)
                i = m_end + 1
                in_dollar = True
                continue
        if ch == ";":
            buf.append(";")
            statements.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    trailing = "".join(buf).strip()
    if trailing:
        statements.append(trailing)
    return statements


def _is_executable(stmt: str) -> bool:
    lines = [
        line.strip()
        for line in stmt.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    body = " ".join(lines).strip()
    return bool(body) and body != ";"


async def _exec_script(conn: asyncpg.Connection, script: str) -> None:
    for stmt in _split_sql_statements(script):
        body = stmt.strip()
        if body and _is_executable(body):
            await conn.execute(body)


async def _prepare_rls_tables(conn: asyncpg.Connection) -> None:
    known = await conn.fetch(
        """
        SELECT relname FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r'
          AND relname = ANY($1::text[])
        """,
        [
            "billable_items",
            "cashier_shifts",
            "clinic_payment_instruments",
            "invoice_documents",
            "invoice_lines",
            "invoice_item_service_links",
            "draft_discount_actions",
            "document_number_counters",
            "service_record_charge_links",
            "payment_attempts",
            "unverified_payment_claims",
            "payment_receipts",
            "receipt_allocations",
            "financial_adjustments",
            "clinic_payment_refunds",
            "clinic_insurers",
            "invoice_insurer_expectations",
            "insurer_settlement_entries",
            "clinic_service_referrers",
            "revenue_share_allocations",
            "revenue_share_adjustments",
            "inventory_items",
            "inventory_lots",
            "stock_movements",
            "inventory_lot_state_events",
            "service_item_suggestions",
            "appointment_waitlist_entries",
            "staff_practitioner_resources",
            "staff_service_links",
            "departments",
            "department_service_links",
            "department_practitioner_links",
            "role_permission_scopes",
            "reception_groups",
            "reception_group_appointments",
            "clinic_visits",
            "visit_appointments",
            "appointment_arrival_facts",
            "service_records",
            "service_record_practitioners",
            "historical_appointment_entries",
            "service_availability_guards",
            "online_availability_closures",
            "patient_operational_notes",
            "patient_note_actions",
            "staff_tag_catalog",
            "patient_staff_tags",
            "patient_identity_reviews",
            "ledger_receipt_guards",
            "receipt_beneficiary_attributions",
        ],
    )
    await conn.execute(
        "SELECT set_config('app.ops_migration_tables', $1, false)",
        json.dumps([r["relname"] for r in known]),
    )


def ops_schema_authorized(*, explicit: bool = False) -> bool:
    if explicit:
        return True
    mode = (os.environ.get("CLINIC_OPS_SCHEMA_MODE") or "").strip().lower()
    return mode in {"disposable", "1", "true", "yes"}


async def apply_ops_schema(
    conn: asyncpg.Connection, *, explicit: bool = False
) -> dict:
    """Apply proposed ops packages. Requires SET ROLE db_migrator (or superuser)."""
    if not ops_schema_authorized(explicit=explicit):
        raise RuntimeError(
            "Ops schema apply refused: set CLINIC_OPS_SCHEMA_MODE=disposable "
            "or pass explicit=True for an isolated harness only."
        )
    # Idempotency marker
    exists = await conn.fetchval(
        "SELECT to_regclass('public.invoice_documents') IS NOT NULL"
    )
    if exists:
        courses = await apply_treatment_courses_schema(conn, explicit=explicit)
        dashboard = await apply_dashboard_r2_schema(conn, explicit=explicit)
        return {
            "applied": False,
            "reason": "already_present",
            "treatment_courses": courses,
            "dashboard_r2": dashboard,
        }

    applied: list[str] = []
    for _step, files in APPLY_STEPS:
        for name in files:
            if name in SKIP:
                continue
            path = CORRECTED / name if (CORRECTED / name).exists() else EXTRACTED / name
            if name == "13.sql":
                await _prepare_rls_tables(conn)
            await _exec_script(conn, path.read_text(encoding="utf-8"))
            applied.append(name)
    courses = await apply_treatment_courses_schema(conn, explicit=explicit)
    dashboard = await apply_dashboard_r2_schema(conn, explicit=explicit)
    return {
        "applied": True,
        "files": applied,
        "skipped": sorted(SKIP),
        "treatment_courses": courses,
        "dashboard_r2": dashboard,
    }


async def apply_treatment_courses_schema(
    conn: asyncpg.Connection, *, explicit: bool = False
) -> dict:
    """Apply disposable treatment-course / rolling-recall DDL (Task 34 R2 §9).

    Idempotent via ``ops_treatment_courses_schema_marker``. Requires disposable
    mode. Does not create official Alembic revisions.
    """
    if not ops_schema_authorized(explicit=explicit):
        raise RuntimeError(
            "Treatment courses schema apply refused: set CLINIC_OPS_SCHEMA_MODE=disposable "
            "or pass explicit=True for an isolated harness only."
        )
    marker = await conn.fetchval(
        "SELECT to_regclass('public.ops_treatment_courses_schema_marker') IS NOT NULL"
    )
    if marker:
        return {"applied": False, "reason": "already_present"}
    # Prefer services + patient_profiles present (ops or baseline); fail soft if missing.
    services_ok = await conn.fetchval(
        "SELECT to_regclass('public.services') IS NOT NULL"
    )
    if not services_ok:
        return {"applied": False, "reason": "services_missing"}
    path = EXTRACTED / "proposed_treatment_courses.sql"
    await _exec_script(conn, path.read_text(encoding="utf-8"))
    return {
        "applied": True,
        "file": "proposed_treatment_courses.sql",
        "label": "treatment_courses_r2_v1",
    }


async def apply_dashboard_r2_schema(
    conn: asyncpg.Connection, *, explicit: bool = False
) -> dict:
    """Apply disposable dashboard R2 DDL (job_title, reviews, notifications).

    Idempotent via ``ops_dashboard_r2_schema_marker`` and IF NOT EXISTS guards.
    Does not create official Alembic revisions.
    """
    if not ops_schema_authorized(explicit=explicit):
        raise RuntimeError(
            "Dashboard R2 schema apply refused: set CLINIC_OPS_SCHEMA_MODE=disposable "
            "or pass explicit=True for an isolated harness only."
        )
    marker = await conn.fetchval(
        "SELECT to_regclass('public.ops_dashboard_r2_schema_marker') IS NOT NULL"
    )
    if marker:
        # Re-run ALTER IF NOT EXISTS so upgrades remain safe on older markers.
        await conn.execute(
            "ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS job_title text"
        )
        return {"applied": False, "reason": "already_present"}
    staff_ok = await conn.fetchval(
        "SELECT to_regclass('public.staff_profiles') IS NOT NULL"
    )
    appts_ok = await conn.fetchval(
        "SELECT to_regclass('public.appointments') IS NOT NULL"
    )
    if not staff_ok or not appts_ok:
        return {"applied": False, "reason": "baseline_tables_missing"}
    path = EXTRACTED / "proposed_dashboard_r2.sql"
    await _exec_script(conn, path.read_text(encoding="utf-8"))
    return {
        "applied": True,
        "file": "proposed_dashboard_r2.sql",
        "label": "dashboard_r2_v1",
    }
