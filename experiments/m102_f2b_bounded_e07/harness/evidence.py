"""E0.7 forensic evidence schema — noncircular seal, authentic detectors, frozen inventory."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXP_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = EXP_ROOT / "evidence"
REPO_ROOT = EXP_ROOT.parents[1]
EVIDENCE_PREFIX = "experiments/m102_f2b_bounded_e07/evidence/"

CONTRACT_SHA256 = "a9fbaf3edba705159d327dc292db71ac0072bd170d6010d868f6bf8690e7b32e"
AUTHORIZATION_SHA256 = "ba099b0767548d7e32c33f146b4d183600030ff0a71430f66dbb5f308ff2d4a7"

PARENT_E02 = "471f88417bfcf69ce864b333114e7fb0f777ede0"
PARENT_E03_FINAL = "0145b3fd114a022dd004a3a36be43a9a0994a9b5"
PARENT_E04_TESTED = "8d015959ec6b2570da74d63d8f7ee0e88d1cff64"
PARENT_E04_FINAL = "f1b11731590fe29a294f86cf7cf5b64878d8ec7d"
PARENT_E05_TESTED = "8652686f41f6420a7afe97e84b5f8f151c2a15bb"
PARENT_E05_FINAL = "92b240d7ef2da0b33ed9c50ed841ffb5e194fd83"
PARENT_E06_TESTED = "56a08278c18659458f625b4b30fa68aa590b0f0b"
PARENT_E06_FINAL = "36a0cebc67bda89e0942b0491d5bb2eff9745b04"

E03_CONTRACT_SHA256 = "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28"
E04_CONTRACT_SHA256 = "8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3"
E05_CONTRACT_SHA256 = "6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783"
E06_CONTRACT_SHA256 = "492aa65345a0d6033fb46d858185510f8721afc6435cdce0b8cdddf69861fb5a"

REQUIRED_FIELDS = [
    "case_id", "finding_id", "classification", "execution_kind",
    "contract_sha256", "authorization_sha256",
    "parent_e02_final_commit_sha", "parent_e03_final_commit_sha",
    "parent_e04_tested_commit_sha", "parent_e04_final_commit_sha",
    "parent_e05_tested_commit_sha", "parent_e05_final_commit_sha",
    "parent_e06_tested_commit_sha", "parent_e06_final_commit_sha",
    "e03_contract_sha256_historical", "e04_contract_sha256_historical",
    "e05_contract_sha256_historical", "e06_contract_sha256_historical",
    "tested_commit_sha", "run_id", "run_attempt", "timestamp_utc",
    "postgres_server_version_num", "database_label", "session_user", "current_user",
    "preconditions", "command_redacted", "expected_result", "observed_result",
    "exit_code", "before_state", "after_state", "evidence_files", "limitations",
    "source_test",
]

ALLOWED_CLASSIFICATIONS = {
    "OBSERVED_PASS", "OBSERVED_FAIL", "BLOCKED", "NOT_RUN", "UNVERIFIED",
    "REVIEW_ONLY", "HISTORICAL_E02", "EXECUTED_E03", "EXECUTED_E04",
    "EXECUTED_E05", "EXECUTED_E06", "EXECUTED_E07", "SKIPPED",
}

REQUIRED_CASE_IDS = [
    "E03-A01-P01", "E03-A01-N01", "E03-A02-N01", "E03-A02-P01", "E03-A02-N02",
    "E03-A03-P01", "E03-A03-N01", "E03-A04-P01", "E03-A04-N01", "E03-A05-C01",
    "E03-A06-P01", "E03-A06-N01", "E03-A06-N02", "E03-A07-C01", "E03-A07-C02",
    "E03-A08-N01", "E03-A08-P01", "E03-REG-P01", "E03-CLOSE-C01",
]

CASE_SCHEMA = {
    "E03-A01-P01": {"finding_id": "A01", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a01_p01_fail_closed_migrator"},
    "E03-A01-N01": {"finding_id": "A01", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a01_n01_set_role_denial"},
    "E03-A02-N01": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a02_n01_incomplete_backfill"},
    "E03-A02-P01": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a02_p01_notnull_and_check"},
    "E03-A02-N02": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a02_n02_guard_denies_without_catalog"},
    "E03-A03-P01": {"finding_id": "A03", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a03_p01_overlapping_writers"},
    "E03-A03-N01": {"finding_id": "A03", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a03_n01_stale_writer_fence"},
    "E03-A04-P01": {"finding_id": "A04", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a04_p01_admission_allow"},
    "E03-A04-N01": {"finding_id": "A04", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a04_n01_admission_deny"},
    "E03-A05-C01": {"finding_id": "A05", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_a05_c01_ci_governance"},
    "E03-A06-P01": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a06_p01_autocommit_role"},
    "E03-A06-N01": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a06_n01_invalid_index_recovery"},
    "E03-A06-N02": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_a06_n02_privilege_negatives"},
    "E03-A07-C01": {"finding_id": "A07", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_zz_a07_c01_evidence_schema"},
    "E03-A07-C02": {"finding_id": "A07", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_a07_c02_preflight_manifest"},
    "E03-A08-N01": {"finding_id": "A08", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_a08_n01_injected_path_denials"},
    "E03-A08-P01": {"finding_id": "A08", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_a08_p01_full_range_diff"},
    "E03-REG-P01": {"finding_id": "REG", "execution_kind": "PHYSICAL_PG15", "source_test": "test_e03_reg_p01_topology"},
    "E03-CLOSE-C01": {"finding_id": "CLOSE", "execution_kind": "GOVERNANCE_CONTROL", "source_test": "test_e03_zz_a07_c01_evidence_schema"},
}

REQUIRED_FIXTURE_IDS = [f"E04-V{i:02d}" for i in range(1, 15)]
FIXTURE_SOURCE_TESTS = {
    f"E04-V{i:02d}": name for i, name in enumerate([
        "test_e04_v01_no_circular_missing_c01",
        "test_e04_v02_complete_19_and_manifest",
        "test_e04_v03_missing_or_duplicate_id",
        "test_e04_v04_byte_tamper_fails_manifest",
        "test_e04_v05_stale_sha_rejected",
        "test_e04_v06_stale_run_id_rejected",
        "test_e04_v07_invalid_field_rejected",
        "test_e04_v08_skipped_as_pass_rejected",
        "test_e04_v09_unsafe_paths_rejected",
        "test_e04_v10_secret_redaction",
        "test_e04_v11_bad_manifest_rejected",
        "test_e04_v12_physical_nota_rejected",
        "test_e04_v13_forensic_gate_independent",
        "test_e04_v14_clean_validator_pending_audit",
    ], start=1)
}

E03_CLASS = "experiments.m102_f2b_bounded_e07.tests.test_e03_corrective_suite"
E04_CLASS = "experiments.m102_f2b_bounded_e07.tests.test_z_e04_validator_fixtures"
EXPECTED_JUNIT_IDENTITIES = frozenset(
    [(E03_CLASS, s["source_test"]) for cid, s in CASE_SCHEMA.items() if cid != "E03-CLOSE-C01"]
    + [(E04_CLASS, n) for n in FIXTURE_SOURCE_TESTS.values()]
)
assert len(EXPECTED_JUNIT_IDENTITIES) == 32, len(EXPECTED_JUNIT_IDENTITIES)

SECRET_PATTERNS = [
    re.compile(r"password\s*=\s*\S+", re.I),
    re.compile(r"postgresql://[^:]+:[^@]+@"),
    re.compile(r"BEGIN (RSA )?PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"synth-ci-only"),
    re.compile(r"SYNTH_SECRET_SENTINEL_[A-Z0-9]+"),
]

PRIMARY_MANIFEST_NAME = "EVIDENCE_CASE_SHA256SUMS.txt"
AUX_MANIFEST_NAME = "EVIDENCE_AUX_SHA256SUMS.txt"
ROOT_DIGEST_NAME = "EVIDENCE_ROOT_DIGESTS.json"
FC_MATRIX_NAME = "E07_FC_PROOF_MATRIX.json"
CLOSURE_JUDGMENTS_NAME = "E07_EV_CLOSURE_JUDGMENTS.json"
AUX_INVENTORY_SCHEMA_VERSION = "E07_AUX_INV_V1"

# Frozen FC gate-vector policy (§7): 10 rows, 12 vectors, 24 process outcomes
FC_VECTOR_POLICY: list[dict[str, Any]] = [
    {"predicate_id": "E05-FC01", "finding_ids": ["A0.1-01", "E5A-02"], "vector_id": "FC01_PRIMARY",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "ACCEPTANCE_NOT_OBSERVED_PASS"},
    {"predicate_id": "E05-FC02", "finding_ids": ["E5A-02"], "vector_id": "FC02_PRIMARY",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "CASE_MAP_MISMATCH"},
    {"predicate_id": "E05-FC03", "finding_ids": ["E5A-01"], "vector_id": "FC03_PRIMARY",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "LINEAGE_MISMATCH"},
    {"predicate_id": "E05-FC04", "finding_ids": ["E5A-02"], "vector_id": "FC04_PRIMARY",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "TYPE_OR_UTC"},
    {"predicate_id": "E05-FC05", "finding_ids": ["E5A-02"], "vector_id": "FC05_PRIMARY",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "EVIDENCE_OWNERSHIP"},
    {"predicate_id": "E05-FC06", "finding_ids": ["E5A-05"], "vector_id": "FC06_PRIMARY_SECRET",
     "entrypoint": "primary_verify_cli", "argv_schema_id": "PRIMARY_VERIFY_V1",
     "expected_negative_detector": "SECRET_PATTERN"},
    {"predicate_id": "E05-FC06", "finding_ids": ["E5A-05"], "vector_id": "FC06_AUX_REDACTION",
     "entrypoint": "aux_redaction_readback_cli", "argv_schema_id": "AUX_REDACTION_V1",
     "expected_negative_detector": "SECRET_PATTERN"},
    {"predicate_id": "E05-FC07", "finding_ids": ["E5A-03"], "vector_id": "FC07_CI_GATE",
     "entrypoint": "ci_gate_sequence", "argv_schema_id": "CI_GATE_V1",
     "expected_negative_detector": "JOB_EQ_NONZERO"},
    {"predicate_id": "E05-FC08", "finding_ids": ["E5A-03", "E5A-04"], "vector_id": "FC08_AUX_INTEGRITY",
     "entrypoint": "aux_integrity_readback_cli", "argv_schema_id": "AUX_INTEGRITY_V1",
     "expected_negative_detector": "AUX_HASH_MISMATCH"},
    {"predicate_id": "E05-FC09", "finding_ids": ["E5A-05", "E6A-04"], "vector_id": "FC09_JUNIT",
     "entrypoint": "junit_and_fixture_identity_readback_cli", "argv_schema_id": "JUNIT_FIXTURE_V1",
     "expected_negative_detector": "JUNIT_ALLOWLIST"},
    {"predicate_id": "E05-FC09", "finding_ids": ["E5A-05", "E6A-04"], "vector_id": "FC09_FIXTURE_PROVENANCE",
     "entrypoint": "junit_and_fixture_identity_readback_cli", "argv_schema_id": "JUNIT_FIXTURE_V1",
     "expected_negative_detector": "FIXTURE_PROVENANCE_MISMATCH"},
    {"predicate_id": "E05-FC10", "finding_ids": ["E5A-06"], "vector_id": "FC10_ROOT",
     "entrypoint": "root_identity_readback_cli", "argv_schema_id": "ROOT_IDENTITY_V1",
     "expected_negative_detector": "ROOT_IDENTITY"},
]
assert len(FC_VECTOR_POLICY) == 12
assert len({v["predicate_id"] for v in FC_VECTOR_POLICY}) == 10

CLOSURE_IDS = [f"E07-C{i:02d}" for i in range(1, 8)]
CLOSURE_TO_FINDING = {
    "E07-C01": "E6A-01", "E07-C02": "E6A-02", "E07-C03": "E6A-03", "E07-C04": "E6A-04",
    "E07-C05": "E6A-05", "E07-C06": "E6A-06", "E07-C07": "E6A-07",
}


def tested_commit_sha() -> str:
    return os.environ.get("GITHUB_SHA") or os.environ.get("E07_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN"


def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI"


def run_attempt() -> str:
    return os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI"


def cli_result(ok: bool, error_codes: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "ok": bool(ok),
        "error_codes": list(error_codes or []),
        "run_id": run_id(),
        "tested_commit_sha": tested_commit_sha(),
        "run_attempt": run_attempt(),
    }
    body.update(extra)
    return body


def emit_cli(result: dict[str, Any]) -> int:
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


def frozen_aux_inventory() -> list[str]:
    """Policy-derived auxiliary inventory — never inferred from a live directory listing alone."""
    inv: list[str] = []
    inv.extend(f"{fid}.json" for fid in REQUIRED_FIXTURE_IDS)
    inv.extend([
        "junit.xml", "pytest.txt", "summary.txt",
        "POST_PYTEST_FORENSIC_VERIFIER.json", "forensic_verifier.txt",
        "E07_G2_PRE_EXECUTION_SAFETY_MANIFEST.json",
        "E07_SOURCE_EQUIVALENCE_LEDGER.json",
        PRIMARY_MANIFEST_NAME, "EVIDENCE_CASE_MANIFEST_DIGEST.txt",
        FC_MATRIX_NAME, "fc_matrix_builder.txt",
        CLOSURE_JUDGMENTS_NAME,
    ])
    # 12 vectors × (pos+neg) json + stdout = 48 receipt files under fc_receipts/
    for v in FC_VECTOR_POLICY:
        for side in ("positive", "negative"):
            base = f"fc_receipts/{v['vector_id']}_{side}"
            inv.append(f"{base}.json")
            inv.append(f"{base}.stdout.txt")
    for cid in CLOSURE_IDS:
        inv.append(f"closure_receipts/{cid}.json")
        inv.append(f"closure_receipts/{cid}.stdout.txt")
    return inv


FROZEN_AUX_INVENTORY = frozen_aux_inventory()
assert len(FROZEN_AUX_INVENTORY) == len(set(FROZEN_AUX_INVENTORY))


def write_evidence(case_id: str, payload: dict[str, Any]) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    caller = "unknown"
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller = frame.f_back.f_code.co_name
    schema = CASE_SCHEMA.get(case_id, {})
    base = {
        "case_id": case_id,
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_tested_commit_sha": PARENT_E04_TESTED,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "parent_e05_tested_commit_sha": PARENT_E05_TESTED,
        "parent_e05_final_commit_sha": PARENT_E05_FINAL,
        "parent_e06_tested_commit_sha": PARENT_E06_TESTED,
        "parent_e06_final_commit_sha": PARENT_E06_FINAL,
        "e03_contract_sha256_historical": E03_CONTRACT_SHA256,
        "e04_contract_sha256_historical": E04_CONTRACT_SHA256,
        "e05_contract_sha256_historical": E05_CONTRACT_SHA256,
        "e06_contract_sha256_historical": E06_CONTRACT_SHA256,
        "tested_commit_sha": tested_commit_sha(),
        "run_id": run_id(),
        "run_attempt": run_attempt(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evidence_files": [f"{EVIDENCE_PREFIX}{case_id}.json"],
        "source_test": payload.get("source_test") or schema.get("source_test") or caller,
        "limitations": payload.get("limitations") or [
            "Synthetic experiment only; not real Cloud/Local Sync proof.",
            "E0.7 forensic harness closure; not F2-B/Package 1/ACR/Gate approval.",
            "E7-F independent external verification PENDING.",
        ],
    }
    merged = {**base, **payload, "case_id": case_id}
    merged["source_test"] = payload.get("source_test") or schema.get("source_test") or caller
    path = EVIDENCE / f"{case_id}.json"
    path.write_text(json.dumps(merged, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _looks_secret(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(_looks_secret(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_looks_secret(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        for pat in SECRET_PATTERNS:
            if pat.search(obj):
                hits.append(f"{path}:{pat.pattern}")
    return hits


def scan_text_for_secrets(text: str, label: str) -> list[str]:
    hits = []
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            hits.append(f"{label}:{pat.pattern}")
    return hits


def validate_evidence_record(
    data: dict[str, Any],
    *,
    path: Path | None = None,
    require_ci_identity: bool | None = None,
    expected_case_id: str | None = None,
    evidence_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    label = path.name if path else str(data.get("case_id", "<memory>"))
    if require_ci_identity is None:
        require_ci_identity = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("GITHUB_RUN_ID"))

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] in (None, ""):
            errors.append(f"{label}: missing {field}")

    case_id = data.get("case_id")
    if expected_case_id and case_id != expected_case_id:
        errors.append(f"{label}: case_id {case_id!r} != expected {expected_case_id!r}")
    if path is not None and case_id and path.stem != case_id:
        errors.append(f"{label}: basename {path.stem!r} != case_id {case_id!r}")

    schema = CASE_SCHEMA.get(str(case_id))
    if schema:
        if data.get("finding_id") != schema["finding_id"]:
            errors.append(f"{label}: finding_id mismatch")
        if data.get("execution_kind") != schema["execution_kind"]:
            errors.append(f"{label}: execution_kind mismatch")
        if data.get("source_test") != schema["source_test"]:
            errors.append(f"{label}: source_test mismatch want {schema['source_test']}")

    cls = data.get("classification")
    if cls not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"{label}: invalid classification {cls!r}")

    if cls == "OBSERVED_PASS":
        ec = data.get("exit_code")
        if not ((type(ec) is int and ec == 0) or ec in ("NONZERO_EXPECTED", "NOT_APPLICABLE_WITH_REASON")):
            errors.append(f"{label}: OBSERVED_PASS unexpected exit_code type/value={ec!r}")
        obs = data.get("observed_result")
        if not isinstance(obs, dict) or not obs:
            errors.append(f"{label}: OBSERVED_PASS requires nonempty observed_result object")
        for st in ("before_state", "after_state"):
            if not isinstance(data.get(st), dict):
                errors.append(f"{label}: {st} must be structured object")

    checks = [
        ("contract_sha256", CONTRACT_SHA256),
        ("authorization_sha256", AUTHORIZATION_SHA256),
        ("parent_e02_final_commit_sha", PARENT_E02),
        ("parent_e03_final_commit_sha", PARENT_E03_FINAL),
        ("parent_e04_tested_commit_sha", PARENT_E04_TESTED),
        ("parent_e04_final_commit_sha", PARENT_E04_FINAL),
        ("parent_e05_tested_commit_sha", PARENT_E05_TESTED),
        ("parent_e05_final_commit_sha", PARENT_E05_FINAL),
        ("parent_e06_tested_commit_sha", PARENT_E06_TESTED),
        ("parent_e06_final_commit_sha", PARENT_E06_FINAL),
        ("e03_contract_sha256_historical", E03_CONTRACT_SHA256),
        ("e04_contract_sha256_historical", E04_CONTRACT_SHA256),
        ("e05_contract_sha256_historical", E05_CONTRACT_SHA256),
        ("e06_contract_sha256_historical", E06_CONTRACT_SHA256),
    ]
    for key, expect in checks:
        if data.get(key) != expect:
            errors.append(f"{label}: {key} mismatch")

    tsha = str(data.get("tested_commit_sha", ""))
    rid = str(data.get("run_id", ""))
    ratt = str(data.get("run_attempt", ""))
    if require_ci_identity:
        if not re.fullmatch(r"[0-9a-f]{40}", tsha):
            errors.append(f"{label}: tested_commit_sha not 40-hex")
        gsha = os.environ.get("GITHUB_SHA", "")
        if gsha and tsha != gsha:
            errors.append(f"{label}: tested_commit_sha != GITHUB_SHA")
        if tsha.startswith("LOCAL_"):
            errors.append(f"{label}: LOCAL SHA rejected in CI")
        if not re.fullmatch(r"[0-9]+", rid) or rid.startswith("LOCAL_"):
            errors.append(f"{label}: run_id invalid for CI")
        grid = os.environ.get("GITHUB_RUN_ID", "")
        if grid and rid != grid:
            errors.append(f"{label}: run_id != GITHUB_RUN_ID")
        if not re.fullmatch(r"[0-9]+", ratt):
            errors.append(f"{label}: run_attempt invalid")
        gatt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        if gatt and ratt != gatt:
            errors.append(f"{label}: run_attempt != GITHUB_RUN_ATTEMPT")

    ts = data.get("timestamp_utc")
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            errors.append(f"{label}: timestamp_utc must be UTC zero-offset")
    except Exception:
        errors.append(f"{label}: invalid timestamp_utc")

    kind = data.get("execution_kind")
    if kind == "PHYSICAL_PG15":
        v = data.get("postgres_server_version_num")
        if not isinstance(v, int) or not (150000 <= v <= 159999):
            errors.append(f"{label}: postgres_server_version_num must be int in PG15 range")
        for role_field in ("session_user", "current_user", "database_label"):
            if str(data.get(role_field, "")).startswith("NOT_APPLICABLE"):
                errors.append(f"{label}: physical proof cannot use NOT_APPLICABLE for {role_field}")
    elif kind == "GOVERNANCE_CONTROL":
        v = data.get("postgres_server_version_num")
        if not isinstance(v, int):
            errors.append(f"{label}: postgres_server_version_num must be int")
    else:
        errors.append(f"{label}: unexpected execution_kind {kind!r}")

    efiles = data.get("evidence_files")
    if not isinstance(efiles, list) or not efiles:
        errors.append(f"{label}: evidence_files must be nonempty list")
    else:
        own = f"{EVIDENCE_PREFIX}{case_id}.json"
        if own not in efiles:
            errors.append(f"{label}: evidence_files must include own canonical path")
        for ep in efiles:
            if not isinstance(ep, str):
                errors.append(f"{label}: evidence_files entry not string")
                continue
            if ep.startswith("/") or ".." in ep.split("/") or ep.startswith("../"):
                errors.append(f"{label}: unsafe evidence path")
            if not ep.startswith(EVIDENCE_PREFIX):
                errors.append(f"{label}: evidence path outside allowlist")
            if evidence_dir is not None and ep == own:
                fp = evidence_dir / f"{case_id}.json"
                if fp.is_symlink() or not fp.is_file():
                    errors.append(f"{label}: own evidence file missing/symlink")

    leaks = _looks_secret(data)
    if leaks:
        errors.append(f"{label}: potential secret patterns count={len(leaks)}")
    return errors


def acceptance_errors_for_record(
    data: dict[str, Any],
    *,
    path: Path | None = None,
    require_ci_identity: bool | None = None,
    expected_case_id: str | None = None,
    evidence_dir: Path | None = None,
) -> list[str]:
    errors = validate_evidence_record(
        data, path=path, require_ci_identity=require_ci_identity,
        expected_case_id=expected_case_id, evidence_dir=evidence_dir,
    )
    label = path.name if path else str(data.get("case_id", "<memory>"))
    cls = data.get("classification")
    if cls != "OBSERVED_PASS":
        errors.append(f"{label}: acceptance requires OBSERVED_PASS, got {cls!r}")
    return errors


def validate_evidence_file(path: Path, *, require_ci_identity: bool | None = None, evidence_dir: Path | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    return validate_evidence_record(
        data, path=path, require_ci_identity=require_ci_identity,
        expected_case_id=path.stem, evidence_dir=evidence_dir or path.parent,
    )


def acceptance_errors_for_file(path: Path, *, require_ci_identity: bool | None = None, evidence_dir: Path | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    return acceptance_errors_for_record(
        data, path=path, require_ci_identity=require_ci_identity,
        expected_case_id=path.stem, evidence_dir=evidence_dir or path.parent,
    )


def write_case_manifest(
    case_ids: list[str] | None = None,
    manifest_name: str = PRIMARY_MANIFEST_NAME,
    *,
    evidence_dir: Path | None = None,
    path_prefix: str | None = None,
) -> tuple[Path, str]:
    ids = case_ids or REQUIRED_CASE_IDS
    edir = evidence_dir or EVIDENCE
    prefix = path_prefix if path_prefix is not None else EVIDENCE_PREFIX
    lines = []
    for case_id in ids:
        p = edir / f"{case_id}.json"
        if not p.is_file() or p.is_symlink():
            raise FileNotFoundError(f"missing regular evidence file for {case_id}")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {prefix}{case_id}.json")
    path = edir / manifest_name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def verify_case_manifest(
    manifest_path: Path,
    *,
    require_ci_identity: bool = True,
    require_acceptance_pass: bool = True,
    evidence_dir: Path | None = None,
    path_prefix: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"manifest missing or symlink: {manifest_path}"]
    prefix = path_prefix if path_prefix is not None else EVIDENCE_PREFIX
    entries: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            errors.append(f"bad manifest line: {line!r}")
            continue
        digest, rel = parts
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"bad digest: {digest}")
        if rel.endswith(manifest_path.name):
            errors.append("manifest must not include itself")
        if ".." in rel.split("/") or rel.startswith("/"):
            errors.append(f"unsafe manifest path {rel}")
        if not rel.startswith(prefix):
            errors.append(f"manifest path outside prefix: {rel}")
        if rel in entries:
            errors.append(f"duplicate manifest path {rel}")
        entries[rel] = digest
    expected_rels = {f"{prefix}{i}.json" for i in REQUIRED_CASE_IDS}
    if set(entries) != expected_rels:
        errors.append(
            f"manifest path set mismatch: missing={sorted(expected_rels - set(entries))} "
            f"extra={sorted(set(entries) - expected_rels)}"
        )
    if len(entries) != 19:
        errors.append(f"manifest entry count {len(entries)} != 19")
    seen_ids: list[str] = []
    for rel, digest in entries.items():
        name = Path(rel).name
        case_id = Path(name).stem
        fp = (evidence_dir / name) if evidence_dir is not None else (REPO_ROOT / rel)
        if fp.is_symlink():
            errors.append(f"symlink refused: {rel}")
            continue
        if not fp.is_file():
            errors.append(f"missing file for manifest entry: {rel}")
            continue
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"PRIMARY_HASH_MISMATCH for {rel}")
        if require_acceptance_pass:
            errs = acceptance_errors_for_file(fp, require_ci_identity=require_ci_identity, evidence_dir=evidence_dir or fp.parent)
            # map classification failure to canonical detector
            for e in errs:
                if "acceptance requires OBSERVED_PASS" in e:
                    errors.append("ACCEPTANCE_NOT_OBSERVED_PASS: " + e)
                elif "mismatch" in e and ("parent_" in e or "authorization" in e or "contract" in e):
                    errors.append("LINEAGE_MISMATCH: " + e)
                elif "timestamp" in e or "exit_code" in e or "postgres_server_version" in e or "must be structured":
                    errors.append("TYPE_OR_UTC: " + e)
                elif "evidence_files" in e or "ownership" in e or "unsafe" in e:
                    errors.append("EVIDENCE_OWNERSHIP: " + e)
                elif "source_test" in e or "finding_id" in e or "execution_kind" in e or "case_id" in e:
                    errors.append("CASE_MAP_MISMATCH: " + e)
                elif "secret" in e:
                    errors.append("SECRET_PATTERN: " + e)
                else:
                    errors.append(e)
        else:
            errors.extend(validate_evidence_file(fp, require_ci_identity=require_ci_identity, evidence_dir=evidence_dir or fp.parent))
        try:
            seen_ids.append(str(json.loads(fp.read_text(encoding="utf-8")).get("case_id")))
        except Exception:
            pass
    if len(seen_ids) == 19:
        if set(seen_ids) != set(REQUIRED_CASE_IDS):
            errors.append("CASE_MAP_MISMATCH: case_id set mismatch")
        if len(set(seen_ids)) != 19:
            errors.append("CASE_MAP_MISMATCH: duplicate case_id values")
    return errors


def write_auxiliary_manifest(
    *,
    evidence_dir: Path | None = None,
    inventory: list[str] | None = None,
) -> tuple[Path, str, list[str]]:
    """SEAL WRITER helper — must only be called from seal_writer_cli, never from post_seal_verify."""
    edir = evidence_dir or EVIDENCE
    inv = list(inventory) if inventory is not None else list(FROZEN_AUX_INVENTORY)
    lines = []
    missing = []
    for name in inv:
        p = edir / name
        if not p.is_file() or p.is_symlink():
            missing.append(name)
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {EVIDENCE_PREFIX}{name}")
    if missing:
        raise FileNotFoundError(f"AUX_INVENTORY_MISSING: {missing}")
    path = edir / AUX_MANIFEST_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest(), inv


def verify_auxiliary_manifest(
    manifest_path: Path,
    *,
    evidence_dir: Path | None = None,
    expected_inventory: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    edir = evidence_dir or EVIDENCE
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"aux manifest missing or symlink: {manifest_path}"]
    inv = expected_inventory if expected_inventory is not None else list(FROZEN_AUX_INVENTORY)
    entries: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            errors.append(f"bad aux line: {line!r}")
            continue
        digest, rel = parts
        if rel.endswith(AUX_MANIFEST_NAME):
            errors.append("aux manifest must not include itself")
        if ".." in rel.split("/") or rel.startswith("/") or not rel.startswith(EVIDENCE_PREFIX):
            errors.append(f"unsafe/out-of-prefix aux path {rel}")
        if rel in entries:
            errors.append(f"duplicate aux path {rel}")
        entries[rel] = digest
    expected = {f"{EVIDENCE_PREFIX}{n}" for n in inv}
    if set(entries) != expected:
        missing = sorted(expected - set(entries))
        extra = sorted(set(entries) - expected)
        if missing:
            errors.append(f"AUX_INVENTORY_MISSING: {missing[:8]}")
        if extra:
            errors.append(f"aux inventory extra: {extra[:8]}")
    for rel, digest in entries.items():
        rel_name = rel[len(EVIDENCE_PREFIX):]
        fp = edir / rel_name
        if fp.is_symlink() or not fp.is_file():
            errors.append(f"AUX_INVENTORY_MISSING: {rel}")
            continue
        if hashlib.sha256(fp.read_bytes()).hexdigest() != digest:
            errors.append(f"AUX_HASH_MISMATCH for {rel}")
    return errors


def write_root_digests(primary_digest: str, aux_digest: str, *, evidence_dir: Path | None = None) -> Path:
    edir = evidence_dir or EVIDENCE
    body = {
        "gate": "E07_ROOT_DIGESTS",
        "primary_manifest": PRIMARY_MANIFEST_NAME,
        "primary_manifest_sha256": primary_digest,
        "auxiliary_manifest": AUX_MANIFEST_NAME,
        "auxiliary_manifest_sha256": aux_digest,
        "self_hashed": False,
        "independent_external_verification": "PENDING",
        "independently_verified": False,
        "run_id": run_id(),
        "tested_commit_sha": tested_commit_sha(),
        "run_attempt": run_attempt(),
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "aux_inventory_schema_version": AUX_INVENTORY_SCHEMA_VERSION,
        "aux_inventory_count": len(FROZEN_AUX_INVENTORY),
    }
    path = edir / ROOT_DIGEST_NAME
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def verify_root_digests(path: Path, *, primary_digest: str, aux_digest: str, require_ci_identity: bool = True) -> list[str]:
    errors: list[str] = []
    if not path.is_file() or path.is_symlink():
        return [f"root digests missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"root digests unreadable: {exc}"]
    if data.get("primary_manifest_sha256") != primary_digest:
        errors.append("ROOT_IDENTITY: root primary digest mismatch")
    if data.get("auxiliary_manifest_sha256") != aux_digest:
        errors.append("ROOT_IDENTITY: root aux digest mismatch")
    if data.get("self_hashed") is not False:
        errors.append("ROOT_IDENTITY: root digests must not self-hash")
    if data.get("independent_external_verification") != "PENDING":
        errors.append("ROOT_IDENTITY: must not self-certify independent verification")
    if data.get("independently_verified") is not False:
        errors.append("ROOT_IDENTITY: independently_verified must be false")
    if require_ci_identity:
        if str(data.get("run_id")) != run_id():
            errors.append("ROOT_IDENTITY: root run_id != trusted provider")
        if str(data.get("tested_commit_sha")) != tested_commit_sha():
            errors.append("ROOT_IDENTITY: root tested_commit_sha != trusted provider")
        if str(data.get("run_attempt")) != run_attempt():
            errors.append("ROOT_IDENTITY: root run_attempt != trusted provider")
    if data.get("contract_sha256") != CONTRACT_SHA256:
        errors.append("ROOT_IDENTITY: root contract mismatch")
    if data.get("authorization_sha256") != AUTHORIZATION_SHA256:
        errors.append("ROOT_IDENTITY: root authorization mismatch")
    return errors


def verify_junit_allowlist(junit_path: Path) -> list[str]:
    errors: list[str] = []
    if not junit_path.is_file():
        return ["missing junit.xml"]
    cases = ET.parse(junit_path).getroot().findall(".//testcase")
    failed = sum(1 for c in cases if c.find("failure") is not None or c.find("error") is not None)
    skipped = sum(1 for c in cases if c.find("skipped") is not None)
    identities = [(c.attrib.get("classname", ""), c.attrib.get("name", "")) for c in cases]
    idset = set(identities)
    if len(identities) != 32:
        errors.append(f"JUNIT_ALLOWLIST: testcase count {len(identities)} != 32")
    if len(idset) != len(identities):
        errors.append("JUNIT_ALLOWLIST: duplicate junit identities")
    if failed or skipped:
        errors.append(f"JUNIT_ALLOWLIST: junit not clean failed={failed} skipped={skipped}")
    if idset != EXPECTED_JUNIT_IDENTITIES:
        errors.append(
            f"JUNIT_ALLOWLIST: identity mismatch missing={sorted(EXPECTED_JUNIT_IDENTITIES - idset)[:3]} "
            f"extra={sorted(idset - EXPECTED_JUNIT_IDENTITIES)[:3]}"
        )
    return errors


def verify_fixture_provenance(evidence_dir: Path, *, require_ci_identity: bool = True) -> list[str]:
    errors: list[str] = []
    for fid in REQUIRED_FIXTURE_IDS:
        fp = evidence_dir / f"{fid}.json"
        if not fp.is_file():
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: missing {fid}")
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} unreadable {exc}")
            continue
        if data.get("case_id") != fid:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} case_id")
        if data.get("source_test") != FIXTURE_SOURCE_TESTS[fid]:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} source_test")
        if data.get("classification") != "OBSERVED_PASS":
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} classification")
        if data.get("contract_sha256") != CONTRACT_SHA256:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} contract")
        if data.get("authorization_sha256") != AUTHORIZATION_SHA256:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} authorization")
        if data.get("parent_e06_final_commit_sha") != PARENT_E06_FINAL:
            errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} parent_e06_final")
        if require_ci_identity:
            if str(data.get("run_id")) != run_id():
                errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} run_id")
            if str(data.get("tested_commit_sha")) != tested_commit_sha():
                errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} sha")
            if str(data.get("run_attempt")) != run_attempt():
                errors.append(f"FIXTURE_PROVENANCE_MISMATCH: {fid} attempt")
    return errors


def scan_sealed_tree_for_secrets(evidence_dir: Path, inventory: list[str]) -> list[str]:
    errors: list[str] = []
    for name in inventory:
        fp = evidence_dir / name
        if not fp.is_file():
            continue
        try:
            text = fp.read_bytes().decode("utf-8")
        except Exception:
            continue
        hits = scan_text_for_secrets(text, name)
        if hits:
            errors.append(f"SECRET_PATTERN: sealed file count={len(hits)} file={name}")
    return errors


def extract_error_codes_from_stdout(text: str) -> list[str]:
    codes: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for c in obj.get("error_codes") or []:
            if isinstance(c, str):
                codes.append(c)
    return codes


def validate_fc_proof_matrix(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["missing E07_FC_PROOF_MATRIX.json"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"FC matrix unreadable: {exc}"]
    rows = data.get("predicates")
    if not isinstance(rows, list) or len(rows) != 10:
        return [f"FC matrix must have exactly 10 predicates"]
    expected_ids = [f"E05-FC{i:02d}" for i in range(1, 11)]
    if [r.get("predicate_id") for r in rows] != expected_ids:
        errors.append("FC predicate order/ids mismatch")

    # Build expected vectors from policy
    policy_by_pred: dict[str, list[dict[str, Any]]] = {}
    for v in FC_VECTOR_POLICY:
        policy_by_pred.setdefault(v["predicate_id"], []).append(v)

    total_vectors = 0
    for r in rows:
        pid = r.get("predicate_id")
        if r.get("finding_ids") != policy_by_pred[pid][0]["finding_ids"]:
            errors.append(f"{pid}: finding_ids mismatch")
        if r.get("contract_sha256") != CONTRACT_SHA256:
            errors.append(f"{pid}: contract mismatch")
        if r.get("authorization_sha256") != AUTHORIZATION_SHA256:
            errors.append(f"{pid}: authorization mismatch")
        if os.environ.get("GITHUB_RUN_ID"):
            if r.get("tested_commit_sha") != tested_commit_sha():
                errors.append(f"{pid}: tested_commit_sha mismatch")
            if r.get("run_id") != run_id():
                errors.append(f"{pid}: run_id mismatch")
        vectors = r.get("vectors")
        expect_vecs = policy_by_pred[pid]
        if not isinstance(vectors, list) or len(vectors) != len(expect_vecs):
            errors.append(f"{pid}: vectors count mismatch want {len(expect_vecs)}")
            continue
        for i, (got, exp) in enumerate(zip(vectors, expect_vecs)):
            total_vectors += 1
            if got.get("vector_id") != exp["vector_id"]:
                errors.append(f"{pid}[{i}]: vector_id mismatch")
            if got.get("entrypoint") != exp["entrypoint"]:
                errors.append(f"{pid}[{i}]: WRONG_GATE_FAMILY entrypoint")
            if got.get("argv_schema_id") != exp["argv_schema_id"]:
                errors.append(f"{pid}[{i}]: argv_schema_id mismatch")
            for side_name, expect_exit, expect_obs_zero in (
                ("positive", 0, True),
                ("negative", "NONZERO", False),
            ):
                side = got.get(side_name) or {}
                if side.get("expected_exit_code") != expect_exit:
                    errors.append(f"EXPECTED_EXIT_CONTRADICTION: {pid}.{side_name} expected_exit_code={side.get('expected_exit_code')!r}")
                obs = side.get("observed_exit_code")
                if not isinstance(obs, int) or type(obs) is bool:
                    errors.append(f"{pid}.{side_name}: observed_exit_code must be int")
                elif expect_obs_zero and obs != 0:
                    errors.append(f"{pid}.{side_name}: positive must be exit 0")
                elif not expect_obs_zero and not (1 <= obs <= 255):
                    errors.append(f"{pid}.{side_name}: negative must be nonzero int 1..255")
                det = side.get("observed_detector")
                if side_name == "negative":
                    if det != exp["expected_negative_detector"]:
                        errors.append(f"DETECTOR_OR_RECEIPT_MISMATCH: {pid}.{side_name} detector={det!r}")
                receipt = side.get("receipt_path")
                stdout_path = side.get("stdout_path")
                if not receipt or not stdout_path:
                    errors.append(f"DETECTOR_OR_RECEIPT_MISMATCH: {pid}.{side_name} missing receipt paths")
                else:
                    rp = path.parent / receipt
                    sp = path.parent / stdout_path
                    if not rp.is_file() or not sp.is_file():
                        errors.append(f"DETECTOR_OR_RECEIPT_MISMATCH: {pid}.{side_name} receipt files missing")
                    else:
                        # authenticate stdout hash and detector presence
                        actual_sha = hashlib.sha256(sp.read_bytes()).hexdigest()
                        if side.get("stdout_stderr_redacted_sha256") != actual_sha:
                            errors.append(f"DETECTOR_OR_RECEIPT_MISMATCH: {pid}.{side_name} stdout sha")
                        if side_name == "negative":
                            codes = extract_error_codes_from_stdout(sp.read_text(encoding="utf-8", errors="replace"))
                            if det not in codes and det not in sp.read_text(encoding="utf-8", errors="replace"):
                                errors.append(f"DETECTOR_OR_RECEIPT_MISMATCH: {pid}.{side_name} detector not in stdout")
    if total_vectors != 12:
        errors.append(f"FC total vectors {total_vectors} != 12")
    return errors


def validate_closure_judgments(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["CLOSURE_JUDGMENT_INVALID: missing judgments file"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"CLOSURE_JUDGMENT_INVALID: unreadable {exc}"]
    rows = data.get("judgments")
    if not isinstance(rows, list) or len(rows) != 7:
        return ["CLOSURE_JUDGMENT_INVALID: must have exactly 7 judgments"]
    ids = [r.get("id") for r in rows]
    if ids != CLOSURE_IDS:
        errors.append("CLOSURE_JUDGMENT_INVALID: id order mismatch")
    for r in rows:
        if r.get("verdict") != "SELF_TESTED_PENDING_FINAL_GATE_AND_EXTERNAL_AUDIT":
            errors.append(f"CLOSURE_JUDGMENT_INVALID: {r.get('id')} premature/invalid verdict {r.get('verdict')!r}")
        if r.get("finding") != CLOSURE_TO_FINDING.get(r.get("id")):
            errors.append(f"CLOSURE_JUDGMENT_INVALID: {r.get('id')} finding map")
        if r.get("independent_external_verification") not in (None, "PENDING"):
            if r.get("independent_external_verification") != "PENDING":
                errors.append(f"CLOSURE_JUDGMENT_INVALID: {r.get('id')} must not claim external PASS")
    if data.get("contract_sha256") != CONTRACT_SHA256:
        errors.append("CLOSURE_JUDGMENT_INVALID: contract")
    if data.get("authorization_sha256") != AUTHORIZATION_SHA256:
        errors.append("CLOSURE_JUDGMENT_INVALID: authorization")
    return errors


def tree_sha256_manifest(root: Path) -> str:
    """Deterministic recursive file digest manifest of a directory tree."""
    lines = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + ("\n" if lines else "")
