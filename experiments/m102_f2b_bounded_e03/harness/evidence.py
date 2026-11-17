"""E0.3 §6 evidence schema helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXP_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = EXP_ROOT / "evidence"

CONTRACT_SHA256 = "b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28"
PARENT_E02 = "471f88417bfcf69ce864b333114e7fb0f777ede0"

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
}


def tested_commit_sha() -> str:
    return os.environ.get("GITHUB_SHA") or os.environ.get("E03_TESTED_COMMIT_SHA") or "LOCAL_UNKNOWN"


def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or "LOCAL_NOT_CI"


def write_evidence(case_id: str, payload: dict[str, Any]) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    base = {
        "case_id": case_id,
        "contract_sha256": CONTRACT_SHA256,
        "parent_e02_final_commit_sha": PARENT_E02,
        "tested_commit_sha": tested_commit_sha(),
        "run_id": run_id(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_files": [f"experiments/m102_f2b_bounded_e03/evidence/{case_id}.json"],
        "limitations": payload.get("limitations")
        or ["Synthetic experiment only; not real Cloud/Local Sync proof."],
    }
    merged = {**base, **payload, **{"case_id": case_id}}
    path = EVIDENCE / f"{case_id}.json"
    path.write_text(json.dumps(merged, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def validate_evidence_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name}: unreadable JSON: {exc}"]
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] in (None, ""):
            errors.append(f"{path.name}: missing {field}")
    cls = data.get("classification")
    if cls not in ALLOWED_CLASSIFICATIONS and cls != "EXECUTED_E03":
        # EXECUTED_E03 may appear as a tag; require OBSERVED_* as primary
        if cls not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{path.name}: invalid classification {cls!r}")
    if data.get("classification") == "SKIPPED":
        errors.append(f"{path.name}: SKIPPED must never be PASS")
    return errors
