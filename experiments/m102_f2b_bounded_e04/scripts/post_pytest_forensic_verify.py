#!/usr/bin/env python3
"""Independent post-pytest forensic gate for E0.4 (must fail CI if red)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import (  # noqa: E402
    EVIDENCE,
    REQUIRED_CASE_IDS,
    verify_case_manifest,
    write_case_manifest,
)


def main() -> int:
    if not os.environ.get("GITHUB_RUN_ID"):
        print("WARNING: not in GitHub Actions; still verifying with require_ci_identity=False")
        require_ci = False
    else:
        require_ci = True
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        if attempt and attempt != "1":
            print(f"STOP: unexpected GITHUB_RUN_ATTEMPT={attempt}")
            return 2
        event = os.environ.get("GITHUB_EVENT_NAME", "")
        if event and event != "push":
            print(f"STOP: unexpected GITHUB_EVENT_NAME={event}")
            return 2

    # Ensure manifest exists over current stable 19 JSON bytes
    missing = [i for i in REQUIRED_CASE_IDS if not (EVIDENCE / f"{i}.json").is_file()]
    if missing:
        print("STOP: missing case JSON:", missing)
        return 1

    man, digest = write_case_manifest()
    errors = verify_case_manifest(man, require_ci_identity=require_ci)
    result = {
        "gate": "E04_POST_PYTEST_FORENSIC_VERIFIER",
        "manifest": str(man.relative_to(ROOT.parents[1])) if False else str(man),
        "manifest_sha256": digest,
        "errors": errors,
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
        "sha": os.environ.get("GITHUB_SHA", "LOCAL_UNKNOWN"),
        "ok": not errors,
    }
    out = EVIDENCE / "POST_PYTEST_FORENSIC_VERIFIER.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "EVIDENCE_CASE_MANIFEST_DIGEST.txt").write_text(digest + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "manifest_sha256": digest, "error_count": len(errors)}))
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
