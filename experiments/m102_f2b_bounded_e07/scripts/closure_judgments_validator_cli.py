#!/usr/bin/env python3
"""Zero-write E07 closure judgments validator."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import CLOSURE_JUDGMENTS_NAME, cli_result, emit_cli, validate_closure_judgments  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--judgments", type=Path, default=None)
    args = ap.parse_args()
    path = args.judgments or (args.evidence_dir / CLOSURE_JUDGMENTS_NAME)
    errors = validate_closure_judgments(path)
    codes = ["CLOSURE_JUDGMENT_INVALID"] if errors else []
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
