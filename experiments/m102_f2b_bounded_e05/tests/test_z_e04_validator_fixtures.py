"""E0.5 retained E04-V01..V14 fixtures — real final-gate invocations on disposable trees."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from harness.evidence import (
    CONTRACT_SHA256,
    EVIDENCE,
    EVIDENCE_PREFIX,
    PARENT_E02,
    PARENT_E03_FINAL,
    PARENT_E04_FINAL,
    REQUIRED_CASE_IDS,
    acceptance_errors_for_record,
    validate_evidence_record,
    verify_case_manifest,
    write_case_manifest,
)

FIXTURE_EVIDENCE: dict[str, dict] = {}
GATE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ci_gate_sequence.py"


def _record_fixture(fid: str, **payload):
    FIXTURE_EVIDENCE[fid] = payload
    out = EVIDENCE / f"{fid}.json"
    body = {
        "case_id": fid,
        "finding_id": "E04V",
        "classification": payload.get("classification", "OBSERVED_PASS"),
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": "15712f73fa02cb589109645ade6be700c5bd0ab9832d23e2286dba1fc86b4ec3",
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": os.environ.get("GITHUB_SHA")
        or os.environ.get("E05_TESTED_COMMIT_SHA")
        or "LOCAL_UNKNOWN",
        "run_id": os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI",
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI",
        "timestamp_utc": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_validator_fixture",
        "session_user": "NOT_APPLICABLE_validator_fixture",
        "current_user": "NOT_APPLICABLE_validator_fixture",
        "preconditions": payload.get("preconditions", "disposable evidence copy"),
        "command_redacted": payload.get("command_redacted", fid),
        "expected_result": payload.get("expected_result", "fail-closed denial or positive verify"),
        "observed_result": payload.get("observed_result", {}),
        "exit_code": payload.get("exit_code", 0),
        "before_state": payload.get("before_state", {}),
        "after_state": payload.get("after_state", {}),
        "evidence_files": [f"{EVIDENCE_PREFIX}{fid}.json"],
        "source_test": payload.get("source_test") or f"test_{fid.lower().replace('-', '_')}",
        "limitations": [
            "Validator fixture on disposable copies; not a physical PG15 case.",
            "E5-E independent external verification PENDING.",
        ],
    }
    out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _seed_tree(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for case_id in REQUIRED_CASE_IDS:
        src = EVIDENCE / f"{case_id}.json"
        assert src.is_file(), f"prerequisite missing: {case_id}"
        shutil.copy2(src, dst / f"{case_id}.json")


def _write_tree_manifest(dst: Path) -> Path:
    lines = []
    for case_id in REQUIRED_CASE_IDS:
        p = dst / f"{case_id}.json"
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {EVIDENCE_PREFIX}{case_id}.json")
    man = dst / "EVIDENCE_CASE_SHA256SUMS.txt"
    man.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return man


@pytest.fixture
def tmp_evidence_tree(tmp_path: Path):
    dst = tmp_path / "evidence_copy"
    _seed_tree(dst)
    return dst


def test_e04_v01_no_circular_missing_c01(pg_proof: dict):
    candidate = {
        "case_id": "E03-A07-C01",
        "finding_id": "A07",
        "classification": "UNVERIFIED",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": os.environ.get("GITHUB_SHA") or "LOCAL_UNKNOWN",
        "run_id": os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI",
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI",
        "timestamp_utc": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
        "postgres_server_version_num": pg_proof["server_version_num"],
        "database_label": "NOT_APPLICABLE_schema_validation",
        "session_user": "NOT_APPLICABLE_schema_validation",
        "current_user": "NOT_APPLICABLE_schema_validation",
        "preconditions": "C01 not yet written",
        "command_redacted": "in-memory provisional C01",
        "expected_result": "no circular missing-self false failure",
        "observed_result": {"on_disk_c01_required_before_validate": False},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A07-C01.json"],
        "source_test": "test_e04_v01_no_circular_missing_c01",
        "limitations": ["provisional"],
    }
    errs = validate_evidence_record(candidate, require_ci_identity=False)
    assert "missing E03-A07-C01" not in str(errs)
    assert candidate["classification"] != "OBSERVED_PASS"
    acc = acceptance_errors_for_record(candidate, require_ci_identity=False)
    assert any("OBSERVED_PASS" in e for e in acc)
    _record_fixture(
        "E04-V01",
        preconditions="fresh protocol, C01 not written",
        command_redacted="validate_evidence_record + acceptance_errors_for_record(provisional C01)",
        expected_result="no circular missing-self; no premature PASS",
        observed_result={
            "schema_errors": errs,
            "acceptance_errors_count": len(acc),
            "classification": candidate["classification"],
        },
        exit_code=0,
    )


def test_e04_v02_complete_19_and_manifest(pg_proof: dict):
    missing = [i for i in REQUIRED_CASE_IDS if not (EVIDENCE / f"{i}.json").exists()]
    assert not missing, missing
    if not (EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt").exists():
        write_case_manifest()
    errors = verify_case_manifest(
        EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt",
        require_ci_identity=bool(os.environ.get("GITHUB_RUN_ID")),
        require_acceptance_pass=True,
    )
    assert not errors, errors
    _record_fixture(
        "E04-V02",
        command_redacted="verify_case_manifest(require_acceptance_pass=True)",
        observed_result={"verified": True, "count": 19, "errors": []},
        exit_code=0,
    )


def test_e04_v03_missing_or_duplicate_id(tmp_evidence_tree: Path):
    target = tmp_evidence_tree / "E03-A01-P01.json"
    target.unlink()
    src = tmp_evidence_tree / "E03-A01-N01.json"
    data = json.loads(src.read_text())
    data["case_id"] = "E03-A02-P01"
    src.write_text(json.dumps(data))
    # Rebuild manifest over remaining files with intentional wrong set
    lines = []
    for p in sorted(tmp_evidence_tree.glob("E03-*.json")):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {EVIDENCE_PREFIX}{p.name}")
    man = tmp_evidence_tree / "EVIDENCE_CASE_SHA256SUMS.txt"
    man.write_text("\n".join(lines) + "\n")
    errors = verify_case_manifest(
        man,
        require_ci_identity=False,
        require_acceptance_pass=True,
        evidence_dir=tmp_evidence_tree,
    )
    assert errors, "real final verifier must deny missing/swapped IDs"
    assert any("mismatch" in e or "basename" in e or "case_id" in e or "missing" in e for e in errors)
    _record_fixture(
        "E04-V03",
        command_redacted="verify_case_manifest(disposable missing/swap tree)",
        observed_result={"denied": True, "error_count": len(errors), "sample": errors[:5]},
        exit_code=0,
        expected_result="reject missing/duplicate/wrong ID via real verifier",
    )


def test_e04_v04_byte_tamper_fails_manifest(tmp_path: Path):
    dst = tmp_path / "tamper_tree"
    _seed_tree(dst)
    man = _write_tree_manifest(dst)
    victim = dst / "E03-A01-P01.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-1] + (b"X" if raw[-1:] != b"X" else b"Y"))
    errors = verify_case_manifest(
        man,
        require_ci_identity=False,
        require_acceptance_pass=False,
        evidence_dir=dst,
    )
    assert any("hash mismatch" in e for e in errors), errors
    _record_fixture(
        "E04-V04",
        command_redacted="verify_case_manifest(disposable byte-tampered tree)",
        observed_result={"denied": True, "errors": [e for e in errors if "hash" in e][:3]},
        exit_code=0,
    )


def test_e04_v05_stale_sha_rejected():
    bad = {
        "case_id": "E03-A05-C01",
        "finding_id": "A05",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "LOCAL_UNKNOWN",
        "run_id": "12345",
        "run_attempt": "1",
        "timestamp_utc": "2026-11-18T00:00:00+00:00",
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_governance_control",
        "session_user": "NOT_APPLICABLE_governance_control",
        "current_user": "NOT_APPLICABLE_governance_control",
        "preconditions": "x",
        "command_redacted": "x",
        "expected_result": "x",
        "observed_result": {"x": 1},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A05-C01.json"],
        "source_test": "test_e04_v05_stale_sha_rejected",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=True)
    assert any("LOCAL" in e or "40-hex" in e or "tested_commit_sha" in e for e in errs)
    _record_fixture("E04-V05", observed_result={"errors": errs}, exit_code=0)


def test_e04_v06_stale_run_id_rejected():
    bad = {
        "case_id": "E03-A05-C01",
        "finding_id": "A05",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "a" * 40,
        "run_id": "LOCAL_NOT_CI",
        "run_attempt": "1",
        "timestamp_utc": "2026-11-18T00:00:00+00:00",
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_governance_control",
        "session_user": "NOT_APPLICABLE_governance_control",
        "current_user": "NOT_APPLICABLE_governance_control",
        "preconditions": "x",
        "command_redacted": "x",
        "expected_result": "x",
        "observed_result": {"x": 1},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A05-C01.json"],
        "source_test": "test_e04_v06_stale_run_id_rejected",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=True)
    assert any("LOCAL_NOT_CI" in e or "run_id" in e for e in errs)
    _record_fixture("E04-V06", observed_result={"errors": errs}, exit_code=0)


def test_e04_v07_invalid_field_rejected():
    bad = {
        "case_id": "E03-A05-C01",
        "finding_id": "A05",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "b" * 40,
        "run_id": "1",
        "run_attempt": "1",
        "timestamp_utc": "not-a-timestamp",
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_governance_control",
        "session_user": "NOT_APPLICABLE_governance_control",
        "current_user": "NOT_APPLICABLE_governance_control",
        "command_redacted": "x",
        "expected_result": "x",
        "observed_result": {"x": 1},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A05-C01.json"],
        "source_test": "test_e04_v07_invalid_field_rejected",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=False)
    assert any("timestamp" in e or "missing preconditions" in e for e in errs)
    _record_fixture("E04-V07", observed_result={"errors": errs}, exit_code=0)


def test_e04_v08_skipped_as_pass_rejected(tmp_path: Path):
    """E05-FC01: OBSERVED_FAIL/BLOCKED/etc with freshly valid hashes must be denied by acceptance."""
    dst = tmp_path / "status_fail_tree"
    _seed_tree(dst)
    victim = dst / "E03-CLOSE-C01.json"
    data = json.loads(victim.read_text())
    data["classification"] = "OBSERVED_FAIL"
    victim.write_text(json.dumps(data, indent=2) + "\n")
    man = _write_tree_manifest(dst)
    # Hash layer is valid; acceptance must still deny.
    errors = verify_case_manifest(
        man,
        require_ci_identity=False,
        require_acceptance_pass=True,
        evidence_dir=dst,
    )
    assert any("OBSERVED_PASS" in e or "OBSERVED_FAIL" in e for e in errors), errors
    # Also direct SKIPPED recording denial
    skipped = dict(data)
    skipped["classification"] = "SKIPPED"
    skipped["case_id"] = "E03-A05-C01"
    skipped["finding_id"] = "A05"
    skipped["execution_kind"] = "GOVERNANCE_CONTROL"
    skipped["evidence_files"] = [f"{EVIDENCE_PREFIX}E03-A05-C01.json"]
    skipped["source_test"] = "test_e04_v08_skipped_as_pass_rejected"
    acc = acceptance_errors_for_record(skipped, require_ci_identity=False)
    assert acc
    _record_fixture(
        "E04-V08",
        command_redacted="verify_case_manifest(status=OBSERVED_FAIL, valid rehash)",
        observed_result={
            "acceptance_denied": True,
            "error_count": len(errors),
            "skipped_direct_errors": len(acc),
        },
        exit_code=0,
    )


def test_e04_v09_unsafe_paths_rejected():
    bad = {
        "case_id": "E03-A05-C01",
        "finding_id": "A05",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "d" * 40,
        "run_id": "1",
        "run_attempt": "1",
        "timestamp_utc": "2026-11-18T00:00:00+00:00",
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_governance_control",
        "session_user": "NOT_APPLICABLE_governance_control",
        "current_user": "NOT_APPLICABLE_governance_control",
        "preconditions": "x",
        "command_redacted": "x",
        "expected_result": "x",
        "observed_result": {"x": 1},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": ["/tmp/secret.json", "../escape.json"],
        "source_test": "test_e04_v09_unsafe_paths_rejected",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=False)
    assert any("unsafe" in e or "allowlist" in e for e in errs)
    _record_fixture("E04-V09", observed_result={"errors": errs}, exit_code=0)


def test_e04_v10_secret_redaction():
    bad = {
        "case_id": "E03-A05-C01",
        "finding_id": "A05",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "e" * 40,
        "run_id": "1",
        "run_attempt": "1",
        "timestamp_utc": "2026-11-18T00:00:00+00:00",
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_governance_control",
        "session_user": "NOT_APPLICABLE_governance_control",
        "current_user": "NOT_APPLICABLE_governance_control",
        "preconditions": "x",
        "command_redacted": "nested",
        "expected_result": "x",
        "observed_result": {
            "nested": {"dsn": "postgresql://u:p@h/db", "token": "SYNTH_SECRET_SENTINEL_ABC"}
        },
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A05-C01.json"],
        "source_test": "test_e04_v10_secret_redaction",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=False)
    assert any("secret" in e for e in errs)
    summary = {"fixture": "E04-V10", "denied": True, "error_count": len(errs)}
    assert "SYNTH_SECRET_SENTINEL" not in json.dumps(summary)
    assert "postgresql://u:p@" not in json.dumps(errs)
    _record_fixture("E04-V10", observed_result={"denied": True, "error_count": len(errs)}, exit_code=0)


def test_e04_v11_bad_manifest_rejected(tmp_path: Path):
    man = tmp_path / "EVIDENCE_CASE_SHA256SUMS.txt"
    man.write_text(
        "deadbeef  experiments/m102_f2b_bounded_e05/evidence/E03-A01-P01.json\n"
        f"{'a' * 64}  {man.name}\n"
    )
    errors = verify_case_manifest(man, require_ci_identity=False, require_acceptance_pass=True)
    assert errors
    _record_fixture("E04-V11", observed_result={"errors": errors[:10]}, exit_code=0)


def test_e04_v12_physical_nota_rejected():
    bad = {
        "case_id": "E03-A01-P01",
        "finding_id": "A01",
        "classification": "OBSERVED_PASS",
        "execution_kind": "PHYSICAL_PG15",
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "tested_commit_sha": "f" * 40,
        "run_id": "1",
        "run_attempt": "1",
        "timestamp_utc": "2026-11-18T00:00:00+00:00",
        "postgres_server_version_num": 150020,
        "database_label": "NOT_APPLICABLE_wrong",
        "session_user": "NOT_APPLICABLE_wrong",
        "current_user": "NOT_APPLICABLE_wrong",
        "preconditions": "x",
        "command_redacted": "x",
        "expected_result": "x",
        "observed_result": {"x": 1},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A01-P01.json"],
        "source_test": "test_e04_v12_physical_nota_rejected",
        "limitations": ["t"],
    }
    errs = validate_evidence_record(bad, require_ci_identity=False)
    assert any("NOT_APPLICABLE" in e for e in errs)
    _record_fixture("E04-V12", observed_result={"errors": errs}, exit_code=0)


def test_e04_v13_forensic_gate_independent(tmp_path: Path):
    """Green simulated pytest + red forensic gate => nonzero job-equivalent exit (real CLI)."""
    dst = tmp_path / "v13_tree"
    _seed_tree(dst)
    victim = dst / "E03-A01-P01.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-1] + b"Z")
    man = _write_tree_manifest(dst)  # written BEFORE tamper? need after wrong - rewrite after tamper? 
    # Manifest was written after seed then we tampered — rewrite? For V13 we want forensic fail.
    # Re-read: we seeded, wrote manifest of good bytes, then tampered file -> hash mismatch.
    # Actually order above: seed, tamper, then _write_tree_manifest would make hashes match.
    # Fix: write manifest of good tree then tamper.
    dst2 = tmp_path / "v13_tree2"
    _seed_tree(dst2)
    man = _write_tree_manifest(dst2)
    victim = dst2 / "E03-A01-P01.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-1] + (b"Z" if raw[-1:] != b"Z" else b"Y"))
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--pytest-rc",
            "0",
            "--manifest",
            str(man),
            "--evidence-dir",
            str(dst2),
            "--require-acceptance",
            "0",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr
    _record_fixture(
        "E04-V13",
        command_redacted="ci_gate_sequence.py pytest_rc=0 + verify_case_manifest(tampered)",
        expected_result="job-equivalent exit != 0 when forensic red despite pytest green",
        observed_result={
            "pytest_rc": 0,
            "job_equivalent_exit": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-500:],
        },
        exit_code=0,
    )


def test_e04_v14_clean_validator_pending_audit():
    man = EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt"
    assert man.is_file(), "primary manifest must exist before V14 positive acceptance"
    errors = verify_case_manifest(
        man,
        require_ci_identity=bool(os.environ.get("GITHUB_RUN_ID")),
        require_acceptance_pass=True,
    )
    assert not errors, errors
    _record_fixture(
        "E04-V14",
        command_redacted="verify_case_manifest(require_acceptance_pass=True)",
        observed_result={
            "status": "PRIMARY_VALIDATOR_OK_PENDING_AUX_SEAL_AND_INDEPENDENT_AUDIT",
            "architecture_approval": False,
            "e5_e": "PENDING",
            "errors": [],
        },
        exit_code=0,
        expected_result="primary validator succeeds; aux seal + independent audit still pending",
    )
