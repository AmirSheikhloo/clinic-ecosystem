#!/usr/bin/env python3
"""WRITE-ONLY seal writer: builds aux manifest + root digests. Never used for verification."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.evidence import (  # noqa: E402
    FROZEN_AUX_INVENTORY, PRIMARY_MANIFEST_NAME, cli_result, emit_cli,
    write_auxiliary_manifest, write_root_digests,
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    edir = args.evidence_dir
    side = edir / "EVIDENCE_CASE_MANIFEST_DIGEST.txt"
    primary = edir / PRIMARY_MANIFEST_NAME
    if not side.is_file() or not primary.is_file():
        return emit_cli(cli_result(False, ["SEAL_WRITER_FAILED"], errors=["missing primary digest"]))
    primary_digest = side.read_text().strip()
    actual = hashlib.sha256(primary.read_bytes()).hexdigest()
    if actual != primary_digest:
        return emit_cli(cli_result(False, ["SEAL_WRITER_FAILED"], errors=["primary digest stale"]))
    try:
        aux_path, aux_digest, inv = write_auxiliary_manifest(
            evidence_dir=edir, inventory=list(FROZEN_AUX_INVENTORY)
        )
    except FileNotFoundError as exc:
        return emit_cli(cli_result(False, ["AUX_INVENTORY_MISSING"], errors=[str(exc)]))
    root = write_root_digests(primary_digest, aux_digest, evidence_dir=edir)
    return emit_cli(cli_result(True, [], aux=str(aux_path), aux_sha256=aux_digest, root=str(root), inventory_count=len(inv)))

if __name__ == "__main__":
    raise SystemExit(main())
