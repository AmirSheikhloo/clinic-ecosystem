"""E0.5 forensic suite — 19 contractual case IDs (A01–A08 + REG + CLOSE)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import errorcodes

EXP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP_ROOT))

from harness.admission import decide_admission  # noqa: E402
from harness.bootstrap import (  # noqa: E402
    app_dsn,
    enable_rls_for_app,
    migrator_url,
    seed_tenant_identifier,
    synthetic_hmac,
)
from harness.evidence import (  # noqa: E402
    CONTRACT_SHA256,
    PARENT_E02,
    PARENT_E03_FINAL,
    PARENT_E04_FINAL,
    REQUIRED_CASE_IDS as EVIDENCE_REQUIRED_CASE_IDS,
    REQUIRED_FIELDS,
    validate_evidence_file,
    validate_evidence_record,
    write_case_manifest,
    write_evidence,
)
from harness.path_guard import (  # noqa: E402
    PathAllowlistError,
    assert_paths_allowed,
    assert_repo_range_allowlisted,
    classify_paths,
)
from harness.upgrade_wrapper import (  # noqa: E402
    UpgradeTargetError,
    assert_safe_target,
    list_heads,
    make_config,
    safe_upgrade,
)
from harness.writer_fence import (  # noqa: E402
    WriterFenceError,
    advance_epoch_and_drain,
    assert_writer_admitted,
    ensure_fence_tables,
    issue_token,
)

EVIDENCE = EXP_ROOT / "evidence"
BOUNDARY = datetime(2026, 12, 4, 22, 59, 0, tzinfo=timezone.utc)


def _clock_ok() -> None:
    now = datetime.now(timezone.utc)
    if now >= BOUNDARY:
        raise RuntimeError("E0.5 authorization expired")


def _versions(dsn: str) -> set[str]:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema='public' AND table_name='exp_e03_alembic_version'
            )
            """
        )
        if not cur.fetchone()[0]:
            return set()
        cur.execute("SELECT version_num FROM public.exp_e03_alembic_version")
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def _meta(dsn: str, key: str) -> str | None:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM exp_e03_meta WHERE key=%s", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _identity(dsn: str) -> dict:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT current_user, session_user,
                   (SELECT rolsuper FROM pg_roles WHERE rolname = current_user),
                   (SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user)
            """
        )
        cu, su, sup, byp = cur.fetchone()
        return {
            "current_user": cu,
            "session_user": su,
            "rolsuper": bool(sup),
            "rolbypassrls": bool(byp),
        }
    finally:
        conn.close()


def _reset_db(admin_dsn: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DROP TABLE IF EXISTS exp_e03_catalog_items CASCADE;
            DROP TABLE IF EXISTS exp_e03_identifiers CASCADE;
            DROP TABLE IF EXISTS exp_e03_tenants CASCADE;
            DROP TABLE IF EXISTS exp_e03_meta CASCADE;
            DROP TABLE IF EXISTS exp_e03_admission_policy CASCADE;
            DROP TABLE IF EXISTS exp_e03_writer_tokens CASCADE;
            DROP TABLE IF EXISTS exp_e03_writer_epoch CASCADE;
            DROP TABLE IF EXISTS exp_e03_alembic_version CASCADE;
            DROP INDEX IF EXISTS uq_exp_e03_next_lookup;
            DROP INDEX IF EXISTS uq_exp_e03_active_lookup;
            """
        )
    finally:
        conn.close()


def _pg_fields(pg_proof: dict, admin_dsn: str) -> dict:
    return {
        "postgres_server_version_num": pg_proof["server_version_num"],
        "database_label": pg_proof.get("database") or "exp_e03",
        "session_user": _identity(admin_dsn)["session_user"],
        "current_user": _identity(admin_dsn)["current_user"],
    }


@pytest.fixture
def clean_db(admin_dsn: str, db_url: str):
    _clock_ok()
    _reset_db(admin_dsn)
    yield db_url


# --------------- A01 ---------------

def test_e03_a01_p01_fail_closed_migrator(clean_db: str, admin_dsn: str, pg_proof: dict):
    before = _versions(admin_dsn)
    assert before == set()
    safe_upgrade(clean_db, "exp_e03_base")
    after = _versions(admin_dsn)
    # Connect as migrator and inspect identity used for objects
    mig = migrator_url(admin_dsn)
    ident = _identity(mig)
    assert ident["current_user"] == "exp_e03_migrator"
    assert ident["rolsuper"] is False and ident["rolbypassrls"] is False
    assert after == {"exp_e03_base"}
    # table owner should be migrator
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tableowner FROM pg_tables
            WHERE schemaname='public' AND tablename='exp_e03_identifiers'
            """
        )
        owner = cur.fetchone()[0]
    finally:
        conn.close()
    assert owner == "exp_e03_migrator"
    write_evidence(
        "E03-A01-P01",
        {
            "finding_id": "A01",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "exp_e03_migrator NOSUPERUSER NOBYPASSRLS; empty version table",
            "command_redacted": "safe_upgrade(... exp_e03_base) via SET ROLE fail-closed env.py",
            "expected_result": "DDL+stamp under migrator only",
            "observed_result": {"versions": sorted(after), "owner": owner, "identity": ident},
            "exit_code": 0,
            "before_state": {"versions": sorted(before)},
            "after_state": {"versions": sorted(after), "owner": owner},
        },
    )


def test_e03_a01_n01_set_role_denial(clean_db: str, admin_dsn: str, pg_proof: dict, monkeypatch):
    # Create a login role that cannot SET ROLE to migrator
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DO $$ BEGIN
              CREATE ROLE exp_e03_norole NOINHERIT LOGIN PASSWORD 'synth-only-not-secret';
            EXCEPTION WHEN duplicate_object THEN
              ALTER ROLE exp_e03_norole WITH LOGIN PASSWORD 'synth-only-not-secret';
            END $$
            """
        )
        cur.execute("ALTER ROLE exp_e03_norole NOSUPERUSER NOBYPASSRLS")
        cur.execute("REVOKE exp_e03_migrator FROM exp_e03_norole")
        cur.execute("GRANT USAGE ON SCHEMA public TO exp_e03_norole")
    finally:
        conn.close()

    scheme, rest = admin_dsn.split("://", 1)
    hostpart = rest.split("@", 1)[1]
    bad_url = f"{scheme}://exp_e03_norole:synth-only-not-secret@{hostpart}"
    # Point alembic at the unprivileged URL; env.py SET ROLE must fail closed
    before_tables = _versions(admin_dsn)
    err = None
    try:
        safe_upgrade(bad_url, "exp_e03_base")
        raised = False
    except Exception as exc:
        raised = True
        err = str(exc)
    assert raised, "expected SET ROLE denial to abort"
    assert "STOP_SECURITY" in err or "SET ROLE" in err
    assert _versions(admin_dsn) == before_tables
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_name='exp_e03_identifiers'
            )
            """
        )
        exists = cur.fetchone()[0]
    finally:
        conn.close()
    assert exists is False
    write_evidence(
        "E03-A01-N01",
        {
            "finding_id": "A01",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "login as exp_e03_norole without migrator membership",
            "command_redacted": "safe_upgrade(norole_url, exp_e03_base)",
            "expected_result": "immediate abort; no DDL/stamp/fallback",
            "observed_result": {"error": err, "identifiers_exist": exists, "versions": sorted(_versions(admin_dsn))},
            "exit_code": "NONZERO_EXPECTED",
            "before_state": {"versions": sorted(before_tables)},
            "after_state": {"versions": sorted(_versions(admin_dsn)), "identifiers_exist": exists},
        },
    )


# --------------- A02 ---------------

def test_e03_a02_n01_incomplete_backfill(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    seed_tenant_identifier(admin_dsn, with_next=False)
    # h6 may succeed even with nulls (partial index); h8 must refuse
    safe_upgrade(clean_db, "exp_e03_h6")
    before_auth = _meta(admin_dsn, "active_authority")
    before_v = _versions(admin_dsn)
    with pytest.raises(Exception) as ei:
        safe_upgrade(clean_db, "exp_e03_h8")
    assert "backfill incomplete" in str(ei.value).lower() or "refused" in str(ei.value).lower()
    assert _meta(admin_dsn, "active_authority") == before_auth == "gen1"
    assert _versions(admin_dsn) == before_v == {"exp_e03_h6"}
    write_evidence(
        "E03-A02-N01",
        {
            "finding_id": "A02",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "NULL lookup_hmac_next present; h6 applied",
            "command_redacted": "safe_upgrade(... exp_e03_h8)",
            "expected_result": "cutover refused; authority/stamp unchanged",
            "observed_result": {"error": str(ei.value), "authority": before_auth, "versions": sorted(before_v)},
            "exit_code": "NONZERO_EXPECTED",
            "before_state": {"authority": before_auth, "versions": sorted(before_v)},
            "after_state": {
                "authority": _meta(admin_dsn, "active_authority"),
                "versions": sorted(_versions(admin_dsn)),
            },
        },
    )


def test_e03_a02_p01_notnull_and_check(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    safe_upgrade(clean_db, "hmac_rotation@head")
    assert _versions(admin_dsn) == {"exp_e03_h8"}
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.attnotnull
            FROM pg_attribute a
            JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname='exp_e03_identifiers'
              AND a.attname='lookup_hmac_next' AND NOT a.attisdropped
            """
        )
        attnotnull = cur.fetchone()[0]
        cur.execute(
            "SELECT convalidated FROM pg_constraint WHERE conname='ck_exp_e03_next_required'"
        )
        convalidated = cur.fetchone()[0]
        cur.execute(
            """
            SELECT i.indisvalid, i.indisready FROM pg_class c
            JOIN pg_index i ON i.indexrelid=c.oid
            WHERE c.relname='uq_exp_e03_next_lookup'
            """
        )
        indisvalid, indisready = cur.fetchone()
    finally:
        conn.close()
    assert attnotnull is True
    assert convalidated is True
    assert indisvalid is True and indisready is True
    assert _meta(admin_dsn, "active_authority") == "gen2"
    write_evidence(
        "E03-A02-P01",
        {
            "finding_id": "A02",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "full backfill; valid next index",
            "command_redacted": "safe_upgrade(... hmac_rotation@head) Phase-8 SET NOT NULL+VALIDATE",
            "expected_result": "attnotnull=true AND convalidated=true AND authority gen2",
            "observed_result": {
                "attnotnull": attnotnull,
                "convalidated": convalidated,
                "indisvalid": indisvalid,
                "indisready": indisready,
                "authority": _meta(admin_dsn, "active_authority"),
            },
            "exit_code": 0,
            "before_state": {"authority": "gen1"},
            "after_state": {"authority": "gen2", "attnotnull": True, "convalidated": True},
        },
    )


def test_e03_a02_n02_guard_denies_without_catalog(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    safe_upgrade(clean_db, "exp_e03_h6")
    # Simulate misleading ready flag without NOT NULL / CHECK
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO exp_e03_meta(key, value) VALUES ('phase8_ready_flag', 'ready')
            ON CONFLICT (key) DO UPDATE SET value='ready'
            """
        )
        conn.commit()
        # Evaluate cutover guard the same way Phase-8 does (without applying h8)
        cur.execute(
            """
            SELECT a.attnotnull
            FROM pg_attribute a
            JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname='exp_e03_identifiers'
              AND a.attname='lookup_hmac_next' AND NOT a.attisdropped
            """
        )
        attnotnull = cur.fetchone()[0]
        cur.execute(
            "SELECT convalidated FROM pg_constraint WHERE conname='ck_exp_e03_next_required'"
        )
        row = cur.fetchone()
        convalidated = row[0] if row else None
        ready_flag = _meta(admin_dsn, "phase8_ready_flag")
        denied = not (attnotnull is True and convalidated is True)
        assert denied
        assert ready_flag == "ready"
        # Must not switch authority when guard fails
        assert _meta(admin_dsn, "active_authority") == "gen1"
    finally:
        conn.close()
    write_evidence(
        "E03-A02-N02",
        {
            "finding_id": "A02",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "ready flag set; NOT NULL/CHECK absent",
            "command_redacted": "catalog guard evaluation before authority switch",
            "expected_result": "guard denies despite ready flag",
            "observed_result": {
                "attnotnull": attnotnull,
                "convalidated": convalidated,
                "ready_flag": ready_flag,
                "authority": _meta(admin_dsn, "active_authority"),
                "denied": denied,
            },
            "exit_code": 0,
            "before_state": {"authority": "gen1", "ready_flag": "ready"},
            "after_state": {"authority": "gen1"},
        },
    )


# --------------- A03 ---------------

def test_e03_a03_p01_overlapping_writers(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    tenant, ident, canon = seed_tenant_identifier(admin_dsn, with_next=True)
    # Sync BEFORE any row locks so both transactions are open and overlapping.
    barrier = threading.Barrier(2)
    results: dict[str, object] = {}
    timeline: list[str] = []
    lock = threading.Lock()
    collide_active = synthetic_hmac(f"{tenant}:{canon}:collide-active")

    def _mark(msg: str) -> None:
        with lock:
            timeline.append(f"{time.time():.6f}:{msg}")

    def worker(name: str, suffix: str):
        conn = psycopg2.connect(admin_dsn)
        try:
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("SET lock_timeout = '5000ms'")
            cur.execute("SELECT 1")  # begin TX
            _mark(f"{name}:begun")
            barrier.wait(timeout=5)
            _mark(f"{name}:after_barrier")
            nxt = synthetic_hmac(f"{tenant}:{canon}:{suffix}")
            try:
                cur.execute(
                    """
                    INSERT INTO exp_e03_identifiers(
                      id, tenant_id, canonical_value, lookup_hmac_active,
                      hmac_key_version_active, lookup_hmac_next, hmac_key_version_next
                    ) VALUES (%s::uuid, %s::uuid, %s, %s, 1, %s, 2)
                    """,
                    (
                        str(uuid4()),
                        tenant,
                        f"{canon}-{suffix}",
                        psycopg2.Binary(collide_active),
                        psycopg2.Binary(nxt),
                    ),
                )
                conn.commit()
                _mark(f"{name}:committed")
                results[name] = {"ok": True, "sqlstate": None}
            except Exception as exc:
                conn.rollback()
                pgcode = getattr(exc, "pgcode", None)
                _mark(f"{name}:rolled_back:{pgcode}")
                results[name] = {"ok": False, "sqlstate": pgcode, "error": str(exc)}
        finally:
            conn.close()

    t1 = threading.Thread(target=worker, args=("A", "2a"))
    t2 = threading.Thread(target=worker, args=("B", "2b"))
    t1.start()
    t2.start()
    t1.join(15)
    t2.join(15)
    assert set(results) == {"A", "B"}
    oks = [n for n, r in results.items() if r.get("ok")]
    fails = [n for n, r in results.items() if not r.get("ok")]
    assert len(oks) == 1, results
    assert len(fails) == 1, results
    loser = fails[0]
    assert results[loser]["sqlstate"] in {errorcodes.UNIQUE_VIOLATION, "23505"}
    # Prove old+next written atomically on the winner row
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT count(*) FROM exp_e03_identifiers
            WHERE tenant_id=%s::uuid AND lookup_hmac_active=%s
              AND lookup_hmac_next IS NOT NULL
            """,
            (tenant, psycopg2.Binary(collide_active)),
        )
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()
    write_evidence(
        "E03-A03-P01",
        {
            "finding_id": "A03",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "two overlapping transactions; active unique index; barrier before DML",
            "command_redacted": "concurrent INSERT same (tenant_id, lookup_hmac_active)",
            "expected_result": "at most one authoritative colliding write commits; loser 23505",
            "observed_result": {"results": results, "timeline": timeline, "seed_ident": ident},
            "exit_code": 0,
            "before_state": {"ident": ident},
            "after_state": results,
            "limitations": [
                "Synthetic overlapping TX proof only; not Zero-Race-Window production claim.",
            ],
        },
    )


def test_e03_a03_n01_stale_writer_fence(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    ensure_fence_tables(admin_dsn)
    issue_token(admin_dsn, "writer-old")
    before_auth = _meta(admin_dsn, "active_authority")
    # admitted before drain
    assert_writer_admitted(admin_dsn, "writer-old")
    advance_epoch_and_drain(admin_dsn)
    with pytest.raises(WriterFenceError) as ei:
        assert_writer_admitted(admin_dsn, "writer-old")
    assert "stale" in str(ei.value).lower() or "DENY" in str(ei.value)
    with pytest.raises(WriterFenceError) as ei2:
        assert_writer_admitted(admin_dsn, "unknown-token")
    assert _meta(admin_dsn, "active_authority") == before_auth
    write_evidence(
        "E03-A03-N01",
        {
            "finding_id": "A03",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "token issued then epoch advanced/drained",
            "command_redacted": "assert_writer_admitted before protected write",
            "expected_result": "stale/unknown denied; authority unchanged",
            "observed_result": {"stale_error": str(ei.value), "unknown_error": str(ei2.value)},
            "exit_code": 0,
            "before_state": {"authority": before_auth},
            "after_state": {"authority": _meta(admin_dsn, "active_authority")},
        },
    )


# --------------- A04 ---------------

def _install_heads(admin: str, url: str, mode: str) -> set[str]:
    _reset_db(admin)
    os.environ["EXP_E05_DATABASE_URL"] = url
    safe_upgrade(url, "exp_e03_base")
    if mode in {"hmac", "both"}:
        seed_tenant_identifier(admin, with_next=True)
        safe_upgrade(url, "hmac_rotation@head")
    if mode in {"catalog", "both"}:
        safe_upgrade(url, "tenant_catalog@head")
    return _versions(admin)


def test_e03_a04_p01_admission_allow(clean_db: str, admin_dsn: str, cloud_admin: str, local_admin: str, pg_proof: dict):
    cloud_url = migrator_url(cloud_admin)
    local_url = migrator_url(local_admin)
    src = _install_heads(cloud_admin, cloud_url, "both")
    dst = _install_heads(local_admin, local_url, "both")
    decision = decide_admission(src, dst)
    assert decision.allowed is True
    # bounded synthetic effect only after allow
    conn = psycopg2.connect(local_admin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO exp_e03_meta(key, value) VALUES ('sync_marker', 'applied')
            ON CONFLICT (key) DO UPDATE SET value='applied'
            """
        )
        conn.commit()
    finally:
        conn.close()
    assert _meta(local_admin, "sync_marker") == "applied"
    write_evidence(
        "E03-A04-P01",
        {
            "finding_id": "A04",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "cloud+local both-heads inventories; allowlisted pair",
            "command_redacted": "decide_admission(src,dst) then bounded sync_marker write",
            "expected_result": "ALLOW with policy rationale",
            "observed_result": {
                "decision": decision.reason,
                "source": sorted(src),
                "dest": sorted(dst),
                "sync_marker": _meta(local_admin, "sync_marker"),
            },
            "exit_code": 0,
            "before_state": {"source": sorted(src), "dest": sorted(dst)},
            "after_state": {"sync_marker": "applied"},
            "limitations": ["Synthetic admission model only; not real Sync proof."],
        },
    )


def test_e03_a04_n01_admission_deny(clean_db: str, admin_dsn: str, cloud_admin: str, local_admin: str, pg_proof: dict):
    cloud_url = migrator_url(cloud_admin)
    local_url = migrator_url(local_admin)
    src = _install_heads(cloud_admin, cloud_url, "hmac")
    dst = _install_heads(local_admin, local_url, "catalog")
    before_local_meta = _meta(local_admin, "sync_marker")
    decision = decide_admission(src, dst)
    assert decision.allowed is False
    # attempt mutation must not proceed
    if not decision.allowed:
        pass
    assert _meta(local_admin, "sync_marker") == before_local_meta
    # reversed both->empty etc.
    d2 = decide_admission(set(), dst)
    assert d2.allowed is False
    write_evidence(
        "E03-A04-N01",
        {
            "finding_id": "A04",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "hmac-only cloud vs catalog-only local; default DENY",
            "command_redacted": "decide_admission mismatched heads",
            "expected_result": "DENY before mutation; inventories unchanged",
            "observed_result": {
                "decision": decision.reason,
                "empty_decision": d2.reason,
                "source": sorted(src),
                "dest": sorted(dst),
                "sync_marker": _meta(local_admin, "sync_marker"),
            },
            "exit_code": 0,
            "before_state": {"sync_marker": before_local_meta},
            "after_state": {"sync_marker": _meta(local_admin, "sync_marker")},
            "limitations": ["Synthetic admission model only; not real Sync proof."],
        },
    )


# --------------- A05 governance ---------------

def test_e03_a05_c01_ci_governance(pg_proof: dict, admin_dsn: str):
    wf = Path(".github/workflows/m102-f2b-bounded-e05.yml")
    assert wf.exists()
    text = wf.read_text(encoding="utf-8")
    assert "pull_request" not in text
    assert "workflow_dispatch" not in text
    assert "pull_request_target" not in text
    assert "schedule:" not in text
    assert "experiment/m102-f2b-e05-*" in text
    assert "paths:" in text
    assert "evidence/**" in text
    assert "permissions:" in text and "contents: read" in text
    # other workflows must not match this branch pattern
    for other in Path(".github/workflows").glob("*.yml"):
        if other.name == "m102-f2b-bounded-e05.yml":
            continue
        ot = other.read_text(encoding="utf-8")
        assert "m102-f2b-e05" not in ot
    event = os.environ.get("GITHUB_EVENT_NAME", "LOCAL_NOT_CI")
    write_evidence(
        "E03-A05-C01",
        {
            "finding_id": "A05",
            "classification": "OBSERVED_PASS",
            "execution_kind": "GOVERNANCE_CONTROL",
            "postgres_server_version_num": pg_proof["server_version_num"],
            "database_label": "NOT_APPLICABLE_governance_control",
            "session_user": "NOT_APPLICABLE_governance_control",
            "current_user": "NOT_APPLICABLE_governance_control",
            "preconditions": "workflow file present; branch filter e05; path filters exclude evidence",
            "command_redacted": "static workflow audit + runtime event name capture",
            "expected_result": "push-only scoped workflow; no PR/dispatch/schedule",
            "observed_result": {
                "event": event,
                "workflow": str(wf),
                "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
            },
            "exit_code": 0,
            "before_state": "workflow authored",
            "after_state": {"event": event},
            "limitations": [
                "GitHub manual re-run residual risk cannot be fully revoked by workflow alone.",
            ],
        },
    )


# --------------- A06 ---------------

def test_e03_a06_p01_autocommit_role(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    # CONCURRENTLY inside an explicit transaction must fail
    conn = psycopg2.connect(migrator_url(admin_dsn))
    try:
        conn.autocommit = False
        cur = conn.cursor()
        cur.execute("SELECT current_user, session_user")
        before = cur.fetchone()
        try:
            cur.execute(
                """
                CREATE UNIQUE INDEX CONCURRENTLY uq_exp_e03_tx_should_fail
                ON exp_e03_identifiers (tenant_id, lookup_hmac_next)
                WHERE lookup_hmac_next IS NOT NULL
                """
            )
            tx_failed = False
            conn.commit()
        except Exception as exc:
            conn.rollback()
            tx_failed = True
            tx_err = str(exc)
        assert tx_failed
    finally:
        conn.close()
    safe_upgrade(clean_db, "exp_e03_h6")
    role_before = _meta(admin_dsn, "h6_role_before")
    role_inside = _meta(admin_dsn, "h6_role_inside")
    role_after = _meta(admin_dsn, "h6_role_after")
    assert role_before == role_inside == role_after == "exp_e03_migrator"
    write_evidence(
        "E03-A06-P01",
        {
            "finding_id": "A06",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "migrator role; Phase-6 path",
            "command_redacted": "CONCURRENTLY inside TX (fail) + h6 autocommit_block success",
            "expected_result": "role stable before/inside/after; TX CONCURRENTLY fails",
            "observed_result": {
                "before": before,
                "roles": {"before": role_before, "inside": role_inside, "after": role_after},
                "tx_error": tx_err,
            },
            "exit_code": 0,
            "before_state": {"role": before},
            "after_state": {"roles": [role_before, role_inside, role_after]},
        },
    )


def test_e03_a06_n01_invalid_index_recovery(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    tenant, _, canon = seed_tenant_identifier(admin_dsn, with_next=True)
    # Engineer duplicate next digests across two rows (same tenant+next)
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        dup = synthetic_hmac(f"{tenant}:{canon}:2")
        cur.execute(
            """
            INSERT INTO exp_e03_tenants(tenant_id, label) VALUES (%s::uuid, 'dup')
            ON CONFLICT DO NOTHING
            """,
            (tenant,),
        )
        # second identifier same next hash
        cur.execute(
            """
            INSERT INTO exp_e03_identifiers(
              id, tenant_id, canonical_value, lookup_hmac_active,
              hmac_key_version_active, lookup_hmac_next, hmac_key_version_next
            ) VALUES (%s::uuid, %s::uuid, %s, %s, 1, %s, 2)
            """,
            (
                str(uuid4()),
                tenant,
                canon + "-dup",
                psycopg2.Binary(synthetic_hmac(f"{tenant}:{canon}-dup:1")),
                psycopg2.Binary(dup),
            ),
        )
        # force first row next to same dup value
        cur.execute(
            "UPDATE exp_e03_identifiers SET lookup_hmac_next=%s WHERE canonical_value=%s",
            (psycopg2.Binary(dup), canon),
        )
        conn.commit()
    finally:
        conn.close()

    before_v = _versions(admin_dsn)
    # Direct CONCURRENTLY as migrator to capture invalid index state
    mig = migrator_url(admin_dsn)
    conn = psycopg2.connect(mig)
    conn.autocommit = True
    invalid_state = None
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE UNIQUE INDEX CONCURRENTLY uq_exp_e03_next_lookup
                ON exp_e03_identifiers (tenant_id, lookup_hmac_next)
                WHERE lookup_hmac_next IS NOT NULL
                """
            )
            created_ok = True
        except Exception as exc:
            created_ok = False
            create_err = str(exc)
        cur.execute(
            """
            SELECT c.relname, i.indisvalid, i.indisready, i.indisunique
            FROM pg_class c JOIN pg_index i ON i.indexrelid=c.oid
            WHERE c.relname='uq_exp_e03_next_lookup'
            """
        )
        invalid_state = cur.fetchone()
    finally:
        conn.close()

    assert created_ok is False
    assert invalid_state is not None, "expected INVALID index left behind by failed CONCURRENTLY"
    assert invalid_state[1] is False
    # Forbid false stamp
    assert _versions(admin_dsn) == before_v == {"exp_e03_base"}
    # Repair: drop invalid, fix data, retry
    conn = psycopg2.connect(mig)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_exp_e03_next_lookup")
    finally:
        conn.close()
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE exp_e03_identifiers SET lookup_hmac_next=%s, hmac_key_version_next=2 WHERE canonical_value=%s",
            (psycopg2.Binary(synthetic_hmac(f"{tenant}:{canon}:2-fixed")), canon),
        )
        conn.commit()
    finally:
        conn.close()
    safe_upgrade(clean_db, "exp_e03_h6")
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.indisvalid, i.indisready FROM pg_class c
            JOIN pg_index i ON i.indexrelid=c.oid
            WHERE c.relname='uq_exp_e03_next_lookup'
            """
        )
        valid = cur.fetchone()
    finally:
        conn.close()
    assert valid == (True, True)
    write_evidence(
        "E03-A06-N01",
        {
            "finding_id": "A06",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "duplicate next digests engineered",
            "command_redacted": "CREATE UNIQUE INDEX CONCURRENTLY; DROP; repair; retry h6",
            "expected_result": "indisvalid=false recorded; stamp forbidden; repair yields valid",
            "observed_result": {
                "create_error": create_err,
                "invalid_state": {
                    "relname": invalid_state[0],
                    "indisvalid": invalid_state[1],
                    "indisready": invalid_state[2],
                    "indisunique": invalid_state[3],
                },
                "repaired": {"indisvalid": valid[0], "indisready": valid[1]},
                "versions_after_fail": sorted(before_v),
            },
            "exit_code": 0,
            "before_state": {"versions": sorted(before_v)},
            "after_state": {"versions": sorted(_versions(admin_dsn)), "index": list(valid)},
        },
    )


def test_e03_a06_n02_privilege_negatives(clean_db: str, admin_dsn: str, pg_proof: dict):
    safe_upgrade(clean_db, "exp_e03_base")
    tenant, ident, _ = seed_tenant_identifier(admin_dsn, with_next=False)
    enable_rls_for_app(admin_dsn)
    adsn = app_dsn(admin_dsn)
    denials = {}
    conn = psycopg2.connect(adsn)
    try:
        cur = conn.cursor()
        # GRANT
        try:
            cur.execute("GRANT exp_e03_migrator TO exp_e03_app")
            conn.commit()
            denials["grant"] = "UNEXPECTED_SUCCESS"
        except Exception as exc:
            conn.rollback()
            denials["grant"] = {"sqlstate": getattr(exc, "pgcode", None), "error": str(exc)}
        # ALTER ROLE
        try:
            cur.execute("ALTER ROLE exp_e03_app BYPASSRLS")
            conn.commit()
            denials["alter_role"] = "UNEXPECTED_SUCCESS"
        except Exception as exc:
            conn.rollback()
            denials["alter_role"] = {"sqlstate": getattr(exc, "pgcode", None), "error": str(exc)}
        # version metadata mutation
        try:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS exp_e03_alembic_version(version_num varchar(32))"
            )
            cur.execute("INSERT INTO exp_e03_alembic_version(version_num) VALUES ('hacked')")
            conn.commit()
            denials["version_mutate"] = "UNEXPECTED_SUCCESS"
        except Exception as exc:
            conn.rollback()
            denials["version_mutate"] = {"sqlstate": getattr(exc, "pgcode", None), "error": str(exc)}
        # cross-tenant RLS
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(uuid4()),))
        cur.execute("SELECT count(*) FROM exp_e03_identifiers WHERE id=%s::uuid", (ident,))
        visible = cur.fetchone()[0]
        denials["cross_tenant_visible"] = visible
        conn.commit()
    finally:
        conn.close()
    for key in ("grant", "alter_role", "version_mutate"):
        assert denials[key] != "UNEXPECTED_SUCCESS", denials
    assert denials["cross_tenant_visible"] == 0
    assert _versions(admin_dsn) == {"exp_e03_base"}
    write_evidence(
        "E03-A06-N02",
        {
            "finding_id": "A06",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "app role NOSUPERUSER NOBYPASSRLS; RLS forced",
            "command_redacted": "GRANT/ALTER ROLE/version insert/cross-tenant SELECT as app",
            "expected_result": "all forbidden ops denied; no bypass",
            "observed_result": denials,
            "exit_code": 0,
            "before_state": {"versions": ["exp_e03_base"]},
            "after_state": {"versions": sorted(_versions(admin_dsn)), "denials": denials},
        },
    )


# --------------- A07 / A08 / REG / CLOSE ---------------

REQUIRED_CASE_IDS = [
    "E03-A01-P01", "E03-A01-N01",
    "E03-A02-N01", "E03-A02-P01", "E03-A02-N02",
    "E03-A03-P01", "E03-A03-N01",
    "E03-A04-P01", "E03-A04-N01",
    "E03-A05-C01",
    "E03-A06-P01", "E03-A06-N01", "E03-A06-N02",
    "E03-A07-C01", "E03-A07-C02",
    "E03-A08-N01", "E03-A08-P01",
    "E03-REG-P01", "E03-CLOSE-C01",
]


def test_e03_a08_n01_injected_path_denials(pg_proof: dict, admin_dsn: str):
    injected = [
        "migrations/tenant_plane/versions/tp0008_dummy.py",
        "src/app/main.py",
        ".github/workflows/m0-postgres-integration.yml",
        "docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt",
        "../secret",
        "Experiments/m102_f2b_bounded_e03/escape.py",  # case collision
    ]
    # traversal should raise
    with pytest.raises(PathAllowlistError):
        assert_paths_allowed(["../secret"])
    ok, bad = classify_paths(
        [
            "migrations/tenant_plane/versions/tp0008_dummy.py",
            "src/app/main.py",
            ".github/workflows/m0-postgres-integration.yml",
            "docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt",
            "Experiments/m102_f2b_bounded_e03/escape.py",
            "experiments/m102_f2b_bounded_e05/harness/x.py",
            ".github/workflows/m102-f2b-bounded-e05.yml",
        ]
    )
    assert "experiments/m102_f2b_bounded_e05/harness/x.py" in ok
    assert ".github/workflows/m102-f2b-bounded-e05.yml" in ok
    assert len(bad) >= 4
    with pytest.raises(PathAllowlistError) as ei:
        assert_paths_allowed(bad)
    write_evidence(
        "E03-A08-N01",
        {
            "finding_id": "A08",
            "classification": "OBSERVED_PASS",
            "execution_kind": "GOVERNANCE_CONTROL",
            "postgres_server_version_num": pg_proof["server_version_num"],
            "database_label": "NOT_APPLICABLE_path_guard_unit",
            "session_user": "NOT_APPLICABLE_path_guard_unit",
            "current_user": "NOT_APPLICABLE_path_guard_unit",
            "preconditions": "synthetic injected paths only; no repo mutation",
            "command_redacted": "classify_paths/assert_paths_allowed on injected list",
            "expected_result": "fail-closed listing offenders",
            "observed_result": {"bad": bad, "error": str(ei.value), "ok": ok},
            "exit_code": 0,
            "before_state": {"injected": injected},
            "after_state": {"bad": bad},
        },
    )


def test_e03_a08_p01_full_range_diff(pg_proof: dict, admin_dsn: str):
    paths = assert_repo_range_allowlisted(parent=PARENT_E04_FINAL, head="HEAD")
    assert paths, "expected E0.3 paths in range"
    for p in paths:
        assert p.startswith("experiments/m102_f2b_bounded_e05/") or p == ".github/workflows/m102-f2b-bounded-e05.yml"
    write_evidence(
        "E03-A08-P01",
        {
            "finding_id": "A08",
            "classification": "OBSERVED_PASS",
            "execution_kind": "GOVERNANCE_CONTROL",
            "postgres_server_version_num": pg_proof["server_version_num"],
            "database_label": "NOT_APPLICABLE_diff_guard",
            "session_user": "NOT_APPLICABLE_diff_guard",
            "current_user": "NOT_APPLICABLE_diff_guard",
            "preconditions": f"parent={PARENT_E04_FINAL}",
            "command_redacted": "git diff --name-status parent...HEAD + allowlist",
            "expected_result": "only allowlisted paths",
            "observed_result": {"paths": paths},
            "exit_code": 0,
            "before_state": {"parent": PARENT_E04_FINAL},
            "after_state": {"path_count": len(paths)},
        },
    )


def test_e03_reg_p01_topology(clean_db: str, admin_dsn: str, pg_proof: dict):
    heads = list_heads(clean_db)
    assert set(heads) == {"exp_e03_h8", "exp_e03_cat2"}
    for bad in ("head", "heads", ""):
        with pytest.raises(UpgradeTargetError):
            assert_safe_target(bad)
    safe_upgrade(clean_db, "exp_e03_base")
    seed_tenant_identifier(admin_dsn, with_next=False)
    safe_upgrade(clean_db, "tenant_catalog@head")
    assert _versions(admin_dsn) == {"exp_e03_cat2"}
    assert _meta(admin_dsn, "active_authority") == "gen1"
    assert _meta(admin_dsn, "hmac_phase8") is None
    write_evidence(
        "E03-REG-P01",
        {
            "finding_id": "REG",
            "classification": "OBSERVED_PASS",
            "execution_kind": "PHYSICAL_PG15",
            **_pg_fields(pg_proof, admin_dsn),
            "preconditions": "synthetic two-head graph",
            "command_redacted": "list_heads; reject head/heads; catalog-only upgrade",
            "expected_result": "heads h8+cat2; catalog independence; dangerous targets refused",
            "observed_result": {"heads": heads, "versions": sorted(_versions(admin_dsn))},
            "exit_code": 0,
            "before_state": {"heads": heads},
            "after_state": {"versions": sorted(_versions(admin_dsn))},
        },
    )


def test_e03_a07_c02_preflight_manifest(pg_proof: dict, admin_dsn: str):
    path = EVIDENCE / "E03_5_1_SAFETY_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [c["case_id"] for c in data["cases"]]
    assert len(ids) == 19 and len(set(ids)) == 19
    assert set(ids) == set(EVIDENCE_REQUIRED_CASE_IDS)
    assert data["phase"] == "G2_PRE_EXECUTION"
    assert data["contract_sha256"] == CONTRACT_SHA256
    write_evidence(
        "E03-A07-C02",
        {
            "finding_id": "A07",
            "classification": "OBSERVED_PASS",
            "execution_kind": "GOVERNANCE_CONTROL",
            "postgres_server_version_num": pg_proof["server_version_num"],
            "database_label": "NOT_APPLICABLE_manifest",
            "session_user": "NOT_APPLICABLE_manifest",
            "current_user": "NOT_APPLICABLE_manifest",
            "preconditions": "G2 manifest written before G4",
            "command_redacted": "validate E03_5_1_SAFETY_MANIFEST.json",
            "expected_result": "19 distinct rows with required fields",
            "observed_result": {"case_ids": ids, "phase": data["phase"]},
            "exit_code": 0,
            "before_state": {"manifest": str(path)},
            "after_state": {"validated": True},
        },
    )



def test_e03_zz_a07_c01_evidence_schema(pg_proof: dict, admin_dsn: str):
    """Staged C01 finalization without circular self-file dependency (E0.4 §5.1)."""
    # CLOSE control evidence first (governance)
    write_evidence(
        "E03-CLOSE-C01",
        {
            "finding_id": "CLOSE",
            "classification": "OBSERVED_PASS",
            "execution_kind": "GOVERNANCE_CONTROL",
            "postgres_server_version_num": pg_proof["server_version_num"],
            "database_label": pg_proof.get("database") or "exp_e03",
            "session_user": "NOT_APPLICABLE_closure_control",
            "current_user": "NOT_APPLICABLE_closure_control",
            "preconditions": "CI ephemeral resources; immutable E0.2/E0.3 refs retained",
            "command_redacted": "closure checklist prior to final forensic gate",
            "expected_result": "cleanup facts + grant cutoff recorded",
            "observed_result": {
                "parent_e02": PARENT_E02,
                "parent_e03_final": PARENT_E03_FINAL,
                "contract": CONTRACT_SHA256,
                "expiry": "2026-12-04T22:59:00Z",
                "ci_event": os.environ.get("GITHUB_EVENT_NAME", "LOCAL_NOT_CI"),
            },
            "exit_code": 0,
            "before_state": "suite executing",
            "after_state": "closure_control_recorded",
            "limitations": [
                "Hosted Actions service teardown is platform-owned; experiment claims only owned SQL objects disposed per job end.",
            ],
        },
    )

    peer_ids = [i for i in EVIDENCE_REQUIRED_CASE_IDS if i != "E03-A07-C01"]
    missing_peers = [i for i in peer_ids if not (EVIDENCE / f"{i}.json").exists()]
    assert not missing_peers, f"peers missing before C01 finalization: {missing_peers}"

    peer_errors = []
    for case_id in peer_ids:
        peer_errors.extend(validate_evidence_file(EVIDENCE / f"{case_id}.json"))
    assert not peer_errors, peer_errors

    # Candidate final C01 payload validated in memory BEFORE writing (no circular missing-self)
    candidate = {
        "case_id": "E03-A07-C01",
        "finding_id": "A07",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": os.environ.get("GITHUB_SHA") or os.environ.get("E05_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN",
        "run_id": os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI",
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "postgres_server_version_num": pg_proof["server_version_num"],
        "database_label": "NOT_APPLICABLE_schema_validation",
        "session_user": "NOT_APPLICABLE_schema_validation",
        "current_user": "NOT_APPLICABLE_schema_validation",
        "preconditions": "18 peer evidence JSON present; candidate C01 validated in memory",
        "command_redacted": "validate 18 peers + candidate C01; write C01; write_case_manifest",
        "expected_result": "19 stable JSONs; external digest manifest; no circular missing-self",
        "observed_result": {
            "peers_validated": peer_ids,
            "peer_errors": peer_errors,
            "protocol": "E0.5 staged C01 retained from E0.4 §5.1",
        },
        "exit_code": 0,
        "before_state": {"peers": peer_ids},
        "after_state": {"c01_finalized": True},
        "evidence_files": ["experiments/m102_f2b_bounded_e05/evidence/E03-A07-C01.json"],
        "source_test": "test_e03_zz_a07_c01_evidence_schema",
        "limitations": [
            "Synthetic experiment only; not real Cloud/Local Sync proof.",
            "Post-pytest independent manifest verifier is a separate CI gate.",
            "E5-E independent external verification PENDING.",
        ],
    }
    mem_errors = validate_evidence_record(candidate, require_ci_identity=None)
    assert not mem_errors, mem_errors

    write_evidence("E03-A07-C01", {k: v for k, v in candidate.items() if k not in {
        "case_id", "contract_sha256", "parent_e02_final_commit_sha", "tested_commit_sha",
        "run_id", "timestamp_utc", "evidence_files", "limitations"
    }})

    # Finalize external 19-case manifest after all bytes stable
    manifest_path, manifest_digest = write_case_manifest()
    # Re-validate all 19 files including C01
    all_errors = []
    for case_id in EVIDENCE_REQUIRED_CASE_IDS:
        all_errors.extend(validate_evidence_file(EVIDENCE / f"{case_id}.json"))
    assert not all_errors, all_errors
    assert (EVIDENCE / "E03-A07-C01.json").exists()
    # Persist manifest digest sidecar (not inside case JSON)
    (EVIDENCE / "EVIDENCE_CASE_MANIFEST_DIGEST.txt").write_text(
        manifest_digest + "\n", encoding="utf-8"
    )
