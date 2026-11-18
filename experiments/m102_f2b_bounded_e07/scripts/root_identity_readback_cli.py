#!/usr/bin/env python3
"""Zero-write root identity / provider binding check."""
from __future__ import annotations
import argparse, hashlib, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    AUX_MANIFEST_NAME, PRIMARY_MANIFEST_NAME, ROOT_DIGEST_NAME,
    cli_result, emit_cli, verify_root_digests,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    edir = args.evidence_dir
    primary = edir / PRIMARY_MANIFEST_NAME
    aux = edir / AUX_MANIFEST_NAME
    side = edir / "EVIDENCE_CASE_MANIFEST_DIGEST.txt"
    if not primary.is_file() or not aux.is_file() or not side.is_file():
        return emit_cli(cli_result(False, ["ROOT_IDENTITY"], errors=["missing primary/aux/digest"]))
    primary_digest = side.read_text().strip()
    aux_digest = hashlib.sha256(aux.read_bytes()).hexdigest()
    require_ci = bool(os.environ.get("GITHUB_RUN_ID"))
    errors = verify_root_digests(
        edir / ROOT_DIGEST_NAME,
        primary_digest=primary_digest,
        aux_digest=aux_digest,
        require_ci_identity=require_ci,
    )
    codes = ["ROOT_IDENTITY"] if errors else []
    return emit_cli(cli_result(not errors, codes, error_count=len(errors), errors=errors[:20]))

if __name__ == "__main__":
    raise SystemExit(main())
