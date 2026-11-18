#!/usr/bin/env python3
"""CI post-pytest primary gate — writes manifest then invokes primary_verify_cli."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import (  # noqa: E402
    EVIDENCE,
    REQUIRED_CASE_IDS,
    write_case_manifest,
)

PRIMARY = ROOT / "scripts" / "primary_verify_cli.py"


def main() -> int:
    if os.environ.get("GITHUB_RUN_ID"):
        if os.environ.get("GITHUB_RUN_ATTEMPT", "") != "1":
            print("STOP: unexpected GITHUB_RUN_ATTEMPT")
            return 2
        if os.environ.get("GITHUB_EVENT_NAME", "") != "push":
            print("STOP: unexpected GITHUB_EVENT_NAME")
            return 2

    missing = [i for i in REQUIRED_CASE_IDS if not (EVIDENCE / f"{i}.json").is_file()]
    if missing:
        print("STOP: missing case JSON:", missing)
        return 1

    man, digest = write_case_manifest()
    (EVIDENCE / "EVIDENCE_CASE_MANIFEST_DIGEST.txt").write_text(digest + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(PRIMARY),
            "--evidence-dir",
            str(EVIDENCE),
            "--manifest",
            str(man),
        ],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")
    result = {
        "gate": "E06_POST_PYTEST_FORENSIC_VERIFIER",
        "manifest": str(man),
        "manifest_sha256": digest,
        "cli_exit": proc.returncode,
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
        "sha": os.environ.get("GITHUB_SHA", "LOCAL_UNKNOWN"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "LOCAL_NOT_CI"),
        "ok": proc.returncode == 0,
        "independent_external_verification": "PENDING",
    }
    (EVIDENCE / "POST_PYTEST_FORENSIC_VERIFIER.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
