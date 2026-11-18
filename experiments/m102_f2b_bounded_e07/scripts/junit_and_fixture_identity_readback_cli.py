#!/usr/bin/env python3
"""Zero-write JUnit allowlist + 14-fixture provenance binding."""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    cli_result, emit_cli, verify_fixture_provenance, verify_junit_allowlist,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--mode", choices=["all", "junit", "fixture"], default="all")
    args = ap.parse_args()
    require_ci = bool(os.environ.get("GITHUB_RUN_ID"))
    errors = []
    if args.mode in ("all", "junit"):
        errors.extend(verify_junit_allowlist(args.evidence_dir / "junit.xml"))
    if args.mode in ("all", "fixture"):
        errors.extend(verify_fixture_provenance(args.evidence_dir, require_ci_identity=require_ci))
    codes = []
    for e in errors:
        if e.startswith("JUNIT_ALLOWLIST") and "JUNIT_ALLOWLIST" not in codes:
            codes.append("JUNIT_ALLOWLIST")
        elif e.startswith("FIXTURE_PROVENANCE_MISMATCH") and "FIXTURE_PROVENANCE_MISMATCH" not in codes:
            codes.append("FIXTURE_PROVENANCE_MISMATCH")
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
