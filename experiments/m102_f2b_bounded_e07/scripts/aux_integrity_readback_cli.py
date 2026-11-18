#!/usr/bin/env python3
"""Zero-write auxiliary integrity readback."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    AUX_MANIFEST_NAME, FROZEN_AUX_INVENTORY, cli_result, emit_cli, verify_auxiliary_manifest,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    errors = verify_auxiliary_manifest(
        args.evidence_dir / AUX_MANIFEST_NAME,
        evidence_dir=args.evidence_dir,
        expected_inventory=list(FROZEN_AUX_INVENTORY),
    )
    codes = []
    for e in errors:
        if "AUX_INVENTORY_MISSING" in e and "AUX_INVENTORY_MISSING" not in codes:
            codes.append("AUX_INVENTORY_MISSING")
        elif "AUX_HASH_MISMATCH" in e and "AUX_HASH_MISMATCH" not in codes:
            codes.append("AUX_HASH_MISMATCH")
        elif "AUX_INTEGRITY" not in codes:
            codes.append("AUX_INTEGRITY_FAILED")
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
