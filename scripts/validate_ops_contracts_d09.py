#!/usr/bin/env python3
"""Disposable PG15 Appendix D.3 validation for ACR-D0.9 proposed SQL.

PO-authorized disposable validation only — does NOT land Alembic revisions.
Reuses bootstrap/topology patterns from the prior D0.10 harness.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import asyncpg

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from tests.integration.alembic_runner import upgrade_tenant_plane  # noqa: E402
from tests.integration.conftest import (  # noqa: E402
    TENANT_SCHEMA_PRIVS_SQL,
    DbEndpoint,
    _apply_db_script,
    _bootstrap_cloud,
)


def _split_sql_statements(script: str) -> list[str]:
    """Split on ';' outside dollar-quotes, strings, and -- / /* */ comments."""
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


def _is_executable_sql(stmt: str) -> bool:
    lines = []
    for line in stmt.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(stripped)
    body = " ".join(lines).strip()
    return bool(body) and body != ";"


async def _exec_script(conn: asyncpg.Connection, script: str) -> None:
    for stmt in _split_sql_statements(script):
        body = stmt.strip()
        if body and _is_executable_sql(body):
            await conn.execute(body)

VALID = REPO / "docs" / "validation" / "d010"
EXTRACTED = VALID / "d09_extracted"
CORRECTED = VALID / "d09_corrected"
EVIDENCE = VALID / "d09_evidence"

# Topological order per ACR-D0.9 §11 (+ FK prerequisites discovered in execution).
# Arrival composite UQs must precede waitlist converted_appointment FK.
# Inventory tables must precede Appendix B.3 inventory triggers in 16.sql.
# Merge package 12 skipped — SOURCE_REQUIRED (D09-12).
APPLY_STEPS: list[tuple[str, list[str]]] = [
    ("step3_eligibility", ["05.sql"]),
    ("step3_departments", ["06.sql"]),
    ("step4_scopes", ["07.sql"]),
    ("step4_notes", ["10.sql"]),
    ("step4_identity_reviews", ["11.sql"]),
    ("step5_arrival", ["08.sql"]),
    ("step5_waitlist", ["04.sql"]),
    ("step5_online_close", ["09.sql"]),
    ("step7_ledger_core", ["00.sql", "01.sql", "02.sql"]),
    ("step7_b2_receipt_guards", ["15.sql"]),
    ("step7_b1_invoice_guards", ["14.sql"]),
    ("step9_inventory", ["03.sql"]),
    ("step7_b3_crossrow", ["16.sql"]),
    ("step7_b4_misc", ["17.sql"]),
    ("appendix_a_rls", ["13.sql"]),
]

SKIPPED = [
    {
        "file": "12.sql",
        "reason": "D09-12 / §10.3 person_merge_events SOURCE_REQUIRED (v1.3 alias)",
        "status": "BLOCKED",
    }
]


@dataclass
class Suite:
    cases: list[dict[str, Any]] = field(default_factory=list)
    apply_log: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)

    def case(self, name: str, ok: bool, detail: str = "", status: str | None = None) -> None:
        st = status or ("PASS" if ok else "FAIL")
        self.cases.append({"name": name, "ok": ok, "status": st, "detail": detail})
        print(st, name, detail[:200] if detail else "")


def load_sql(directory: Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


async def apply_file(
    conn: asyncpg.Connection, directory: Path, name: str, step: str, suite: Suite
) -> bool:
    body = load_sql(directory, name)
    try:
        await _exec_script(conn, body)
        suite.apply_log.append({"step": step, "file": name, "ok": True})
        print(f"  APPLY OK [{step}] {name}")
        return True
    except Exception as exc:  # noqa: BLE001
        suite.apply_log.append(
            {"step": step, "file": name, "ok": False, "error": str(exc)}
        )
        print(f"  APPLY FAIL [{step}] {name}: {exc}")
        return False


async def apply_all(
    conn: asyncpg.Connection, directory: Path, suite: Suite, label: str
) -> bool:
    ok_all = True
    for step, files in APPLY_STEPS:
        for name in files:
            if name == "13.sql":
                await prepare_rls_setting(conn)
            src = directory if (directory / name).exists() else EXTRACTED
            if not await apply_file(conn, src, name, f"{label}/{step}", suite):
                ok_all = False
    for skip in SKIPPED:
        suite.apply_log.append(
            {
                "step": "skip",
                "file": skip["file"],
                "ok": False,
                "skipped": True,
                "reason": skip["reason"],
            }
        )
        suite.case(f"skip_{skip['file']}", True, skip["reason"], status="BLOCKED")
    return ok_all


async def prepare_rls_setting(conn: asyncpg.Connection) -> None:
    """Appendix A requires app.ops_migration_tables JSON array of table names."""
    tables = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
          AND c.relname NOT IN (
            SELECT tablename FROM pg_tables
            WHERE schemaname='public' AND tablename IN (
              SELECT unnest(ARRAY[
                'tenant_registry','tenant_persons','person_identifiers','person_phones',
                'patient_profiles','staff_profiles','user_accounts','permission_catalog_snapshots',
                'tenant_roles','role_permission_assignments','user_role_assignments',
                'tenant_governance_assignments','services','bookable_resources',
                'service_resource_requirements','appointments','appointment_resource_allocations',
                'hold_expiry_work_items','idempotency_records','outbox_messages','inbox_messages',
                'sync_sequence_counters','audit_entries','alembic_version_tp'
              ])
            )
          )
        ORDER BY 1
        """
    )
    # Simpler: collect known ops tables that exist
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
    names = [r["relname"] for r in known]
    await conn.execute(
        "SELECT set_config('app.ops_migration_tables', $1, false)",
        json.dumps(names),
    )


def lineage_report() -> dict[str, Any]:
    versions = sorted(
        p.name
        for p in (REPO / "migrations" / "tenant_plane" / "versions").glob("tp*.py")
    )
    return {
        "baseline_commit": "8309f2a044e944123ddb1f49a8bad1255e4ce2e0",
        "acr_d09_path": "docs/architecture_change_records/ACR-D0.9-COMPLETE-OPERATIONS-CONTRACTS.md",
        "acr_d09_sha256": "7171bfc10589410a60d857b5b14814f2475d4412d78071eb7bfedc7955465b40",
        "official_tp_on_disk_development": versions,
        "official_head": "tp0007",
        "main_lineage": "None→tp0001→…→tp0007 (no tp0008+ on origin/main or development/clinic-operations)",
        "roadmap_candidate": {
            "file": "uploads/MASTER_EXECUTION_ROADMAP_v3.0.1_R4.16_fdc5.md",
            "status": "REVIEW CANDIDATE / NOT APPROVED",
            "protected_TP0011": "HMAC Phase-6 / atomic resource — do not repurpose for ops tables",
            "candidate_ops_alignment": "TP0012–TP0013 scheduling/waitlist; TP0015–TP0017 finance; TP0019 inventory (unapproved)",
            "f2b": "experimental branches only; TERMINAL FAILED E0.7; no official tp0008+",
        },
        "no_tp0008_plus_landed": True,
        "person_merge_skipped": True,
    }


async def smoke_behavioral(
    admin: DbEndpoint, passwords: dict[str, str], suite: Suite
) -> None:
    """Targeted positive/negative smoke after successful corrected apply."""
    from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
    from tests.integration.m1_seed import seed_scheduling_graph

    migrator = await asyncpg.connect(
        f"postgresql://{quote_plus('tp_migrator_login')}:{quote_plus(passwords['tp_migrator_login'])}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    app = await asyncpg.connect(
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(passwords['tp_app_login'])}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )
    try:
        await migrator.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(migrator)
        other = await seed_scheduling_graph(migrator)
        now = datetime.now(timezone.utc)

        # practitioner mapping
        staff_person = new_uuid7()
        staff_id = new_uuid7()
        pract = new_uuid7()
        mapping = new_uuid7()
        await migrator.execute(
            """
            INSERT INTO tenant_persons (
              id, tenant_id, first_name, last_name, birth_date, gender,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,'Dr','Map',NULL,NULL,1,$3,$3)
            """,
            staff_person,
            ids.tenant_id,
            now,
        )
        await migrator.execute(
            """
            INSERT INTO staff_profiles (
              id, tenant_id, person_id, staff_kind, is_active, created_at_utc
            ) VALUES ($1,$2,$3,'DOCTOR',TRUE,$4)
            """,
            staff_id,
            ids.tenant_id,
            staff_person,
            now,
        )
        await migrator.execute(
            """
            INSERT INTO bookable_resources (
              id, tenant_id, resource_type, resource_name, is_active, created_at_utc
            ) VALUES ($1,$2,'PRACTITIONER','Dr Map',TRUE,$3)
            """,
            pract,
            ids.tenant_id,
            now,
        )

        await app.execute("SET ROLE db_app_runtime")
        await app.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )

        # Check whether staff_practitioner_resources exists and is usable
        exists = await migrator.fetchval(
            "SELECT to_regclass('public.staff_practitioner_resources') IS NOT NULL"
        )
        if not exists:
            suite.case("eligibility_table_present", False, "table missing after apply")
            return

        # Inspect required columns dynamically
        cols = {
            r["column_name"]
            for r in await migrator.fetch(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='staff_practitioner_resources'
                """
            )
        }
        # Minimal insert based on D0.9 shape
        try:
            await app.execute(
                """
                INSERT INTO staff_practitioner_resources (
                  id, tenant_id, staff_profile_id, bookable_resource_id,
                  is_active, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,$3,$4,TRUE,$5,$5)
                """,
                mapping,
                ids.tenant_id,
                staff_id,
                pract,
                now,
            )
            suite.case("eligibility_mapping_insert", True, str(sorted(cols)))
        except Exception as exc:  # noqa: BLE001
            suite.case("eligibility_mapping_insert", False, str(exc))

        # RLS smoke on departments if present
        if await migrator.fetchval("SELECT to_regclass('public.departments') IS NOT NULL"):
            dept = new_uuid7()
            await app.execute(
                """
                INSERT INTO departments (
                  id, tenant_id, department_code, department_name, is_active,
                  aggregate_version, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,'GEN','General',TRUE,1,$3,$3)
                """,
                dept,
                ids.tenant_id,
                now,
            )
            await app.execute(
                "SELECT set_config('app.current_tenant_id', $1, false)", str(other.tenant_id)
            )
            cross = await app.fetchval(
                "SELECT count(*) FROM departments WHERE id=$1", dept
            )
            suite.case("rls_departments_cross_tenant_hidden", cross == 0)
            await app.execute(
                "SELECT set_config('app.current_tenant_id', '', false)"
            )
            bare = await app.fetchval("SELECT count(*) FROM departments")
            suite.case("rls_departments_no_tenant_fail_closed", bare == 0)
            await app.execute(
                "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
            )

        # Policy names on a new table
        if await migrator.fetchval(
            "SELECT to_regclass('public.invoice_documents') IS NOT NULL"
        ):
            pol = await migrator.fetch(
                """
                SELECT polname FROM pg_policy p
                JOIN pg_class c ON c.oid=p.polrelid
                WHERE c.relname='invoice_documents'
                """
            )
            names = {r["polname"] for r in pol}
            suite.case(
                "rls_invoice_policy_names",
                names
                >= {
                    "tenant_runtime_base",
                    "tenant_runtime_guard",
                    "tenant_migrator_maintenance",
                },
                str(names),
            )

        # Trigger presence samples
        for fn in (
            "ops_invoice_guard",
            "ops_receipt_allocation_reconcile",
            "ops_practitioner_mapping_guard",
            "ops_inventory_lot_guard",
            "ops_terminal_state_guard",
            "ops_appointment_lifecycle_facts_guard",
        ):
            present2 = await migrator.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname=$1)", fn
            )
            suite.case(f"function_present_{fn}", bool(present2))

        # Invoice DRAFT-only insert via runtime
        if await migrator.fetchval(
            "SELECT to_regclass('public.invoice_documents') IS NOT NULL"
        ):
            inv = new_uuid7()
            try:
                await app.execute(
                    """
                    INSERT INTO invoice_documents (
                      id, tenant_id, status, beneficiary_patient_id, currency_code,
                      aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES ($1,$2,'DRAFT',$3,'IRR',1,$4,$4)
                    """,
                    inv,
                    ids.tenant_id,
                    ids.patient_id,
                    now,
                )
                suite.case("invoice_draft_insert", True)
            except Exception as exc:  # noqa: BLE001
                # Column set may differ — capture for correction
                suite.case("invoice_draft_insert", False, str(exc)[:400])

            # Non-DRAFT insert should fail if guard installed
            bad = False
            try:
                await app.execute(
                    """
                    INSERT INTO invoice_documents (
                      id, tenant_id, status, beneficiary_patient_id, currency_code,
                      aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES ($1,$2,'POSTED',$3,'IRR',1,$4,$4)
                    """,
                    new_uuid7(),
                    ids.tenant_id,
                    ids.patient_id,
                    now,
                )
            except Exception:  # noqa: BLE001
                bad = True
            suite.case("invoice_rejects_non_draft_insert", bad)

        # Inventory FEFO index / table presence
        if await migrator.fetchval(
            "SELECT to_regclass('public.inventory_lots') IS NOT NULL"
        ):
            suite.case("inventory_lots_present", True)
            idx = await migrator.fetchval(
                "SELECT 1 FROM pg_indexes WHERE indexname='inventory_fefo_idx'"
            )
            suite.case("inventory_fefo_index_present", idx == 1)

        # Waitlist table + online closure present
        suite.case(
            "waitlist_present",
            await migrator.fetchval(
                "SELECT to_regclass('public.appointment_waitlist_entries') IS NOT NULL"
            ),
        )
        suite.case(
            "online_closures_present",
            await migrator.fetchval(
                "SELECT to_regclass('public.online_availability_closures') IS NOT NULL"
            ),
        )
        suite.case(
            "arrival_facts_present",
            await migrator.fetchval(
                "SELECT to_regclass('public.appointment_arrival_facts') IS NOT NULL"
            ),
        )
        suite.case(
            "service_records_present",
            await migrator.fetchval(
                "SELECT to_regclass('public.service_records') IS NOT NULL"
            ),
        )

        # Append-only: UPDATE payment_receipts should fail if never inserted — check trigger exists
        trig = await migrator.fetchval(
            """
            SELECT 1 FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid
            WHERE c.relname='invoice_documents' AND NOT t.tgisinternal
            LIMIT 1
            """
        )
        suite.case("invoice_guard_trigger_installed", trig == 1)

        # Direct SQL attack: cross-tenant insert should fail RLS WITH CHECK
        await app.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        forged = False
        try:
            await app.execute(
                """
                INSERT INTO departments (
                  id, tenant_id, department_code, department_name, is_active,
                  aggregate_version, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,'X','X',TRUE,1,$3,$3)
                """,
                new_uuid7(),
                other.tenant_id,
                now,
            )
        except Exception:  # noqa: BLE001
            forged = True
        suite.case("rls_rejects_forged_tenant_insert", forged)

    finally:
        await app.close()
        await migrator.close()


async def recreate_tenant_db(admin: DbEndpoint) -> None:
    aconn = await asyncpg.connect(admin.asyncpg_dsn())
    try:
        await aconn.execute(
            """
            SELECT pg_terminate_backend(pid) FROM pg_stat_activity
            WHERE datname='tenant_app' AND pid <> pg_backend_pid()
            """
        )
        await aconn.execute("DROP DATABASE IF EXISTS tenant_app")
        await aconn.execute('CREATE DATABASE "tenant_app"')
        await aconn.execute(
            "GRANT CONNECT ON DATABASE tenant_app TO tp_migrator_login, tp_app_login"
        )
        await aconn.execute("GRANT CREATE ON DATABASE tenant_app TO db_migrator")
        await aconn.execute("REVOKE CONNECT, TEMPORARY ON DATABASE tenant_app FROM PUBLIC")
    finally:
        await aconn.close()
    await _apply_db_script(admin, "tenant_app", TENANT_SCHEMA_PRIVS_SQL)


async def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    CORRECTED.mkdir(parents=True, exist_ok=True)
    suite = Suite(lineage=lineage_report())

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
        print("Upgrade to tp0007…")
        await asyncio.to_thread(upgrade_tenant_plane, migrator_url, "head")

        raw_ok = False
        conn = await asyncpg.connect(
            f"postgresql://{quote_plus('tp_migrator_login')}:"
            f"{quote_plus(passwords['tp_migrator_login'])}"
            f"@{admin.host}:{admin.port}/tenant_app"
        )
        try:
            await conn.execute("SET ROLE db_migrator")
            ver = await conn.fetchval(
                "SELECT version_num FROM alembic_meta.alembic_version_tp"
            )
            suite.case("lineage_head_tp0007", ver == "tp0007", str(ver))
            pg = await conn.fetchval("SHOW server_version")
            suite.case("postgres_15", str(pg).startswith("15."), str(pg))

            print("Applying RAW D0.9 extracted SQL (topological)…")
            raw_ok = await apply_all(conn, EXTRACTED, suite, "raw")
            suite.case("raw_d09_apply_all_non_skipped", raw_ok)
        finally:
            await conn.close()

        if raw_ok:
            print("Running behavioral suite on applied D0.9 schema…")
            await smoke_behavioral(admin, passwords, suite)
        else:
            suite.case("behavioral_skipped_due_to_apply_fail", False)

    except Exception as exc:  # noqa: BLE001
        suite.case("harness_fatal", False, f"{exc}\n{traceback.format_exc()}")
    finally:
        cloud.stop()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": suite.lineage,
        "apply_log": suite.apply_log,
        "cases": suite.cases,
        "skipped": SKIPPED,
        "summary": {
            "cases_passed": sum(1 for c in suite.cases if c["ok"] and c["status"] == "PASS"),
            "cases_failed": sum(1 for c in suite.cases if c["status"] == "FAIL"),
            "cases_blocked": sum(1 for c in suite.cases if c["status"] == "BLOCKED"),
            "apply_ok": sum(1 for a in suite.apply_log if a.get("ok")),
            "apply_fail": sum(
                1 for a in suite.apply_log if not a.get("ok") and not a.get("skipped")
            ),
            "apply_skipped": sum(1 for a in suite.apply_log if a.get("skipped")),
        },
    }
    out = EVIDENCE / "execution_evidence.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# ACR-D0.9 disposable PG15 execution evidence",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"ACR-D0.9 SHA-256: `{suite.lineage['acr_d09_sha256']}`",
        "",
        f"- Apply OK: {payload['summary']['apply_ok']}",
        f"- Apply FAIL: {payload['summary']['apply_fail']}",
        f"- Apply SKIPPED: {payload['summary']['apply_skipped']}",
        f"- Cases PASS/FAIL/BLOCKED: "
        f"{payload['summary']['cases_passed']}/"
        f"{payload['summary']['cases_failed']}/"
        f"{payload['summary']['cases_blocked']}",
        "",
        "## Apply log",
        "",
    ]
    for a in suite.apply_log:
        if a.get("skipped"):
            md_lines.append(f"- `BLOCKED` {a['file']} — {a.get('reason')}")
        elif a.get("ok"):
            md_lines.append(f"- `OK` [{a.get('step')}] {a['file']}")
        else:
            md_lines.append(
                f"- `FAIL` [{a.get('step')}] {a['file']} — {a.get('error','')[:300]}"
            )
    md_lines += ["", "## Cases", ""]
    for c in suite.cases:
        md_lines.append(
            f"- `{c['status']}` {c['name']}"
            + (f" — {c['detail'][:200]}" if c["detail"] else "")
        )
    (EVIDENCE / "execution_evidence.md").write_text("\n".join(md_lines) + "\n")
    print(json.dumps(payload["summary"], indent=2))
    print("Wrote", out)
    return 0 if payload["summary"]["apply_fail"] == 0 and payload["summary"]["cases_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
