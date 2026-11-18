#!/usr/bin/env python3
"""Read-only post-seal gate for E0.6."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import (  # noqa: E402
    AUX_MANIFEST_NAME,
    EVIDENCE,
    PRIMARY_MANIFEST_NAME,
    REQUIRED_CASE_IDS,
    REQUIRED_FIXTURE_IDS,
    ROOT_DIGEST_NAME,
    scan_sealed_tree_for_secrets,
    validate_fc_proof_matrix,
    verify_auxiliary_manifest,
    verify_case_manifest,
    verify_junit_allowlist,
    verify_root_digests,
    write_auxiliary_manifest,
    write_root_digests,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    ap.add_argument("--skip-matrix-validate", default="0")
    ap.add_argument("--reuse-existing-seal", default="0")
    args = ap.parse_args()
    edir = args.evidence_dir
    require_ci = bool(os.environ.get("GITHUB_RUN_ID")) and edir.resolve() == EVIDENCE.resolve()

    if require_ci:
        if os.environ.get("GITHUB_RUN_ATTEMPT", "") != "1":
            print("STOP: unexpected run attempt")
            return 2
        if os.environ.get("GITHUB_EVENT_NAME", "") != "push":
            print("STOP: unexpected event")
            return 2

    primary = edir / PRIMARY_MANIFEST_NAME
    digest_side = edir / "EVIDENCE_CASE_MANIFEST_DIGEST.txt"
    if not digest_side.is_file():
        print("STOP: missing primary digest sidecar")
        return 1
    primary_digest = digest_side.read_text().strip()

    errors = verify_case_manifest(
        primary,
        require_ci_identity=require_ci,
        require_acceptance_pass=True,
        evidence_dir=edir,
    )
    errors.extend(verify_junit_allowlist(edir / "junit.xml"))

    for fid in REQUIRED_FIXTURE_IDS:
        fp = edir / f"{fid}.json"
        if not fp.is_file():
            errors.append(f"missing fixture {fid}")
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("classification") != "OBSERVED_PASS":
            errors.append(f"{fid}: not OBSERVED_PASS")
        if require_ci:
            if str(data.get("run_id")) != os.environ.get("GITHUB_RUN_ID"):
                errors.append(f"{fid}: run_id mismatch")
            if str(data.get("tested_commit_sha")) != os.environ.get("GITHUB_SHA"):
                errors.append(f"{fid}: sha mismatch")

    for cid in REQUIRED_CASE_IDS:
        if not (edir / f"{cid}.json").is_file():
            errors.append(f"missing case {cid}")

    if args.skip_matrix_validate != "1":
        errors.extend(validate_fc_proof_matrix(edir / "E06_FC_PROOF_MATRIX.json"))

    if args.reuse_existing_seal == "1":
        aux_path = edir / AUX_MANIFEST_NAME
        aux_digest = hashlib.sha256(aux_path.read_bytes()).hexdigest() if aux_path.is_file() else ""
        inv = None
        # reconstruct inventory from aux file
        if aux_path.is_file():
            inv = []
            for line in aux_path.read_text().splitlines():
                parts = line.split()
                if len(parts) == 2:
                    inv.append(parts[1].split("/evidence/", 1)[-1])
        else:
            errors.append("missing aux for reuse")
            inv = []
    else:
        try:
            aux_path, aux_digest, inv = write_auxiliary_manifest(evidence_dir=edir)
        except FileNotFoundError as exc:
            print("STOP:", exc)
            return 1
        write_root_digests(primary_digest, aux_digest, evidence_dir=edir)

    errors.extend(verify_auxiliary_manifest(aux_path, evidence_dir=edir, expected_inventory=inv))
    errors.extend(
        verify_root_digests(
            edir / ROOT_DIGEST_NAME,
            primary_digest=primary_digest,
            aux_digest=aux_digest,
            require_ci_identity=require_ci,
        )
    )
    if inv:
        errors.extend(scan_sealed_tree_for_secrets(edir, inv))

    actual_primary = hashlib.sha256(primary.read_bytes()).hexdigest()
    if actual_primary != primary_digest:
        errors.append("primary digest sidecar stale")

    result = {
        "gate": "E06_POST_SEAL_VERIFIER",
        "primary_manifest_sha256": primary_digest,
        "auxiliary_manifest_sha256": aux_digest,
        "aux_inventory": inv,
        "errors": errors,
        "ok": not errors,
        "ci_executed": require_ci,
        "self_verifier_pass": not errors,
        "independently_verified": False,
        "independent_external_verification": "PENDING",
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
        "sha": os.environ.get("GITHUB_SHA", "LOCAL_UNKNOWN"),
    }
    # Outside sealed inventory
    (edir / "POST_SEAL_VERIFIER.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "error_count": len(errors), "primary": primary_digest, "aux": aux_digest}))
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
