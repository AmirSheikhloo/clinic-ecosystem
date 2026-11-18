"""E0.6 retained E04-V01..V14 — real CLI process exits (same options as CI)."""

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
    AUTHORIZATION_SHA256,
    CONTRACT_SHA256,
    EVIDENCE,
    EVIDENCE_PREFIX,
    PARENT_E02,
    PARENT_E03_FINAL,
    PARENT_E04_FINAL,
    PARENT_E04_TESTED,
    PARENT_E05_FINAL,
    PARENT_E05_TESTED,
    REQUIRED_CASE_IDS,
    acceptance_errors_for_record,
    validate_evidence_record,
    write_case_manifest,
)

PRIMARY = Path(__file__).resolve().parents[1] / "scripts" / "primary_verify_cli.py"
POST_SEAL = Path(__file__).resolve().parents[1] / "scripts" / "post_seal_verify.py"
GATE = Path(__file__).resolve().parents[1] / "scripts" / "ci_gate_sequence.py"


def _run_primary(evidence_dir: Path, manifest: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PRIMARY), "--evidence-dir", str(evidence_dir), "--manifest", str(manifest)],
        capture_output=True,
        text=True,
    )


def _record_fixture(fid: str, **payload):
    out = EVIDENCE / f"{fid}.json"
    body = {
        "case_id": fid,
        "finding_id": "E04V",
        "classification": "OBSERVED_PASS",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_tested_commit_sha": PARENT_E04_TESTED,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "parent_e05_tested_commit_sha": PARENT_E05_TESTED,
        "parent_e05_final_commit_sha": PARENT_E05_FINAL,
        "e03_contract_sha256_historical": "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28",
        "e04_contract_sha256_historical": "8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3",
        "e05_contract_sha256_historical": "6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783",
        "tested_commit_sha": os.environ.get("GITHUB_SHA") or os.environ.get("E06_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN",
        "run_id": os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI",
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI",
        "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
        "postgres_server_version_num": 150000,
        "database_label": "NOT_APPLICABLE_validator_fixture",
        "session_user": "NOT_APPLICABLE_validator_fixture",
        "current_user": "NOT_APPLICABLE_validator_fixture",
        "preconditions": payload.get("preconditions", "disposable evidence copy"),
        "command_redacted": payload.get("command_redacted", fid),
        "expected_result": payload.get("expected_result", "fail-closed denial or positive verify"),
        "observed_result": payload.get("observed_result", {"ok": True}),
        "exit_code": 0,
        "before_state": payload.get("before_state", {}),
        "after_state": payload.get("after_state", {}),
        "evidence_files": [f"{EVIDENCE_PREFIX}{fid}.json"],
        "source_test": payload.get("source_test") or f"test_{fid.lower().replace('-', '_')}",
        "limitations": ["Validator fixture; not a physical PG15 case.", "E6-E PENDING."],
    }
    out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _seed(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for case_id in REQUIRED_CASE_IDS:
        src = EVIDENCE / f"{case_id}.json"
        assert src.is_file(), f"missing {case_id}"
        shutil.copy2(src, dst / f"{case_id}.json")


@pytest.fixture
def tmp_evidence_tree(tmp_path: Path):
    dst = tmp_path / "evidence_copy"
    _seed(dst)
    return dst


def test_e04_v01_no_circular_missing_c01(pg_proof: dict):
    candidate = {
        "case_id": "E03-A07-C01",
        "finding_id": "A07",
        "classification": "UNVERIFIED",
        "execution_kind": "GOVERNANCE_CONTROL",
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_tested_commit_sha": PARENT_E04_TESTED,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "parent_e05_tested_commit_sha": PARENT_E05_TESTED,
        "parent_e05_final_commit_sha": PARENT_E05_FINAL,
        "e03_contract_sha256_historical": "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28",
        "e04_contract_sha256_historical": "8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3",
        "e05_contract_sha256_historical": "6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783",
        "tested_commit_sha": os.environ.get("GITHUB_SHA") or "LOCAL_UNKNOWN",
        "run_id": os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI",
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI",
        "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
        "postgres_server_version_num": int(pg_proof["server_version_num"]),
        "database_label": "NOT_APPLICABLE_schema_validation",
        "session_user": "NOT_APPLICABLE_schema_validation",
        "current_user": "NOT_APPLICABLE_schema_validation",
        "preconditions": "C01 not yet written",
        "command_redacted": "in-memory provisional C01",
        "expected_result": "no circular missing-self",
        "observed_result": {"on_disk_c01_required_before_validate": False},
        "exit_code": 0,
        "before_state": {},
        "after_state": {},
        "evidence_files": [f"{EVIDENCE_PREFIX}E03-A07-C01.json"],
        "source_test": "test_e03_zz_a07_c01_evidence_schema",
        "limitations": ["provisional"],
    }
    errs = validate_evidence_record(candidate, require_ci_identity=False)
    assert "missing E03-A07-C01" not in str(errs)
    assert candidate["classification"] != "OBSERVED_PASS"
    acc = acceptance_errors_for_record(candidate, require_ci_identity=False)
    assert any("OBSERVED_PASS" in e for e in acc)
    _record_fixture("E04-V01", observed_result={"acceptance_denied": True, "error_count": len(acc)}, source_test="test_e04_v01_no_circular_missing_c01")


def test_e04_v02_complete_19_and_manifest(pg_proof: dict):
    missing = [i for i in REQUIRED_CASE_IDS if not (EVIDENCE / f"{i}.json").exists()]
    assert not missing, missing
    if not (EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt").exists():
        write_case_manifest()
    proc = _run_primary(EVIDENCE, EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _record_fixture("E04-V02", observed_result={"verifier_exit": 0, "count": 19}, command_redacted="primary_verify_cli", source_test="test_e04_v02_complete_19_and_manifest")


def test_e04_v03_missing_or_duplicate_id(tmp_evidence_tree: Path):
    (tmp_evidence_tree / "E03-A01-P01.json").unlink()
    src = tmp_evidence_tree / "E03-A01-N01.json"
    data = json.loads(src.read_text())
    data["case_id"] = "E03-A02-P01"
    src.write_text(json.dumps(data))
    # incomplete tree — write partial manifest lines for remaining
    lines = []
    for p in sorted(tmp_evidence_tree.glob("E03-*.json")):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {EVIDENCE_PREFIX}{p.name}")
    man = tmp_evidence_tree / "EVIDENCE_CASE_SHA256SUMS.txt"
    man.write_text("\n".join(lines) + "\n")
    proc = _run_primary(tmp_evidence_tree, man)
    assert proc.returncode != 0, proc.stdout
    _record_fixture("E04-V03", observed_result={"verifier_exit": proc.returncode, "denied": True}, command_redacted="primary_verify_cli(missing/swap)", source_test="test_e04_v03_missing_or_duplicate_id")


def test_e04_v04_byte_tamper_fails_manifest(tmp_path: Path):
    dst = tmp_path / "tamper"
    _seed(dst)
    man, _ = write_case_manifest(evidence_dir=dst)
    victim = dst / "E03-A01-P01.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-1] + (b"X" if raw[-1:] != b"X" else b"Y"))
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    assert "hash mismatch" in (proc.stdout + proc.stderr)
    _record_fixture("E04-V04", observed_result={"verifier_exit": proc.returncode}, command_redacted="primary_verify_cli(byte tamper)", source_test="test_e04_v04_byte_tamper_fails_manifest")


def test_e04_v05_stale_sha_rejected(tmp_path: Path):
    dst = tmp_path / "v05"
    _seed(dst)
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["tested_commit_sha"] = "LOCAL_UNKNOWN"
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    # Force CI identity via env
    env = os.environ.copy()
    env["GITHUB_RUN_ID"] = env.get("GITHUB_RUN_ID") or "12345"
    env["GITHUB_SHA"] = env.get("GITHUB_SHA") or ("a" * 40)
    env["GITHUB_RUN_ATTEMPT"] = env.get("GITHUB_RUN_ATTEMPT") or "1"
    proc = subprocess.run([sys.executable, str(PRIMARY), "--evidence-dir", str(dst), "--manifest", str(man)], capture_output=True, text=True, env=env)
    assert proc.returncode != 0
    _record_fixture("E04-V05", observed_result={"verifier_exit": proc.returncode}, source_test="test_e04_v05_stale_sha_rejected")


def test_e04_v06_stale_run_id_rejected(tmp_path: Path):
    dst = tmp_path / "v06"
    _seed(dst)
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["run_id"] = "LOCAL_NOT_CI"
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    env = os.environ.copy()
    env["GITHUB_RUN_ID"] = env.get("GITHUB_RUN_ID") or "12345"
    env["GITHUB_SHA"] = env.get("GITHUB_SHA") or ("b" * 40)
    env["GITHUB_RUN_ATTEMPT"] = "1"
    # also fix tested sha to match env for isolation of run_id fault
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["tested_commit_sha"] = env["GITHUB_SHA"]
    d["run_attempt"] = "1"
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = subprocess.run([sys.executable, str(PRIMARY), "--evidence-dir", str(dst), "--manifest", str(man)], capture_output=True, text=True, env=env)
    assert proc.returncode != 0
    _record_fixture("E04-V06", observed_result={"verifier_exit": proc.returncode}, source_test="test_e04_v06_stale_run_id_rejected")


def test_e04_v07_invalid_field_rejected(tmp_path: Path):
    dst = tmp_path / "v07"
    _seed(dst)
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["timestamp_utc"] = "not-a-timestamp"
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    _record_fixture("E04-V07", observed_result={"verifier_exit": proc.returncode}, source_test="test_e04_v07_invalid_field_rejected")


def test_e04_v08_skipped_as_pass_rejected(tmp_path: Path):
    dst = tmp_path / "v08"
    _seed(dst)
    d = json.loads((dst / "E03-CLOSE-C01.json").read_text())
    d["classification"] = "OBSERVED_FAIL"
    (dst / "E03-CLOSE-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    assert "OBSERVED_PASS" in (proc.stdout + proc.stderr) or "OBSERVED_FAIL" in (proc.stdout + proc.stderr)
    _record_fixture("E04-V08", observed_result={"verifier_exit": proc.returncode}, command_redacted="primary_verify_cli(OBSERVED_FAIL rehash)", source_test="test_e04_v08_skipped_as_pass_rejected")


def test_e04_v09_unsafe_paths_rejected(tmp_path: Path):
    dst = tmp_path / "v09"
    _seed(dst)
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["evidence_files"] = ["/tmp/x.json", f"{EVIDENCE_PREFIX}E03-A05-C01.json"]
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    _record_fixture("E04-V09", observed_result={"verifier_exit": proc.returncode}, source_test="test_e04_v09_unsafe_paths_rejected")


def test_e04_v10_secret_redaction(tmp_path: Path):
    dst = tmp_path / "v10"
    _seed(dst)
    d = json.loads((dst / "E03-A05-C01.json").read_text())
    d["observed_result"] = {"nested": {"token": "SYNTH_SECRET_SENTINEL_ABC"}}
    (dst / "E03-A05-C01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    assert "SYNTH_SECRET_SENTINEL_ABC" not in (proc.stdout + proc.stderr)
    _record_fixture("E04-V10", observed_result={"verifier_exit": proc.returncode, "denied": True}, source_test="test_e04_v10_secret_redaction")


def test_e04_v11_bad_manifest_rejected(tmp_path: Path):
    man = tmp_path / "EVIDENCE_CASE_SHA256SUMS.txt"
    man.write_text(
        "deadbeef  experiments/m102_f2b_bounded_e06/evidence/E03-A01-P01.json\n"
        f"{'a'*64}  {man.name}\n"
    )
    proc = _run_primary(tmp_path, man)
    assert proc.returncode != 0
    # aux self-hash denial via post_seal reuse path is covered in FC08 matrix
    _record_fixture("E04-V11", observed_result={"verifier_exit": proc.returncode, "primary_denied": True}, source_test="test_e04_v11_bad_manifest_rejected")


def test_e04_v12_physical_nota_rejected(tmp_path: Path):
    dst = tmp_path / "v12"
    _seed(dst)
    d = json.loads((dst / "E03-A01-P01.json").read_text())
    d["database_label"] = "NOT_APPLICABLE_wrong"
    d["session_user"] = "NOT_APPLICABLE_wrong"
    d["current_user"] = "NOT_APPLICABLE_wrong"
    (dst / "E03-A01-P01.json").write_text(json.dumps(d, indent=2) + "\n")
    man, _ = write_case_manifest(evidence_dir=dst)
    proc = _run_primary(dst, man)
    assert proc.returncode != 0
    _record_fixture("E04-V12", observed_result={"verifier_exit": proc.returncode}, source_test="test_e04_v12_physical_nota_rejected")


def test_e04_v13_forensic_gate_independent(tmp_path: Path):
    dst = tmp_path / "v13"
    _seed(dst)
    man, _ = write_case_manifest(evidence_dir=dst)
    victim = dst / "E03-A01-P01.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-1] + (b"Z" if raw[-1:] != b"Z" else b"Y"))
    proc = subprocess.run(
        [sys.executable, str(GATE), "--pytest-rc", "0", "--manifest", str(man), "--evidence-dir", str(dst)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    _record_fixture(
        "E04-V13",
        command_redacted="ci_gate_sequence.py pytest_rc=0 + primary_verify_cli",
        observed_result={"pytest_rc": 0, "job_equivalent_exit": proc.returncode},
        source_test="test_e04_v13_forensic_gate_independent",
    )


def test_e04_v14_clean_validator_pending_audit():
    man = EVIDENCE / "EVIDENCE_CASE_SHA256SUMS.txt"
    assert man.is_file(), "primary manifest must exist"
    proc = _run_primary(EVIDENCE, man)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _record_fixture(
        "E04-V14",
        command_redacted="primary_verify_cli(clean)",
        observed_result={"verifier_exit": 0, "e6_e": "PENDING", "architecture_approval": False},
        source_test="test_e04_v14_clean_validator_pending_audit",
    )
