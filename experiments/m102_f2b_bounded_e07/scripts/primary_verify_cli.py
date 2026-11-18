#!/usr/bin/env python3
"""Zero-write primary acceptance CLI."""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    cli_result, emit_cli, verify_case_manifest,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--path-prefix", default="experiments/m102_f2b_bounded_e07/evidence/")
    args = ap.parse_args()
    require_ci = bool(os.environ.get("GITHUB_RUN_ID"))
    errors = verify_case_manifest(
        args.manifest,
        require_ci_identity=require_ci,
        require_acceptance_pass=True,
        evidence_dir=args.evidence_dir,
        path_prefix=args.path_prefix,
    )
    codes = []
    for e in errors:
        for c in ("ACCEPTANCE_NOT_OBSERVED_PASS","CASE_MAP_MISMATCH","LINEAGE_MISMATCH","TYPE_OR_UTC",
                  "EVIDENCE_OWNERSHIP","SECRET_PATTERN","PRIMARY_HASH_MISMATCH"):
            if e.startswith(c) or c in e:
                if c not in codes:
                    codes.append(c)
                break
        else:
            if "PRIMARY_VERIFY" not in codes:
                codes.append("PRIMARY_VERIFY_FAILED")
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
