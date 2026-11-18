#!/usr/bin/env python3
"""Read-only primary acceptance CLI (same options for CI and disposable tamper tests)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import verify_case_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument(
        "--path-prefix",
        default="experiments/m102_f2b_bounded_e06/evidence/",
    )
    args = ap.parse_args()

    require_ci = bool(os.environ.get("GITHUB_RUN_ID"))
    errors = verify_case_manifest(
        args.manifest,
        require_ci_identity=require_ci,
        require_acceptance_pass=True,
        evidence_dir=args.evidence_dir,
        path_prefix=args.path_prefix,
    )
    print(json.dumps({"ok": not errors, "error_count": len(errors), "errors": errors[:30]}))
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
