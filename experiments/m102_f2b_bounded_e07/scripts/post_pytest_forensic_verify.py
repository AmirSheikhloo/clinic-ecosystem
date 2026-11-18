#!/usr/bin/env python3
"""CI Step 2 orchestrator: primary seal writer then zero-write primary_verify_cli; stdout captured by CI."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import EVIDENCE, REQUIRED_CASE_IDS, write_case_manifest  # noqa: E402
PRIMARY = ROOT / "scripts" / "primary_verify_cli.py"

def main() -> int:
    if os.environ.get("GITHUB_RUN_ID"):
        if os.environ.get("GITHUB_RUN_ATTEMPT", "") != "1":
            print(json.dumps({"ok": False, "error_codes": ["ATTEMPT_DENIED"]}))
            return 2
        if os.environ.get("GITHUB_EVENT_NAME", "") != "push":
            print(json.dumps({"ok": False, "error_codes": ["EVENT_DENIED"]}))
            return 2
    missing = [i for i in REQUIRED_CASE_IDS if not (EVIDENCE / f"{i}.json").is_file()]
    if missing:
        print(json.dumps({"ok": False, "error_codes": ["MISSING_CASES"], "missing": missing}))
        return 1
    man, digest = write_case_manifest()
    (EVIDENCE / "EVIDENCE_CASE_MANIFEST_DIGEST.txt").write_text(digest + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(PRIMARY), "--evidence-dir", str(EVIDENCE), "--manifest", str(man)],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")
    # CI shell is responsible for redirecting stdout into evidence/POST_PYTEST_FORENSIC_VERIFIER.json
    # This script also writes a stable JSON summary for local convenience when not redirected.
    result = {
        "gate": "E07_POST_PYTEST_FORENSIC_VERIFIER",
        "manifest": str(man),
        "manifest_sha256": digest,
        "cli_exit": proc.returncode,
        "ok": proc.returncode == 0,
        "independent_external_verification": "PENDING",
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
        "sha": os.environ.get("GITHUB_SHA", "LOCAL_UNKNOWN"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "LOCAL_NOT_CI"),
        "primary_stdout": proc.stdout,
    }
    # Write BEFORE aux seal (Step 2 output is part of frozen inventory)
    (EVIDENCE / "POST_PYTEST_FORENSIC_VERIFIER.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if proc.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
