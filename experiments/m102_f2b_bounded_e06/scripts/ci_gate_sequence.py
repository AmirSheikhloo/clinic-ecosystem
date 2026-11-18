#!/usr/bin/env python3
"""Job-equivalent gate sequence for V13 (pytest green + forensic red => nonzero)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "scripts" / "primary_verify_cli.py"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pytest-rc", type=int, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()

    if args.pytest_rc != 0:
        print(f"pytest_rc={args.pytest_rc}")
        return args.pytest_rc

    proc = subprocess.run(
        [
            sys.executable,
            str(PRIMARY),
            "--evidence-dir",
            str(args.evidence_dir),
            "--manifest",
            str(args.manifest),
        ],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")
    if proc.returncode != 0:
        print(f"forensic_rc={proc.returncode}")
        return proc.returncode
    print("forensic_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
