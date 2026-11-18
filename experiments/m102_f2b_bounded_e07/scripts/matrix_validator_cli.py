#!/usr/bin/env python3
"""Zero-write FC matrix schema/receipt/detector authentication."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import FC_MATRIX_NAME, cli_result, emit_cli, validate_fc_proof_matrix  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--matrix", type=Path, default=None)
    args = ap.parse_args()
    path = args.matrix or (args.evidence_dir / FC_MATRIX_NAME)
    errors = validate_fc_proof_matrix(path)
    codes = []
    for e in errors:
        for c in ("EXPECTED_EXIT_CONTRADICTION", "WRONG_GATE_FAMILY", "DETECTOR_OR_RECEIPT_MISMATCH"):
            if c in e and c not in codes:
                codes.append(c)
    if errors and not codes:
        codes.append("MATRIX_INVALID")
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:30]))

if __name__ == "__main__":
    raise SystemExit(main())
