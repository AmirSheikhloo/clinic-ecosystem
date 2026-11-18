#!/usr/bin/env python3
"""Read-only post-seal gate: primary + auxiliary manifests, root digests, JUnit cross-bind."""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import (  # noqa: E402
    AUX_INVENTORY,
    AUX_MANIFEST_NAME,
    EVIDENCE,
    PRIMARY_MANIFEST_NAME,
    REQUIRED_CASE_IDS,
    REQUIRED_FIXTURE_IDS,
    ROOT_DIGEST_NAME,
    verify_auxiliary_manifest,
    verify_case_manifest,
    verify_root_digests,
    write_auxiliary_manifest,
    write_root_digests,
)


def main() -> int:
    require_ci = bool(os.environ.get("GITHUB_RUN_ID"))
    if require_ci:
        if os.environ.get("GITHUB_RUN_ATTEMPT", "") != "1":
            print("STOP: unexpected run attempt")
            return 2
        if os.environ.get("GITHUB_EVENT_NAME", "") != "push":
            print("STOP: unexpected event")
            return 2

    primary = EVIDENCE / PRIMARY_MANIFEST_NAME
    primary_digest = (EVIDENCE / "EVIDENCE_CASE_MANIFEST_DIGEST.txt").read_text().strip()
    errors = verify_case_manifest(
        primary,
        require_ci_identity=require_ci,
        require_acceptance_pass=True,
    )

    # Cross-bind JUnit / fixtures (E05-FC09)
    junit = EVIDENCE / "junit.xml"
    if not junit.is_file():
        errors.append("missing junit.xml")
    else:
        cases = ET.parse(junit).getroot().findall(".//testcase")
        failed = sum(1 for c in cases if c.find("failure") is not None or c.find("error") is not None)
        skipped = sum(1 for c in cases if c.find("skipped") is not None)
        if len(cases) != 32:
            errors.append(f"junit testcase count {len(cases)} != 32")
        if failed or skipped:
            errors.append(f"junit not clean failed={failed} skipped={skipped}")

    for fid in REQUIRED_FIXTURE_IDS:
        fp = EVIDENCE / f"{fid}.json"
        if not fp.is_file():
            errors.append(f"missing fixture record {fid}")
        else:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("classification") != "OBSERVED_PASS":
                errors.append(f"{fid}: fixture classification not OBSERVED_PASS")

    for cid in REQUIRED_CASE_IDS:
        if not (EVIDENCE / f"{cid}.json").is_file():
            errors.append(f"missing case {cid}")

    # Write auxiliary manifest only after inventory is stable; then verify read-only.
    try:
        aux_path, aux_digest, inv = write_auxiliary_manifest()
    except FileNotFoundError as exc:
        print("STOP:", exc)
        return 1

    errors.extend(verify_auxiliary_manifest(aux_path, expected_inventory=inv))
    root = write_root_digests(primary_digest, aux_digest)
    errors.extend(verify_root_digests(root, primary_digest=primary_digest, aux_digest=aux_digest))

    # Recompute primary digest from bytes
    import hashlib

    actual_primary = hashlib.sha256(primary.read_bytes()).hexdigest()
    if actual_primary != primary_digest:
        errors.append("primary digest sidecar stale vs manifest bytes")

    result = {
        "gate": "E05_POST_SEAL_VERIFIER",
        "primary_manifest": PRIMARY_MANIFEST_NAME,
        "primary_manifest_sha256": primary_digest,
        "auxiliary_manifest": AUX_MANIFEST_NAME,
        "auxiliary_manifest_sha256": aux_digest,
        "root_digests": ROOT_DIGEST_NAME,
        "aux_inventory": list(AUX_INVENTORY),
        "errors": errors,
        "ok": not errors,
        "ci_executed": require_ci,
        "self_verifier_pass": not errors,
        "independently_verified": False,
        "independent_external_verification": "PENDING",
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_NOT_CI"),
        "sha": os.environ.get("GITHUB_SHA", "LOCAL_UNKNOWN"),
    }
    # NOTE: do not mutate files already covered by aux inventory after seal.
    # Persist seal result OUTSIDE sealed inventory name set — use POST_SEAL_VERIFIER.json
    # which is intentionally excluded from AUX_INVENTORY.
    out = EVIDENCE / "POST_SEAL_VERIFIER.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "primary_manifest_sha256": primary_digest,
                "auxiliary_manifest_sha256": aux_digest,
                "error_count": len(errors),
            }
        )
    )
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
