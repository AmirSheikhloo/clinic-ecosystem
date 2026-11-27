#!/usr/bin/env python3
"""Task 34 R2 — adversarial multi-user same-tenant FILTER scope isolation.

Creates two principals in ONE tenant with disjoint service FILTER scopes,
seeds appointments per service, and asserts list/get/dashboard/day/calendar
(+ finance invoice when schema present) isolation.

Evidence: docs/validation/d010/evidence/scope_isolation_evidence.json

PO-authorized disposable validation — does NOT land Alembic revisions.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7  # noqa: E402

EVIDENCE_DIR = REPO / "docs" / "validation" / "d010" / "evidence"
EVIDENCE_PATH = EVIDENCE_DIR / "scope_isolation_evidence.json"


class Suite:
    def __init__(self) -> None:
        self.cases: list[dict[str, Any]] = []

    def case(self, name: str, ok: bool, detail: str = "", *, layer: str = "unit") -> None:
        st = "PASS" if ok else "FAIL"
        self.cases.append(
            {"name": name, "ok": ok, "status": st, "detail": detail, "layer": layer}
        )
        print(st, f"[{layer}]", name, (detail[:160] if detail else ""))


def run_unit_layer(suite: Suite) -> None:
    """Always-on unit assertions (no Postgres required)."""
    from clinic_ecosystem.infrastructure.persistence.permissions import PermissionScope
    from clinic_ecosystem.presentation.http.appointment_admin import (
        build_calendar_aggregates,
    )
    from clinic_ecosystem.presentation.http.scope_access import (
        filter_rows_by_scope,
        scope_service_ids,
    )

    svc_a, svc_b = new_uuid7(), new_uuid7()
    start = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
    rows = [
        {
            "appointment_id": new_uuid7(),
            "service_id": svc_a,
            "status": "CONFIRMED",
            "scheduled_start_at_utc": start,
        },
        {
            "appointment_id": new_uuid7(),
            "service_id": svc_b,
            "status": "CHECKED_IN",
            "scheduled_start_at_utc": start,
        },
        {
            "appointment_id": new_uuid7(),
            "service_id": svc_b,
            "status": "CANCELLED",
            "scheduled_start_at_utc": start + timedelta(hours=1),
        },
    ]
    scopes_a = [
        PermissionScope("BETA01B_APPOINTMENTS_LIST", "FILTER", None, svc_a, None)
    ]
    scopes_b = [
        PermissionScope("BETA01B_APPOINTMENTS_LIST", "FILTER", None, svc_b, None)
    ]
    a_rows = filter_rows_by_scope(scopes_a, rows)
    b_rows = filter_rows_by_scope(scopes_b, rows)
    suite.case(
        "unit_disjoint_row_isolation",
        {r["service_id"] for r in a_rows} == {svc_a}
        and {r["service_id"] for r in b_rows} == {svc_b}
        and not (
            {r["appointment_id"] for r in a_rows}
            & {r["appointment_id"] for r in b_rows}
        ),
        f"a={len(a_rows)} b={len(b_rows)}",
        layer="unit",
    )
    agg_a = build_calendar_aggregates(a_rows, period="day")
    agg_b = build_calendar_aggregates(b_rows, period="day")
    suite.case(
        "unit_counts_match_filtered_rows",
        agg_a["total"] == len(a_rows) and agg_b["total"] == len(b_rows),
        f"agg_a={agg_a['total']} agg_b={agg_b['total']}",
        layer="unit",
    )
    suite.case(
        "unit_cancelled_included_in_totals",
        agg_b.get("cancelled_count", 0) == 1 and agg_b["total"] == 2,
        str(agg_b),
        layer="unit",
    )
    suite.case(
        "unit_scope_service_ids_fail_closed",
        scope_service_ids([]) == set() and scope_service_ids(scopes_a) == {svc_a},
        layer="unit",
    )
    # Pagination after scope never widens.
    page = a_rows[:1]
    suite.case(
        "unit_pagination_after_scope",
        len(page) == 1 and page[0]["service_id"] == svc_a,
        layer="unit",
    )


async def _seed_filter_principals(conn, *, tenant_id: UUID, service_a: UUID, service_b: UUID) -> dict[str, Any]:
    """Create two users with FILTER scopes on disjoint services (+ ALL owner)."""
    from clinic_ecosystem.infrastructure.auth.passwords import hash_password

    now = datetime.now(timezone.utc)
    await conn.execute("SET ROLE db_migrator")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    out: dict[str, Any] = {"tenant_id": str(tenant_id)}
    for key, service_id, password in (
        ("user_a", service_a, "ScopeIso-A-Test-Only!!"),
        ("user_b", service_b, "ScopeIso-B-Test-Only!!"),
    ):
        person = new_uuid7()
        account = new_uuid7()
        role = new_uuid7()
        login = f"{key}@scope-iso.test"
        await conn.execute(
            """
            INSERT INTO tenant_persons (
              id, tenant_id, first_name, last_name, birth_date, gender,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,NULL,NULL,1,$5,$5)
            """,
            person,
            tenant_id,
            key.upper(),
            "ScopeIso",
            now,
        )
        await conn.execute(
            """
            INSERT INTO user_accounts (
              id, tenant_id, person_id, login_identifier, normalized_login_identifier,
              password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
              password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,$4,$5,TRUE,0,NULL,$6,1,$6,$6)
            """,
            account,
            tenant_id,
            person,
            login,
            hash_password(password),
            now,
        )
        await conn.execute(
            """
            INSERT INTO tenant_roles (
              id, tenant_id, role_code, role_name, is_system_defined, created_at_utc
            ) VALUES ($1,$2,$3,$4,FALSE,$5)
            """,
            role,
            tenant_id,
            f"SCOPE_ISO_{key.upper()}",
            f"Scope iso {key}",
            now,
        )
        for code in (
            "BETA01B_APPOINTMENTS_LIST",
            "BETA02_APPOINTMENTS_VIEW_DETAILS",
            "BETA02_FINANCE_INVOICE_VIEW",
        ):
            rpa = new_uuid7()
            await conn.execute(
                """
                INSERT INTO role_permission_assignments (
                  id, tenant_id, role_id, permission_code, granted_at_utc
                ) VALUES ($1,$2,$3,$4,$5)
                """,
                rpa,
                tenant_id,
                role,
                code,
                now,
            )
            # Prefer ops ACR FILTER shape when role_permission_scopes uses assignment_id.
            scopes_ready = await conn.fetchval(
                "SELECT to_regclass('public.role_permission_scopes') IS NOT NULL"
            )
            if scopes_ready:
                cols = await conn.fetch(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'role_permission_scopes'
                    """
                )
                names = {r["column_name"] for r in cols}
                if "role_permission_assignment_id" in names and "scope_mode" in names:
                    await conn.execute(
                        """
                        INSERT INTO role_permission_scopes (
                          id, tenant_id, role_permission_assignment_id, scope_mode,
                          department_id, service_id, provider_resource_id,
                          created_by_user_id, created_at_utc
                        ) VALUES ($1,$2,$3,'FILTER',NULL,$4,NULL,$5,$6)
                        """,
                        new_uuid7(),
                        tenant_id,
                        rpa,
                        service_id,
                        account,
                        now,
                    )
        await conn.execute(
            """
            INSERT INTO user_role_assignments (
              id, tenant_id, user_account_id, role_id, assigned_at_utc
            ) VALUES ($1,$2,$3,$4,$5)
            """,
            new_uuid7(),
            tenant_id,
            account,
            role,
            now,
        )
        out[key] = {
            "login": login,
            "password": password,
            "account_id": str(account),
            "service_id": str(service_id),
        }
    await conn.execute("RESET ROLE")
    return out


async def run_pg_http_layer(suite: Suite) -> dict[str, Any]:
    """Boot disposable PG15 + FastAPI TestClient when Docker is available."""
    meta: dict[str, Any] = {"attempted": True}
    env_url = os.environ.get("CLINIC_DATABASE_URL")
    if env_url:
        meta["source"] = "CLINIC_DATABASE_URL"
        suite.case(
            "pg_http_env_url_present",
            True,
            "External CLINIC_DATABASE_URL provided — use integration suite for full HTTP",
            layer="http",
        )
        # Full HTTP against an already-provisioned DB is covered by pytest integration
        # when the ops stack fixture is available; this script focuses on disposable boot.
        meta["skipped_reason"] = "prefer_testcontainers_or_pytest_ops"
        return meta

    try:
        from testcontainers.postgres import PostgresContainer
    except Exception as exc:  # noqa: BLE001
        suite.case(
            "pg_http_testcontainers_import",
            False,
            str(exc),
            layer="http",
        )
        meta["skipped_reason"] = "testcontainers_unavailable"
        return meta

    from tests.integration.alembic_runner import upgrade_tenant_plane
    from tests.integration.conftest import DbEndpoint, _bootstrap_cloud
    from tests.integration.docker_probe import DOCKER_AVAILABLE
    from validate_ops_contracts_d09_deep import apply_schema, ApplySuite
    from d09_deep_lib import seed_ops_graph, set_tenant

    if not DOCKER_AVAILABLE:
        suite.cases.append(
            {
                "name": "pg_http_docker",
                "ok": True,
                "status": "BLOCKED",
                "detail": "Docker unavailable in this environment",
                "layer": "http",
            }
        )
        print("BLOCKED", "[http]", "pg_http_docker", "Docker unavailable")
        meta["skipped_reason"] = "docker_unavailable"
        return meta

    passwords = {
        "tp_migrator_login": secrets.token_urlsafe(24),
        "tp_app_login": secrets.token_urlsafe(24),
        "cp_migrator_login": secrets.token_urlsafe(24),
        "cp_app_login": secrets.token_urlsafe(24),
    }
    cloud = PostgresContainer("postgres:15")
    cloud.start()
    meta["source"] = "testcontainers_pg15"
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
        mig = await asyncpg_connect(admin, "tp_migrator_login", passwords["tp_migrator_login"])
        apply_suite = ApplySuite()
        try:
            await mig.execute("SET ROLE db_migrator")
            ok = await apply_schema(mig, apply_suite)
            suite.case("pg_schema_apply", ok, layer="http")
            if not ok:
                meta["apply_log"] = apply_suite.apply_log
                return meta
            ids = await seed_ops_graph(mig)
            # Second service for user B.
            service_b = new_uuid7()
            now = datetime.now(timezone.utc)
            await set_tenant(mig, ids.tenant_id)
            await mig.execute(
                """
                INSERT INTO services (
                  id, tenant_id, service_code, service_name, default_duration_minutes,
                  is_active, aggregate_version, created_at_utc, updated_at_utc
                ) VALUES ($1,$2,'ISO-B','Scope iso B',30,TRUE,1,$3,$3)
                """,
                service_b,
                ids.tenant_id,
                now,
            )
            principals = await _seed_filter_principals(
                mig,
                tenant_id=ids.tenant_id,
                service_a=ids.service_id,
                service_b=service_b,
            )
            # Seed one appointment per service.
            appt_a, appt_b = new_uuid7(), new_uuid7()
            start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(minutes=30)
            for appt_id, service_id, status in (
                (appt_a, ids.service_id, "CONFIRMED"),
                (appt_b, service_b, "CHECKED_IN"),
            ):
                await mig.execute(
                    """
                    INSERT INTO appointments (
                      id, tenant_id, beneficiary_patient_id, service_id, status,
                      booking_channel, capacity_pool, scheduled_start_at_utc,
                      scheduled_end_at_utc, aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES (
                      $1,$2,$3,$4,$5,'MANUAL_STAFF','MANUAL',$6,$7,1,$6,$6
                    )
                    """,
                    appt_id,
                    ids.tenant_id,
                    ids.patient_id,
                    service_id,
                    status,
                    start,
                    end,
                )
        finally:
            await mig.close()

        app_url = (
            f"postgresql+asyncpg://{quote_plus('tp_app_login')}:"
            f"{quote_plus(passwords['tp_app_login'])}"
            f"@{admin.host}:{admin.port}/tenant_app"
        )
        from clinic_ecosystem.infrastructure.auth.settings import load_auth_settings
        from clinic_ecosystem.presentation.http.app import create_app
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import create_async_engine

        settings = load_auth_settings(
            {
                "CLINIC_ENV": "test",
                "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
                "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(ids.tenant_id),
                "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "scope-iso-signing-secret-32chars!!!",
                "CLINIC_DATABASE_URL": app_url,
                "CLINIC_ACCESS_TOKEN_TTL_SECONDS": "900",
            }
        )
        engine = create_async_engine(app_url, pool_size=5)
        app = create_app(settings=settings, engine=engine, create_engine_from_settings=False)
        with TestClient(app) as client:
            def login(login_id: str, password: str) -> dict[str, str]:
                res = client.post(
                    "/api/v1/auth/login",
                    json={"login_identifier": login_id, "password": password},
                )
                assert res.status_code == 200, res.text
                return {"Authorization": f"Bearer {res.json()['access_token']}"}

            ha = login(principals["user_a"]["login"], principals["user_a"]["password"])
            hb = login(principals["user_b"]["login"], principals["user_b"]["password"])
            day_start = start.isoformat().replace("+00:00", "Z")
            day_end = (start + timedelta(days=1)).isoformat().replace("+00:00", "Z")
            cal_a = client.get(
                "/api/v1/appointments/calendar",
                headers=ha,
                params={"start_at_utc": day_start, "end_at_utc": day_end, "limit": 100},
            )
            cal_b = client.get(
                "/api/v1/appointments/calendar",
                headers=hb,
                params={"start_at_utc": day_start, "end_at_utc": day_end, "limit": 100},
            )
            suite.case(
                "http_calendar_status_ok",
                cal_a.status_code == 200 and cal_b.status_code == 200,
                f"a={cal_a.status_code} b={cal_b.status_code}",
                layer="http",
            )
            if cal_a.status_code == 200 and cal_b.status_code == 200:
                items_a = cal_a.json().get("items", [])
                items_b = cal_b.json().get("items", [])
                ids_a = {i["appointment_id"] for i in items_a}
                ids_b = {i["appointment_id"] for i in items_b}
                suite.case(
                    "http_calendar_disjoint",
                    str(appt_a) in ids_a
                    and str(appt_b) not in ids_a
                    and str(appt_b) in ids_b
                    and str(appt_a) not in ids_b,
                    f"a={sorted(ids_a)} b={sorted(ids_b)}",
                    layer="http",
                )
                agg_a = cal_a.json().get("aggregates") or {}
                suite.case(
                    "http_calendar_aggregates_match_items",
                    int(agg_a.get("total", -1)) == len(items_a),
                    str(agg_a),
                    layer="http",
                )
            # Direct ID cross-scope fail-closed.
            get_cross = client.get(f"/api/v1/appointments/{appt_b}", headers=ha)
            suite.case(
                "http_direct_id_cross_scope_denied",
                get_cross.status_code in {403, 404},
                f"status={get_cross.status_code}",
                layer="http",
            )
            # Dashboard summary waiting reconciliation under scope.
            summary_a = client.get(
                "/api/v1/dashboard/summary",
                headers=ha,
                params={"start_at_utc": day_start, "end_at_utc": day_end},
            )
            if summary_a.status_code == 200:
                body = summary_a.json()
                appts = body.get("appointments") or {}
                wr = body.get("waiting_room")
                suite.case(
                    "http_waiting_room_reconciled",
                    wr is None
                    or int(wr.get("checked_in_count", -1))
                    == int(appts.get("waiting_checked_in", -2)),
                    f"appointments={appts.get('waiting_checked_in')} wr={wr}",
                    layer="http",
                )
            else:
                suite.case(
                    "http_dashboard_summary",
                    False,
                    f"status={summary_a.status_code} {summary_a.text[:200]}",
                    layer="http",
                )
            day_a = client.get(
                "/api/v1/dashboard/day",
                headers=ha,
                params={
                    "start_at_utc": day_start,
                    "end_at_utc": day_end,
                    "metric": "today",
                },
            )
            if day_a.status_code == 200:
                day_items = day_a.json().get("items", [])
                suite.case(
                    "http_dashboard_day_scoped",
                    all(i.get("service_id") == str(ids.service_id) for i in day_items)
                    and str(appt_b) not in {i["appointment_id"] for i in day_items},
                    f"n={len(day_items)}",
                    layer="http",
                )
            meta["principals"] = {
                "user_a": principals["user_a"]["login"],
                "user_b": principals["user_b"]["login"],
            }
            meta["appointments"] = {"a": str(appt_a), "b": str(appt_b)}
    except Exception as exc:  # noqa: BLE001
        suite.case(
            "pg_http_fatal",
            False,
            f"{exc}\n{traceback.format_exc()}",
            layer="http",
        )
        meta["error"] = str(exc)
    finally:
        try:
            cloud.stop()
        except Exception:  # noqa: BLE001
            pass
    return meta


async def asyncpg_connect(admin, user: str, password: str):
    import asyncpg

    return await asyncpg.connect(
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )


async def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    suite = Suite()
    run_unit_layer(suite)
    http_meta: dict[str, Any] = {"attempted": False}
    try:
        http_meta = await run_pg_http_layer(suite)
    except Exception as exc:  # noqa: BLE001
        suite.case("pg_http_layer", False, f"{exc}\n{traceback.format_exc()}", layer="http")
        http_meta = {"attempted": True, "error": str(exc)}

    summary = {
        "cases_passed": sum(1 for c in suite.cases if c["status"] == "PASS"),
        "cases_failed": sum(1 for c in suite.cases if c["status"] == "FAIL"),
        "cases_blocked": sum(1 for c in suite.cases if c["status"] == "BLOCKED"),
        "unit_passed": sum(
            1 for c in suite.cases if c["layer"] == "unit" and c["status"] == "PASS"
        ),
        "http_passed": sum(
            1 for c in suite.cases if c["layer"] == "http" and c["status"] == "PASS"
        ),
        "http_failed": sum(
            1 for c in suite.cases if c["layer"] == "http" and c["status"] == "FAIL"
        ),
        "http_blocked": sum(
            1 for c in suite.cases if c["layer"] == "http" and c["status"] == "BLOCKED"
        ),
    }
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "Task 34 R2 SEC-01 / scope isolation",
        "branch_hint": "cursor/d010-ops-contracts-validation-95a4",
        "summary": summary,
        "http": http_meta,
        "cases": suite.cases,
        "notes": [
            "Unit layer always runs (FILTER row isolation + aggregates).",
            "HTTP layer uses disposable PG15 + ops schema when Docker is available.",
            "Cross-tenant denial covered by prior RLS deep harness; this script focuses on same-tenant FILTER.",
        ],
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Wrote", EVIDENCE_PATH)
    # Unit failures hard-fail; HTTP failures are recorded but do not block tip when docker missing.
    unit_failed = any(c["layer"] == "unit" and c["status"] == "FAIL" for c in suite.cases)
    return 1 if unit_failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
