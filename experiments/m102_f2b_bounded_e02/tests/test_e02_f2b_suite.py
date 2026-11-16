"""E0.2 §5.2 synthetic F2-B feasibility suite — E02-F2B-01..14."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg2
import pytest
from alembic import command
from alembic.script import ScriptDirectory

EXP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP_ROOT))

from harness.bootstrap import (  # noqa: E402
    app_dsn,
    seed_tenant_identifier,
    synthetic_hmac,
)
from harness.upgrade_wrapper import (  # noqa: E402
    ALLOWED_TARGETS,
    UpgradeTargetError,
    assert_safe_target,
    list_heads,
    make_config,
    safe_upgrade,
)

EVIDENCE = EXP_ROOT / "evidence"
BOUNDARY = datetime(2026, 11, 23, 22, 59, 0, tzinfo=timezone.utc)


def _record(test_id: str, payload: dict) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{test_id}.json"
    payload = {
        **payload,
        "utc": datetime.now(timezone.utc).isoformat(),
        "test_id": test_id,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def _versions(dsn: str) -> set[str]:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema='public' AND table_name='exp_f2b_alembic_version'
            )
            """
        )
        if not cur.fetchone()[0]:
            return set()
        cur.execute("SELECT version_num FROM public.exp_f2b_alembic_version")
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def _meta(dsn: str, key: str) -> str | None:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM exp_f2b_meta WHERE key=%s", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _reset_db(admin_dsn: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DROP TABLE IF EXISTS exp_f2b_catalog_items CASCADE;
            DROP TABLE IF EXISTS exp_f2b_identifiers CASCADE;
            DROP TABLE IF EXISTS exp_f2b_tenants CASCADE;
            DROP TABLE IF EXISTS exp_f2b_meta CASCADE;
            DROP TABLE IF EXISTS exp_f2b_alembic_version CASCADE;
            DROP INDEX IF EXISTS uq_exp_f2b_next_lookup;
            DROP INDEX IF EXISTS uq_exp_f2b_active_lookup;
            """
        )
    finally:
        conn.close()


@pytest.fixture
def clean_db(admin_dsn: str, db_url: str):
    _reset_db(admin_dsn)
    yield db_url
    # leave final state for last evidence; next test resets


def test_e02_f2b_01_synthetic_graph_audit(db_url: str, pg_proof: str):
    heads = list_heads(db_url)
    expected = {"exp_f2b_h8", "exp_f2b_cat2"}
    assert set(heads) == expected
    cfg = make_config(db_url)
    script = ScriptDirectory.from_config(cfg)
    h6 = script.get_revision("exp_f2b_h6")
    cat1 = script.get_revision("exp_f2b_cat1")
    assert h6.down_revision == "exp_f2b_base"
    assert cat1.down_revision == "exp_f2b_base"
    assert "hmac_rotation" in (h6.branch_labels or set())
    assert "tenant_catalog" in (cat1.branch_labels or set())
    # no depends_on cross edges
    for rev in script.walk_revisions():
        assert not rev.dependencies
    path = _record(
        "E02-F2B-01",
        {"result": "PASS", "heads": heads, "pg_proof": pg_proof, "expected": sorted(expected)},
    )
    assert path.exists()


def test_e02_f2b_02_explicit_head_targeting(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    assert _versions(admin_dsn) == {"exp_f2b_base"}
    safe_upgrade(clean_db, "tenant_catalog@head")
    assert _versions(admin_dsn) == {"exp_f2b_cat2"}
    # idempotent re-entry
    safe_upgrade(clean_db, "tenant_catalog@head")
    assert _versions(admin_dsn) == {"exp_f2b_cat2"}
    _record("E02-F2B-02", {"result": "PASS", "versions": sorted(_versions(admin_dsn))})


def test_e02_f2b_03_dangerous_target_negatives(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    before_v = _versions(admin_dsn)
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM exp_f2b_tenants")
        before_t = cur.fetchone()[0]
    finally:
        conn.close()
    for bad in ("head", "heads", "", "unknown_rev", "tp0007"):
        with pytest.raises(UpgradeTargetError):
            assert_safe_target(bad)
        with pytest.raises(UpgradeTargetError):
            safe_upgrade(clean_db, bad)
    assert _versions(admin_dsn) == before_v
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM exp_f2b_tenants")
        assert cur.fetchone()[0] == before_t
    finally:
        conn.close()
    # read-only heads inspection still allowed
    assert set(list_heads(clean_db)) == {"exp_f2b_h8", "exp_f2b_cat2"}
    _record("E02-F2B-03", {"result": "PASS", "forbidden": ["head", "heads", "blank", "unknown"]})


def test_e02_f2b_04_version_table_state_machine(clean_db: str, admin_dsn: str):
    assert _versions(admin_dsn) == set()
    safe_upgrade(clean_db, "exp_f2b_base")
    assert _versions(admin_dsn) == {"exp_f2b_base"}
    assert len(_versions(admin_dsn)) == 1
    # HMAC-only head path: base + h6 + h8 => single head row exp_f2b_h8
    # seed next digests for h8
    seed_tenant_identifier(admin_dsn, with_next=True)
    safe_upgrade(clean_db, "hmac_rotation@head")
    assert _versions(admin_dsn) == {"exp_f2b_h8"}
    # reset and catalog-only
    _reset_db(admin_dsn)
    safe_upgrade(clean_db, "exp_f2b_base")
    safe_upgrade(clean_db, "tenant_catalog@head")
    assert _versions(admin_dsn) == {"exp_f2b_cat2"}
    # both heads
    _reset_db(admin_dsn)
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    safe_upgrade(clean_db, "hmac_rotation@head")
    safe_upgrade(clean_db, "tenant_catalog@head")
    both = _versions(admin_dsn)
    assert both == {"exp_f2b_h8", "exp_f2b_cat2"}
    assert len(both) == 2
    _record("E02-F2B-04", {"result": "PASS", "both_heads": sorted(both)})


def test_e02_f2b_05_catalog_only_independence(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=False)
    auth_before = _meta(admin_dsn, "active_authority")
    safe_upgrade(clean_db, "tenant_catalog@head")
    assert _meta(admin_dsn, "active_authority") == auth_before == "gen1"
    assert _meta(admin_dsn, "hmac_phase8") is None
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT count(*) FROM pg_indexes
            WHERE indexname = 'uq_exp_f2b_next_lookup'
            """
        )
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM exp_f2b_catalog_items")
        assert cur.fetchone()[0] == 0  # table exists
        cur.execute(
            """
            SELECT to_regclass('public.exp_f2b_catalog_items') IS NOT NULL
            """
        )
        assert cur.fetchone()[0] is True
        # negative: requiring phase8 meta must fail closed for catalog-only deploy marker
        cur.execute("SELECT value FROM exp_f2b_meta WHERE key='hmac_phase8'")
        assert cur.fetchone() is None
    finally:
        conn.close()
    _record("E02-F2B-05", {"result": "PASS", "authority": auth_before})


def test_e02_f2b_06_hmac_only_independence(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    safe_upgrade(clean_db, "hmac_rotation@head")
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT to_regclass('public.exp_f2b_catalog_items') IS NOT NULL"
        )
        assert cur.fetchone()[0] is False
        assert _meta(admin_dsn, "catalog_rev") is None
        assert _meta(admin_dsn, "hmac_phase8") == "cutover"
    finally:
        conn.close()
    _record("E02-F2B-06", {"result": "PASS"})


def test_e02_f2b_07_phase6_transaction_boundary(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=True)
    # Positive: h6 uses autocommit_block CONCURRENTLY
    safe_upgrade(clean_db, "exp_f2b_h6")
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.indisvalid, i.indisready, i.indisunique
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indexrelid
            WHERE c.relname = 'uq_exp_f2b_next_lookup'
            """
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] is True and row[1] is True and row[2] is True
    finally:
        conn.close()
    # Negative: CONCURRENTLY inside an explicit transaction must fail.
    neg = psycopg2.connect(admin_dsn)
    neg.autocommit = False
    try:
        cur = neg.cursor()
        cur.execute("SELECT 1")  # open a transaction block
        with pytest.raises(psycopg2.Error) as ei:
            cur.execute(
                """
                CREATE UNIQUE INDEX CONCURRENTLY uq_exp_f2b_should_fail
                ON exp_f2b_identifiers (tenant_id, canonical_value)
                """
            )
            neg.commit()
        neg.rollback()
        msg = str(ei.value).lower()
        assert "concur" in msg or "transaction" in msg
    finally:
        neg.close()
    assert _versions(admin_dsn) == {"exp_f2b_h6"}
    _record("E02-F2B-07", {"result": "PASS", "versions": sorted(_versions(admin_dsn))})


def test_e02_f2b_08_concurrent_index_failure_retry(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    # Same tenant, two rows, identical next digest => unique (tenant_id, next) collision.
    t1, i1 = seed_tenant_identifier(admin_dsn, with_next=False)
    collision = synthetic_hmac("collision-next")
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE exp_f2b_identifiers
            SET lookup_hmac_next=%s, hmac_key_version_next=2 WHERE id=%s
            """,
            (psycopg2.Binary(collision), i1),
        )
        i2 = str(uuid4())
        cur.execute(
            """
            INSERT INTO exp_f2b_identifiers(
              id, tenant_id, canonical_value, lookup_hmac_active,
              hmac_key_version_active, lookup_hmac_next, hmac_key_version_next
            ) VALUES (%s::uuid, %s::uuid, 'other', %s, 1, %s, 2)
            """,
            (
                i2,
                t1,
                psycopg2.Binary(synthetic_hmac("other-active")),
                psycopg2.Binary(collision),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(Exception):
        safe_upgrade(clean_db, "exp_f2b_h6")
    versions = _versions(admin_dsn)
    assert "exp_f2b_h6" not in versions
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.indisvalid FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid
            WHERE c.relname='uq_exp_f2b_next_lookup'
            """
        )
        row = cur.fetchone()
        if row is not None:
            assert row[0] is False
            cur.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_exp_f2b_next_lookup")
        cur.execute(
            """
            UPDATE exp_f2b_identifiers SET lookup_hmac_next=%s
            WHERE id=%s::uuid
            """,
            (psycopg2.Binary(synthetic_hmac("unique-next")), i2),
        )
    finally:
        conn.close()
    safe_upgrade(clean_db, "exp_f2b_h6")
    assert _versions(admin_dsn) == {"exp_f2b_h6"}
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.indisvalid FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid
            WHERE c.relname='uq_exp_f2b_next_lookup'
            """
        )
        assert cur.fetchone()[0] is True
    finally:
        conn.close()
    _record("E02-F2B-08", {"result": "PASS"})


def test_e02_f2b_09_phase8_guarded_cutover(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=False)  # incomplete backfill
    safe_upgrade(clean_db, "exp_f2b_h6")
    with pytest.raises(Exception):
        safe_upgrade(clean_db, "exp_f2b_h8")
    assert "exp_f2b_h8" not in _versions(admin_dsn)
    assert _meta(admin_dsn, "active_authority") == "gen1"
    # complete backfill and retry
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, tenant_id, canonical_value FROM exp_f2b_identifiers")
        for iid, tid, canon in cur.fetchall():
            nxt = synthetic_hmac(f"{tid}:{canon}:2")
            cur.execute(
                """
                UPDATE exp_f2b_identifiers
                SET lookup_hmac_next=%s, hmac_key_version_next=2 WHERE id=%s
                """,
                (psycopg2.Binary(nxt), iid),
            )
        conn.commit()
    finally:
        conn.close()
    safe_upgrade(clean_db, "exp_f2b_h8")
    assert _versions(admin_dsn) == {"exp_f2b_h8"}
    assert _meta(admin_dsn, "active_authority") == "gen2"
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.attnotnull, c.convalidated
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attname='lookup_hmac_next'
            WHERE c.conname='ck_exp_f2b_next_required'
            """
        )
        # CHECK validated; attnotnull may still be false (CHECK NOT NULL vs column NOT NULL)
        row = cur.fetchone()
        assert row is not None
        assert row[1] is True  # convalidated
    finally:
        conn.close()
    _record("E02-F2B-09", {"result": "PASS", "authority": _meta(admin_dsn, "active_authority")})


def test_e02_f2b_10_dual_write_active_uniqueness(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    t1, i1 = seed_tenant_identifier(admin_dsn, with_next=False)
    active = synthetic_hmac("dup-active")
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE exp_f2b_identifiers SET lookup_hmac_active=%s WHERE id=%s",
            (psycopg2.Binary(active), i1),
        )
        conn.commit()
        t2 = str(uuid4())
        i2 = str(uuid4())
        cur.execute(
            "INSERT INTO exp_f2b_tenants(tenant_id, label) VALUES (%s::uuid,'y')",
            (t2,),
        )
        # same tenant collision on active uniqueness
        with pytest.raises(psycopg2.Error):
            cur.execute(
                """
                INSERT INTO exp_f2b_identifiers(
                  id, tenant_id, canonical_value, lookup_hmac_active, hmac_key_version_active
                ) VALUES (%s::uuid, %s::uuid, 'z', %s, 1)
                """,
                (i2, t1, psycopg2.Binary(active)),
            )
            conn.commit()
        conn.rollback()
        # dual-write same canonical in one TX
        canon = "dual-canon"
        a = synthetic_hmac(f"{t1}:{canon}:1")
        n = synthetic_hmac(f"{t1}:{canon}:2")
        iid = str(uuid4())
        cur.execute("BEGIN")
        cur.execute(
            """
            INSERT INTO exp_f2b_identifiers(
              id, tenant_id, canonical_value, lookup_hmac_active, hmac_key_version_active,
              lookup_hmac_next, hmac_key_version_next
            ) VALUES (%s::uuid, %s::uuid, %s, %s, 1, %s, 2)
            """,
            (iid, t1, canon, psycopg2.Binary(a), psycopg2.Binary(n)),
        )
        cur.execute("COMMIT")
    finally:
        conn.close()
    # incomplete backfill blocks cutover (h6 ok, h8 fail)
    safe_upgrade(clean_db, "exp_f2b_h6")
    # leave one null next
    with pytest.raises(Exception):
        # ensure at least one null remains
        conn = psycopg2.connect(admin_dsn)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE exp_f2b_identifiers SET lookup_hmac_next=NULL, hmac_key_version_next=NULL
                WHERE id=%s
                """,
                (i1,),
            )
            conn.commit()
        finally:
            conn.close()
        safe_upgrade(clean_db, "exp_f2b_h8")
    _record("E02-F2B-10", {"result": "PASS"})


def test_e02_f2b_11_role_privilege_negatives(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    seed_tenant_identifier(admin_dsn, with_next=False)
    # Enable FORCE RLS for synthetic isolation demo
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE exp_f2b_identifiers ENABLE ROW LEVEL SECURITY")
        cur.execute("ALTER TABLE exp_f2b_identifiers FORCE ROW LEVEL SECURITY")
        cur.execute("DROP POLICY IF EXISTS exp_f2b_app_deny ON exp_f2b_identifiers")
        cur.execute(
            """
            CREATE POLICY exp_f2b_app_tenant ON exp_f2b_identifiers
            FOR ALL TO exp_f2b_app
            USING (false) WITH CHECK (false)
            """
        )
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON exp_f2b_identifiers TO exp_f2b_app")
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON exp_f2b_tenants TO exp_f2b_app")
        cur.execute("REVOKE ALL ON TABLE public.exp_f2b_alembic_version FROM PUBLIC")
        cur.execute("REVOKE ALL ON TABLE public.exp_f2b_alembic_version FROM exp_f2b_app")
        cur.execute("REVOKE ALL ON TABLE public.exp_f2b_meta FROM exp_f2b_app")
    finally:
        conn.close()

    adsn = app_dsn()
    aconn = psycopg2.connect(adsn)
    try:
        cur = aconn.cursor()
        # RLS USING false => zero rows (not necessarily an error).
        cur.execute("SELECT count(*) FROM exp_f2b_identifiers")
        assert cur.fetchone()[0] == 0
        aconn.rollback()
        with pytest.raises(psycopg2.Error):
            cur.execute("DELETE FROM exp_f2b_alembic_version")
            aconn.commit()
        aconn.rollback()
        with pytest.raises(psycopg2.Error):
            cur.execute(
                "INSERT INTO exp_f2b_identifiers(id, tenant_id, canonical_value, lookup_hmac_active, hmac_key_version_active) "
                "VALUES (%s::uuid, %s::uuid, 'nope', %s, 1)",
                (str(uuid4()), str(uuid4()), psycopg2.Binary(synthetic_hmac("x"))),
            )
            aconn.commit()
        aconn.rollback()
    finally:
        aconn.close()

    # bypassrls denied
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname='exp_f2b_app'"
        )
        assert cur.fetchone()[0] is False
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname='exp_f2b_migrator'"
        )
        assert cur.fetchone()[0] is False
    finally:
        conn.close()
    _record("E02-F2B-11", {"result": "PASS"})


def test_e02_f2b_12_cloud_local_mixed_state_simulation(clean_db: str, admin_dsn: str):
    """Two logical DBs on same disposable server simulate Cloud/Local pairs."""
    _ = clean_db
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_database()")
        main_db = cur.fetchone()[0]
        for name in ("exp_f2b_cloud", "exp_f2b_local"):
            cur.execute(f"DROP DATABASE IF EXISTS {name}")
            cur.execute(f"CREATE DATABASE {name}")
    finally:
        conn.close()

    def dsn_for(db: str) -> str:
        scheme, rest = admin_dsn.split("://", 1)
        creds, hostpart = rest.split("@", 1)
        host = hostpart.split("/")[0]
        return f"{scheme}://{creds}@{host}/{db}"

    def migrator_url_for(dsn: str) -> str:
        scheme, rest = dsn.split("://", 1)
        _, hostpart = rest.split("@", 1)
        return f"{scheme}://exp_f2b_migrator:synth-only-not-secret@{hostpart}"

    from harness.bootstrap import bootstrap_roles_and_rls

    results = {}
    pairs = (
        ("cloud_catalog", "exp_f2b_cloud", "tenant_catalog@head"),
        ("local_base", "exp_f2b_local", "exp_f2b_base"),
    )
    for label, db, target in pairs:
        dsn = dsn_for(db)
        bootstrap_roles_and_rls(dsn)
        url = migrator_url_for(dsn)
        safe_upgrade(url, "exp_f2b_base")
        if target != "exp_f2b_base":
            safe_upgrade(url, target)
        results[label] = sorted(_versions(dsn))
    assert results["cloud_catalog"] == ["exp_f2b_cat2"]
    assert results["local_base"] == ["exp_f2b_base"]
    _record(
        "E02-F2B-12",
        {
            "result": "PASS",
            "note": "synthetic dual-DB model only; production Sync/app UNVERIFIED",
            "states": results,
            "main_db": main_db,
        },
    )


def test_e02_f2b_13_interrupted_upgrade_semantics(clean_db: str, admin_dsn: str):
    safe_upgrade(clean_db, "exp_f2b_base")
    # Incomplete next digests: Alembic may apply h6 then fail h8 — partial stamp must not be h8.
    seed_tenant_identifier(admin_dsn, with_next=False)
    assert _versions(admin_dsn) == {"exp_f2b_base"}
    with pytest.raises(Exception):
        safe_upgrade(clean_db, "exp_f2b_h8")
    versions = _versions(admin_dsn)
    assert "exp_f2b_h8" not in versions
    assert versions == {"exp_f2b_h6"}
    assert _meta(admin_dsn, "hmac_phase8") is None
    assert _meta(admin_dsn, "active_authority") == "gen1"
    # Explicit remediation + retry required (no unsafe automatic onward cutover).
    conn = psycopg2.connect(admin_dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, tenant_id, canonical_value FROM exp_f2b_identifiers")
        for iid, tid, canon in cur.fetchall():
            cur.execute(
                """
                UPDATE exp_f2b_identifiers
                SET lookup_hmac_next=%s, hmac_key_version_next=2 WHERE id=%s
                """,
                (psycopg2.Binary(synthetic_hmac(f"{tid}:{canon}:2")), iid),
            )
        conn.commit()
    finally:
        conn.close()
    safe_upgrade(clean_db, "exp_f2b_h8")
    assert _versions(admin_dsn) == {"exp_f2b_h8"}
    _record("E02-F2B-13", {"result": "PASS", "partial_then_final": ["exp_f2b_h6", "exp_f2b_h8"]})


def test_e02_f2b_14_scope_clock_resource_closure(admin_dsn: str, pg_proof: str):
    now = datetime.now(timezone.utc)
    berlin = now.astimezone(ZoneInfo("Europe/Berlin"))
    assert now < BOUNDARY
    # allowlist path check via git
    root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    allowed_prefixes = (
        "experiments/m102_f2b_bounded_e02/",
        ".github/workflows/m102-f2b-bounded-e02.yml",
    )
    offenders = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip() if len(line) > 3 else ""
        if not path:
            continue
        if not any(path == p or path.startswith(p) for p in allowed_prefixes):
            # ignore evidence scratch outside? must be allowlisted
            offenders.append(path)
    assert not offenders, f"paths outside allowlist: {offenders}"
    assert "15" in pg_proof or "server_version_num=15" in pg_proof
    _record(
        "E02-F2B-14",
        {
            "result": "PASS",
            "now_utc": now.isoformat(),
            "now_berlin": berlin.isoformat(),
            "pg_proof": pg_proof,
            "offenders": offenders,
            "allowed_targets_count": len(ALLOWED_TARGETS),
        },
    )
