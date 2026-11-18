#!/usr/bin/env python3
"""Job-equivalent gate: pytest_rc==0 then primary_verify_cli."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "scripts" / "primary_verify_cli.py"
sys.path.insert(0, str(ROOT))
from harness.evidence import cli_result, emit_cli  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pytest-rc", type=int, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    if args.pytest_rc != 0:
        return emit_cli(cli_result(False, ["JOB_EQ_NONZERO"], pytest_rc=args.pytest_rc))
    proc = subprocess.run(
        [sys.executable, str(PRIMARY), "--evidence-dir", str(args.evidence_dir), "--manifest", str(args.manifest)],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout or "")
    if proc.returncode != 0:
        codes = ["JOB_EQ_NONZERO"]
        if "PRIMARY_HASH_MISMATCH" in (proc.stdout or ""):
            codes.append("PRIMARY_HASH_MISMATCH")
        return emit_cli(cli_result(False, codes, forensic_rc=proc.returncode))
    return emit_cli(cli_result(True, []))

if __name__ == "__main__":
    raise SystemExit(main())
