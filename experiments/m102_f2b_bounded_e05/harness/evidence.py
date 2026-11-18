"""E0.5 forensic evidence schema + fail-closed acceptance helpers."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXP_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = EXP_ROOT / "evidence"
REPO_ROOT = EXP_ROOT.parents[1]
EVIDENCE_PREFIX = "experiments/m102_f2b_bounded_e05/evidence/"

# Approved E0.5 contract digest (current-run binding)
CONTRACT_SHA256 = "6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783"
AUTHORIZATION_SHA256 = "15712f73fa02cb589109645ade6be700c5bd0ab9832d23e2286dba1fc86b4ec3"
# Immutable historical lineage
PARENT_E02 = "471f88417bfcf69ce864b333114e7fb0f777ede0"
PARENT_E03_FINAL = "0145b3fd114a022dd004a3a36be43a9a0994a9b5"
PARENT_E04_TESTED = "8d015959ec6b2570da74d63d8f7ee0e88d1cff64"
PARENT_E04_FINAL = "f1b11731590fe29a294f86cf7cf5b64878d8ec7d"
E03_CONTRACT_SHA256 = "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28"
E04_CONTRACT_SHA256 = "8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3"

REQUIRED_FIELDS = [
    "case_id",
    "finding_id",
    "classification",
    "execution_kind",
    "contract_sha256",
    "parent_e02_final_commit_sha",
    "parent_e03_final_commit_sha",
    "parent_e04_final_commit_sha",
    "tested_commit_sha",
    "run_id",
    "run_attempt",
    "timestamp_utc",
    "postgres_server_version_num",
    "database_label",
    "session_user",
    "current_user",
    "preconditions",
    "command_redacted",
    "expected_result",
    "observed_result",
    "exit_code",
    "before_state",
    "after_state",
    "evidence_files",
    "limitations",
    "source_test",
]

# Valid for *recording* failures; acceptance requires OBSERVED_PASS for all 19.
ALLOWED_CLASSIFICATIONS = {
    "OBSERVED_PASS",
    "OBSERVED_FAIL",
    "BLOCKED",
    "NOT_RUN",
    "UNVERIFIED",
    "REVIEW_ONLY",
    "HISTORICAL_E02",
    "EXECUTED_E03",
    "EXECUTED_E04",
    "EXECUTED_E05",
    "SKIPPED",  # recorded only so acceptance can explicitly deny it
}

NON_ACCEPTANCE_CLASSIFICATIONS = {
    "OBSERVED_FAIL",
    "BLOCKED",
    "NOT_RUN",
    "UNVERIFIED",
    "REVIEW_ONLY",
    "HISTORICAL_E02",
    "SKIPPED",
}

REQUIRED_CASE_IDS = [
    "E03-A01-P01",
    "E03-A01-N01",
    "E03-A02-N01",
    "E03-A02-P01",
    "E03-A02-N02",
    "E03-A03-P01",
    "E03-A03-N01",
    "E03-A04-P01",
    "E03-A04-N01",
    "E03-A05-C01",
    "E03-A06-P01",
    "E03-A06-N01",
    "E03-A06-N02",
    "E03-A07-C01",
    "E03-A07-C02",
    "E03-A08-N01",
    "E03-A08-P01",
    "E03-REG-P01",
    "E03-CLOSE-C01",
]

CASE_SCHEMA: dict[str, dict[str, str]] = {
    "E03-A01-P01": {"finding_id": "A01", "execution_kind": "PHYSICAL_PG15"},
    "E03-A01-N01": {"finding_id": "A01", "execution_kind": "PHYSICAL_PG15"},
    "E03-A02-N01": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15"},
    "E03-A02-P01": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15"},
    "E03-A02-N02": {"finding_id": "A02", "execution_kind": "PHYSICAL_PG15"},
    "E03-A03-P01": {"finding_id": "A03", "execution_kind": "PHYSICAL_PG15"},
    "E03-A03-N01": {"finding_id": "A03", "execution_kind": "PHYSICAL_PG15"},
    "E03-A04-P01": {"finding_id": "A04", "execution_kind": "PHYSICAL_PG15"},
    "E03-A04-N01": {"finding_id": "A04", "execution_kind": "PHYSICAL_PG15"},
    "E03-A05-C01": {"finding_id": "A05", "execution_kind": "GOVERNANCE_CONTROL"},
    "E03-A06-P01": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15"},
    "E03-A06-N01": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15"},
    "E03-A06-N02": {"finding_id": "A06", "execution_kind": "PHYSICAL_PG15"},
    "E03-A07-C01": {"finding_id": "A07", "execution_kind": "GOVERNANCE_CONTROL"},
    "E03-A07-C02": {"finding_id": "A07", "execution_kind": "GOVERNANCE_CONTROL"},
    "E03-A08-N01": {"finding_id": "A08", "execution_kind": "GOVERNANCE_CONTROL"},
    "E03-A08-P01": {"finding_id": "A08", "execution_kind": "GOVERNANCE_CONTROL"},
    "E03-REG-P01": {"finding_id": "REG", "execution_kind": "PHYSICAL_PG15"},
    "E03-CLOSE-C01": {"finding_id": "CLOSE", "execution_kind": "GOVERNANCE_CONTROL"},
}

REQUIRED_FIXTURE_IDS = [f"E04-V{i:02d}" for i in range(1, 15)]

SECRET_PATTERNS = [
    re.compile(r"password\s*=\s*\S+", re.I),
    re.compile(r"postgresql://[^:]+:[^@]+@"),
    re.compile(r"BEGIN (RSA )?PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"synth-ci-only"),
    re.compile(r"SYNTH_SECRET_SENTINEL_[A-Z0-9]+"),
]

AUX_MANIFEST_NAME = "EVIDENCE_AUX_SHA256SUMS.txt"
PRIMARY_MANIFEST_NAME = "EVIDENCE_CASE_SHA256SUMS.txt"
ROOT_DIGEST_NAME = "EVIDENCE_ROOT_DIGESTS.json"

AUX_INVENTORY = [
    *[f"{fid}.json" for fid in REQUIRED_FIXTURE_IDS],
    "junit.xml",
    "pytest.txt",
    "summary.txt",
    "forensic_verifier.txt",
    "POST_PYTEST_FORENSIC_VERIFIER.json",
    "E05_G2_PRE_EXECUTION_SAFETY_MANIFEST.json",
    "E05_SOURCE_EQUIVALENCE_LEDGER.json",
    PRIMARY_MANIFEST_NAME,
    "EVIDENCE_CASE_MANIFEST_DIGEST.txt",
]


def tested_commit_sha() -> str:
    return os.environ.get("GITHUB_SHA") or os.environ.get("E05_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN"


def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI"


def run_attempt() -> str:
    return os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI"


def write_evidence(case_id: str, payload: dict[str, Any]) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    caller = "unknown"
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller = frame.f_back.f_code.co_name
    base = {
        "case_id": case_id,
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "parent_e04_tested_commit_sha": PARENT_E04_TESTED,
        "parent_e04_final_commit_sha": PARENT_E04_FINAL,
        "e03_contract_sha256_historical": E03_CONTRACT_SHA256,
        "e04_contract_sha256_historical": E04_CONTRACT_SHA256,
        "tested_commit_sha": tested_commit_sha(),
        "run_id": run_id(),
        "run_attempt": run_attempt(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_files": [f"{EVIDENCE_PREFIX}{case_id}.json"],
        "source_test": payload.get("source_test") or caller,
        "limitations": payload.get("limitations")
        or [
            "Synthetic experiment only; not real Cloud/Local Sync proof.",
            "E0.5 forensic acceptance re-proof; not F2-B/Package 1/ACR/Gate approval.",
            "E5-E independent external verification PENDING.",
        ],
    }
    merged = {**base, **payload, "case_id": case_id, "source_test": payload.get("source_test") or caller}
    path = EVIDENCE / f"{case_id}.json"
    path.write_text(json.dumps(merged, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _looks_secret(obj: Any, path: str = "$") -> list[str]:
    """Recursive nested secret/DSN scan; returns pattern names, never matched secret text."""
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


def validate_evidence_record(
    data: dict[str, Any],
    *,
    path: Path | None = None,
    require_ci_identity: bool | None = None,
    expected_case_id: str | None = None,
) -> list[str]:
    """Schema + provenance validation of one evidence record (failure statuses allowed for recording)."""
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
            errors.append(f"{label}: finding_id mismatch want {schema['finding_id']}")
        if data.get("execution_kind") != schema["execution_kind"]:
            errors.append(f"{label}: execution_kind mismatch want {schema['execution_kind']}")

    cls = data.get("classification")
    if cls not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"{label}: invalid classification {cls!r}")

    if cls == "OBSERVED_PASS":
        ec = data.get("exit_code")
        if ec not in (0, "0", "NONZERO_EXPECTED", "NOT_APPLICABLE_WITH_REASON"):
            errors.append(f"{label}: OBSERVED_PASS with unexpected exit_code={ec!r}")
        obs = data.get("observed_result")
        if obs in (None, "", {}, []):
            errors.append(f"{label}: OBSERVED_PASS requires nonempty observed_result")

    tsha = str(data.get("tested_commit_sha", ""))
    rid = str(data.get("run_id", ""))
    ratt = str(data.get("run_attempt", ""))
    if require_ci_identity:
        if not re.fullmatch(r"[0-9a-f]{40}", tsha):
            errors.append(f"{label}: tested_commit_sha not full 40-hex in CI")
        gsha = os.environ.get("GITHUB_SHA", "")
        if gsha and tsha != gsha:
            errors.append(f"{label}: tested_commit_sha != GITHUB_SHA")
        if tsha in {"LOCAL_UNKNOWN", "LOCAL_NOT_CI"} or tsha.startswith("LOCAL_"):
            errors.append(f"{label}: LOCAL identity rejected in CI")
        if not re.fullmatch(r"[0-9]+", rid):
            errors.append(f"{label}: run_id must be numeric GITHUB_RUN_ID in CI")
        if rid == "LOCAL_NOT_CI" or rid.startswith("LOCAL_"):
            errors.append(f"{label}: LOCAL_NOT_CI rejected in CI")
        grid = os.environ.get("GITHUB_RUN_ID", "")
        if grid and rid != grid:
            errors.append(f"{label}: run_id != GITHUB_RUN_ID")
        if not re.fullmatch(r"[0-9]+", ratt):
            errors.append(f"{label}: run_attempt must be numeric in CI")
        gatt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        if gatt and ratt != gatt:
            errors.append(f"{label}: run_attempt != GITHUB_RUN_ATTEMPT")

    if data.get("contract_sha256") != CONTRACT_SHA256:
        errors.append(f"{label}: contract_sha256 mismatch")
    if data.get("parent_e02_final_commit_sha") != PARENT_E02:
        errors.append(f"{label}: parent_e02_final_commit_sha mismatch")
    if data.get("parent_e03_final_commit_sha") != PARENT_E03_FINAL:
        errors.append(f"{label}: parent_e03_final_commit_sha mismatch")
    if data.get("parent_e04_final_commit_sha") != PARENT_E04_FINAL:
        errors.append(f"{label}: parent_e04_final_commit_sha mismatch")

    ts = data.get("timestamp_utc")
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            errors.append(f"{label}: timestamp_utc must be timezone-aware UTC")
    except Exception:
        errors.append(f"{label}: invalid timestamp_utc")

    efiles = data.get("evidence_files")
    if not isinstance(efiles, list) or not efiles:
        errors.append(f"{label}: evidence_files must be nonempty list")
    else:
        for ep in efiles:
            if not isinstance(ep, str):
                errors.append(f"{label}: evidence_files entry not string")
                continue
            if ep.startswith("/") or ".." in ep.split("/") or ep.startswith("../"):
                errors.append(f"{label}: unsafe evidence path {ep!r}")
            if not ep.startswith(EVIDENCE_PREFIX):
                errors.append(f"{label}: evidence path outside allowlist {ep!r}")

    kind = data.get("execution_kind")
    if kind == "PHYSICAL_PG15":
        try:
            v = int(data.get("postgres_server_version_num"))
            if not (150000 <= v <= 159999):
                errors.append(f"{label}: postgres_server_version_num out of PG15 range")
        except Exception:
            errors.append(f"{label}: postgres_server_version_num not int")
        for role_field in ("session_user", "current_user", "database_label"):
            val = str(data.get(role_field, ""))
            if val.startswith("NOT_APPLICABLE"):
                errors.append(f"{label}: physical proof cannot use NOT_APPLICABLE for {role_field}")
    elif kind == "GOVERNANCE_CONTROL":
        pass
    else:
        errors.append(f"{label}: unexpected execution_kind {kind!r}")

    if not isinstance(data.get("source_test"), str) or not str(data.get("source_test")).strip():
        errors.append(f"{label}: source_test required nonempty string")

    leaks = _looks_secret(data)
    if leaks:
        # Do not echo matched secret text — only pattern identifiers.
        errors.append(f"{label}: potential secret patterns count={len(leaks)}")

    return errors


def acceptance_errors_for_record(
    data: dict[str, Any],
    *,
    path: Path | None = None,
    require_ci_identity: bool | None = None,
    expected_case_id: str | None = None,
) -> list[str]:
    """Acceptance gate: schema validation PLUS mandatory OBSERVED_PASS (E05-FC01)."""
    errors = validate_evidence_record(
        data,
        path=path,
        require_ci_identity=require_ci_identity,
        expected_case_id=expected_case_id,
    )
    label = path.name if path else str(data.get("case_id", "<memory>"))
    cls = data.get("classification")
    if cls != "OBSERVED_PASS":
        errors.append(
            f"{label}: acceptance requires OBSERVED_PASS, got {cls!r} (E05-FC01)"
        )
    if cls in NON_ACCEPTANCE_CLASSIFICATIONS:
        errors.append(f"{label}: non-acceptance classification {cls!r} denied")
    return errors


def validate_evidence_file(path: Path, *, require_ci_identity: bool | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    return validate_evidence_record(
        data, path=path, require_ci_identity=require_ci_identity, expected_case_id=path.stem
    )


def acceptance_errors_for_file(path: Path, *, require_ci_identity: bool | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    return acceptance_errors_for_record(
        data, path=path, require_ci_identity=require_ci_identity, expected_case_id=path.stem
    )


def write_case_manifest(
    case_ids: list[str] | None = None,
    manifest_name: str = PRIMARY_MANIFEST_NAME,
    *,
    evidence_dir: Path | None = None,
    path_prefix: str | None = None,
) -> tuple[Path, str]:
    """Write external SHA-256 manifest over final case JSON bytes (no self-hash)."""
    ids = case_ids or REQUIRED_CASE_IDS
    edir = evidence_dir or EVIDENCE
    prefix = path_prefix if path_prefix is not None else EVIDENCE_PREFIX
    lines: list[str] = []
    for case_id in ids:
        p = edir / f"{case_id}.json"
        if not p.is_file() or p.is_symlink():
            raise FileNotFoundError(f"missing regular evidence file for {case_id}")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = f"{prefix}{case_id}.json"
        lines.append(f"{digest}  {rel}")
    path = edir / manifest_name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, manifest_digest


def verify_case_manifest(
    manifest_path: Path,
    *,
    require_ci_identity: bool = True,
    require_acceptance_pass: bool = True,
    evidence_dir: Path | None = None,
    path_prefix: str | None = None,
) -> list[str]:
    """Independent read-back verification of the 19-case digest manifest (+ acceptance)."""
    errors: list[str] = []
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"manifest missing or symlink: {manifest_path}"]
    text = manifest_path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    prefix = path_prefix if path_prefix is not None else EVIDENCE_PREFIX
    for line in text.splitlines():
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
        if rel == str(manifest_path.as_posix()) or rel.endswith(manifest_path.name):
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
        if evidence_dir is not None:
            fp = evidence_dir / name
        else:
            fp = REPO_ROOT / rel
        if fp.is_symlink():
            errors.append(f"symlink refused: {rel}")
            continue
        if not fp.is_file():
            errors.append(f"missing file for manifest entry: {rel}")
            continue
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"hash mismatch for {rel}")
        if require_acceptance_pass:
            errors.extend(
                acceptance_errors_for_file(fp, require_ci_identity=require_ci_identity)
            )
        else:
            errors.extend(validate_evidence_file(fp, require_ci_identity=require_ci_identity))
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            seen_ids.append(str(data.get("case_id")))
        except Exception:
            pass

    if len(seen_ids) == 19:
        if set(seen_ids) != set(REQUIRED_CASE_IDS):
            errors.append(f"case_id set mismatch: {sorted(set(REQUIRED_CASE_IDS) - set(seen_ids))}")
        if len(set(seen_ids)) != 19:
            errors.append("duplicate case_id values among 19 files")

    return errors


def write_auxiliary_manifest(
    *,
    evidence_dir: Path | None = None,
    inventory: list[str] | None = None,
) -> tuple[Path, str, list[str]]:
    """Secondary integrity inventory over stable auxiliary evidence (no self-hash)."""
    edir = evidence_dir or EVIDENCE
    inv = inventory or list(AUX_INVENTORY)
    lines: list[str] = []
    missing: list[str] = []
    for name in inv:
        p = edir / name
        if not p.is_file() or p.is_symlink():
            missing.append(name)
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {EVIDENCE_PREFIX}{name}")
    if missing:
        raise FileNotFoundError(f"auxiliary inventory missing: {missing}")
    path = edir / AUX_MANIFEST_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest, inv


def verify_auxiliary_manifest(
    manifest_path: Path,
    *,
    evidence_dir: Path | None = None,
    expected_inventory: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    edir = evidence_dir or EVIDENCE
    inv = expected_inventory or list(AUX_INVENTORY)
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"aux manifest missing or symlink: {manifest_path}"]
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
        if rel.endswith(manifest_path.name) or rel.endswith(AUX_MANIFEST_NAME):
            errors.append("aux manifest must not include itself")
        if ".." in rel.split("/") or rel.startswith("/"):
            errors.append(f"unsafe aux path {rel}")
        if not rel.startswith(EVIDENCE_PREFIX):
            errors.append(f"aux path outside prefix {rel}")
        if rel in entries:
            errors.append(f"duplicate aux path {rel}")
        entries[rel] = digest

    expected = {f"{EVIDENCE_PREFIX}{n}" for n in inv}
    if set(entries) != expected:
        errors.append(
            f"aux inventory mismatch missing={sorted(expected - set(entries))} "
            f"extra={sorted(set(entries) - expected)}"
        )

    for rel, digest in entries.items():
        fp = edir / Path(rel).name
        if fp.is_symlink() or not fp.is_file():
            errors.append(f"aux file missing/symlink: {rel}")
            continue
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"aux hash mismatch for {rel}")
    return errors


def write_root_digests(primary_digest: str, aux_digest: str, *, evidence_dir: Path | None = None) -> Path:
    edir = evidence_dir or EVIDENCE
    body = {
        "gate": "E05_ROOT_DIGESTS",
        "primary_manifest": PRIMARY_MANIFEST_NAME,
        "primary_manifest_sha256": primary_digest,
        "auxiliary_manifest": AUX_MANIFEST_NAME,
        "auxiliary_manifest_sha256": aux_digest,
        "self_hashed": False,
        "independent_external_verification": "PENDING",
        "run_id": run_id(),
        "tested_commit_sha": tested_commit_sha(),
        "run_attempt": run_attempt(),
    }
    path = edir / ROOT_DIGEST_NAME
    # Root record must not include a hash of itself.
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def verify_root_digests(path: Path, *, primary_digest: str, aux_digest: str) -> list[str]:
    errors: list[str] = []
    if not path.is_file() or path.is_symlink():
        return [f"root digests missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"root digests unreadable: {exc}"]
    if data.get("primary_manifest_sha256") != primary_digest:
        errors.append("root primary digest mismatch")
    if data.get("auxiliary_manifest_sha256") != aux_digest:
        errors.append("root aux digest mismatch")
    if data.get("self_hashed") is not False:
        errors.append("root digests must not self-hash")
    if data.get("independent_external_verification") != "PENDING":
        errors.append("must not self-certify independent verification")
    return errors
