#!/usr/bin/env python3
"""Disposable job-equivalent gate sequence for V13 (pytest green + forensic red => nonzero)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import verify_case_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pytest-rc", type=int, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--require-acceptance", type=int, default=1)
    args = ap.parse_args()

    # Mimic `set -euo pipefail`: stop on pytest failure first.
    if args.pytest_rc != 0:
        print(f"pytest_rc={args.pytest_rc}")
        return args.pytest_rc

    errors = verify_case_manifest(
        args.manifest,
        require_ci_identity=False,
        require_acceptance_pass=bool(args.require_acceptance),
        evidence_dir=args.evidence_dir,
    )
    if errors:
        print(f"forensic_errors={len(errors)}")
        for e in errors[:20]:
            print("ERROR:", e)
        return 1
    print("forensic_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
