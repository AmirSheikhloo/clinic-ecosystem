#!/usr/bin/env python3
"""Zero-write recursive redaction scan of sealed auxiliary inventory."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    FROZEN_AUX_INVENTORY, cli_result, emit_cli, scan_sealed_tree_for_secrets,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    errors = scan_sealed_tree_for_secrets(args.evidence_dir, list(FROZEN_AUX_INVENTORY))
    codes = ["SECRET_PATTERN"] if errors else []
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
