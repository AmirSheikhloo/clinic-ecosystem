#!/usr/bin/env python3
"""ZERO-WRITE post-seal verifier composing all seven mandatory subgates. No evidence/ writes."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    AUX_MANIFEST_NAME, PRIMARY_MANIFEST_NAME, ROOT_DIGEST_NAME,
    cli_result, emit_cli,
)

SCRIPTS = ROOT / "scripts"

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    edir = args.evidence_dir.resolve()
    # Hard guarantee: never write into evidence_dir
    errors = []
    codes = []

    def sub(name: str, argv: list[str]) -> None:
        nonlocal errors, codes
        proc = _run(argv)
        sys.stderr.write(proc.stderr or "")
        if proc.returncode != 0:
            errors.append(f"{name} rc={proc.returncode}")
            # parse codes from stdout JSON lines
            for line in (proc.stdout or "").splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        import json
                        obj = json.loads(line)
                        for c in obj.get("error_codes") or []:
                            if c not in codes:
                                codes.append(c)
                    except Exception:
                        pass
            if not codes:
                codes.append(f"{name.upper()}_FAILED")
        # still print child stdout for receipt capture when used as subgate
        sys.stdout.write(proc.stdout or "")

    # 1 primary
    sub("primary_verify_cli", [
        sys.executable, str(SCRIPTS/"primary_verify_cli.py"),
        "--evidence-dir", str(edir), "--manifest", str(edir/PRIMARY_MANIFEST_NAME),
    ])
    # 2 aux integrity
    sub("aux_integrity_readback_cli", [
        sys.executable, str(SCRIPTS/"aux_integrity_readback_cli.py"),
        "--evidence-dir", str(edir),
    ])
    # 3 aux redaction
    sub("aux_redaction_readback_cli", [
        sys.executable, str(SCRIPTS/"aux_redaction_readback_cli.py"),
        "--evidence-dir", str(edir),
    ])
    # 4 junit+fixture
    sub("junit_and_fixture_identity_readback_cli", [
        sys.executable, str(SCRIPTS/"junit_and_fixture_identity_readback_cli.py"),
        "--evidence-dir", str(edir),
    ])
    # 5 matrix
    sub("matrix_validator_cli", [
        sys.executable, str(SCRIPTS/"matrix_validator_cli.py"),
        "--evidence-dir", str(edir),
    ])
    # 6 closure judgments
    sub("closure_judgments_validator_cli", [
        sys.executable, str(SCRIPTS/"closure_judgments_validator_cli.py"),
        "--evidence-dir", str(edir),
    ])
    # 7 root identity
    sub("root_identity_readback_cli", [
        sys.executable, str(SCRIPTS/"root_identity_readback_cli.py"),
        "--evidence-dir", str(edir),
    ])

    # Do not write POST_SEAL_VERIFIER.json into evidence — stdout only
    result = cli_result(not errors, codes, error_count=len(errors), errors=errors[:30],
                        zero_write=True, composed_subgates=7)
    # final emit (may duplicate child lines — that's ok for CI tee outside evidence)
    print(json.dumps({"post_seal_summary": result}, sort_keys=True))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
