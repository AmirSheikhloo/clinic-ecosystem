"""E0.4 forensic evidence schema + trusted provenance helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXP_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = EXP_ROOT / "evidence"

# Approved E0.4 contract digest (current-run binding)
CONTRACT_SHA256 = "8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3"
# Immutable historical lineage
PARENT_E02 = "471f88417bfcf69ce864b333114e7fb0f777ede0"
PARENT_E03_FINAL = "0145b3fd114a022dd004a3a36be43a9a0994a9b5"
E03_CONTRACT_SHA256 = "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28"

REQUIRED_FIELDS = [
    "case_id",
    "finding_id",
    "classification",
    "execution_kind",
    "contract_sha256",
    "parent_e02_final_commit_sha",
    "tested_commit_sha",
    "run_id",
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
]

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

SECRET_PATTERNS = [
    re.compile(r"password\s*=\s*\S+", re.I),
    re.compile(r"postgresql://[^:]+:[^@]+@"),
    re.compile(r"BEGIN (RSA )?PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def tested_commit_sha() -> str:
    return os.environ.get("GITHUB_SHA") or os.environ.get("E04_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN"


def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI"


def run_attempt() -> str:
    return os.environ.get("GITHUB_RUN_ATTEMPT") or "LOCAL_NOT_CI"


def write_evidence(case_id: str, payload: dict[str, Any]) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    base = {
        "case_id": case_id,
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "parent_e03_final_commit_sha": PARENT_E03_FINAL,
        "e03_contract_sha256_historical": E03_CONTRACT_SHA256,
        "tested_commit_sha": tested_commit_sha(),
        "run_id": run_id(),
        "run_attempt": run_attempt(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_files": [f"experiments/m102_f2b_bounded_e04/evidence/{case_id}.json"],
        "limitations": payload.get("limitations")
        or [
            "Synthetic experiment only; not real Cloud/Local Sync proof.",
            "E0.4 forensic re-proof; not F2-B/Package 1/ACR/Gate approval.",
        ],
    }
    merged = {**base, **payload, "case_id": case_id}
    # Never embed self-digest inside the JSON
    path = EVIDENCE / f"{case_id}.json"
    path.write_text(json.dumps(merged, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _looks_secret(text: str) -> list[str]:
    hits = []
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def validate_evidence_record(
    data: dict[str, Any],
    *,
    path: Path | None = None,
    require_ci_identity: bool | None = None,
) -> list[str]:
    """Full forensic validation of one evidence record (in-memory or loaded)."""
    errors: list[str] = []
    label = path.name if path else data.get("case_id", "<memory>")

    if require_ci_identity is None:
        require_ci_identity = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("GITHUB_RUN_ID"))

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] in (None, ""):
            errors.append(f"{label}: missing {field}")

    cls = data.get("classification")
    if cls not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"{label}: invalid classification {cls!r}")
    if cls == "SKIPPED":
        errors.append(f"{label}: SKIPPED must never be PASS")

    # Semantic contradictions
    if cls == "OBSERVED_PASS":
        ec = data.get("exit_code")
        if ec not in (0, "0", "NONZERO_EXPECTED", "NOT_APPLICABLE_WITH_REASON"):
            errors.append(f"{label}: OBSERVED_PASS with unexpected exit_code={ec!r}")

    # Trusted CI identity
    tsha = str(data.get("tested_commit_sha", ""))
    rid = str(data.get("run_id", ""))
    if require_ci_identity:
        if not re.fullmatch(r"[0-9a-f]{40}", tsha):
            errors.append(f"{label}: tested_commit_sha not full 40-hex in CI")
        gsha = os.environ.get("GITHUB_SHA", "")
        if gsha and tsha != gsha:
            errors.append(f"{label}: tested_commit_sha != GITHUB_SHA")
        if tsha in {"LOCAL_UNKNOWN", "LOCAL_NOT_CI"}:
            errors.append(f"{label}: LOCAL identity rejected in CI")
        if not re.fullmatch(r"[0-9]+", rid):
            errors.append(f"{label}: run_id must be numeric GITHUB_RUN_ID in CI")
        if rid == "LOCAL_NOT_CI":
            errors.append(f"{label}: LOCAL_NOT_CI rejected in CI")
        grid = os.environ.get("GITHUB_RUN_ID", "")
        if grid and rid != grid:
            errors.append(f"{label}: run_id != GITHUB_RUN_ID")
    else:
        if tsha == "LOCAL_UNKNOWN" and require_ci_identity:
            errors.append(f"{label}: LOCAL_UNKNOWN")

    # Contract binding
    if data.get("contract_sha256") != CONTRACT_SHA256:
        errors.append(f"{label}: contract_sha256 mismatch")
    if data.get("parent_e02_final_commit_sha") != PARENT_E02:
        errors.append(f"{label}: parent_e02_final_commit_sha mismatch")

    # Timestamp
    ts = data.get("timestamp_utc")
    try:
        datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        errors.append(f"{label}: invalid timestamp_utc")

    # Paths
    for ep in data.get("evidence_files") or []:
        if not isinstance(ep, str):
            errors.append(f"{label}: evidence_files entry not string")
            continue
        if ep.startswith("/") or ".." in ep.split("/") or ep.startswith("../"):
            errors.append(f"{label}: unsafe evidence path {ep!r}")
        if not ep.startswith("experiments/m102_f2b_bounded_e04/evidence/"):
            errors.append(f"{label}: evidence path outside allowlist {ep!r}")

    # Physical vs governance
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
        # allow NOT_APPLICABLE markers with reason embedded in value
        pass
    else:
        errors.append(f"{label}: unexpected execution_kind {kind!r}")

    # Redaction scan
    blob = json.dumps(data, default=str)
    leaks = _looks_secret(blob)
    if leaks:
        errors.append(f"{label}: potential secret patterns {leaks}")

    return errors


def validate_evidence_file(path: Path, *, require_ci_identity: bool | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    return validate_evidence_record(data, path=path, require_ci_identity=require_ci_identity)


def write_case_manifest(case_ids: list[str] | None = None, manifest_name: str = "EVIDENCE_CASE_SHA256SUMS.txt") -> tuple[Path, str]:
    """Write external SHA-256 manifest over final case JSON bytes (no self-hash)."""
    ids = case_ids or REQUIRED_CASE_IDS
    lines: list[str] = []
    for case_id in ids:
        p = EVIDENCE / f"{case_id}.json"
        if not p.is_file() or p.is_symlink():
            raise FileNotFoundError(f"missing regular evidence file for {case_id}")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        # canonical repo-relative path
        rel = f"experiments/m102_f2b_bounded_e04/evidence/{case_id}.json"
        lines.append(f"{digest}  {rel}")
    path = EVIDENCE / manifest_name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, manifest_digest


def verify_case_manifest(manifest_path: Path, *, require_ci_identity: bool = True) -> list[str]:
    """Independent read-back verification of the 19-case digest manifest."""
    errors: list[str] = []
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"manifest missing or symlink: {manifest_path}"]
    text = manifest_path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
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
        if rel in entries:
            errors.append(f"duplicate manifest path {rel}")
        entries[rel] = digest

    expected_rels = {f"experiments/m102_f2b_bounded_e04/evidence/{i}.json" for i in REQUIRED_CASE_IDS}
    if set(entries) != expected_rels:
        errors.append(
            f"manifest path set mismatch: missing={sorted(expected_rels-set(entries))} "
            f"extra={sorted(set(entries)-expected_rels)}"
        )

    for rel, digest in entries.items():
        # resolve under repo root = parents of EXP_ROOT's parent? EXP_ROOT is e04 package
        repo_root = EXP_ROOT.parents[1]
        fp = repo_root / rel
        if fp.is_symlink():
            errors.append(f"symlink refused: {rel}")
            continue
        if not fp.is_file():
            errors.append(f"missing file for manifest entry: {rel}")
            continue
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"hash mismatch for {rel}")
        errors.extend(validate_evidence_file(fp, require_ci_identity=require_ci_identity))

    # Ensure no OBSERVED_PASS that is UNVERIFIED etc already handled; also reject any FAIL as overall if desired by caller
    return errors
