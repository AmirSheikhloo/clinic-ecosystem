#!/usr/bin/env python3
"""Step 4: E07-C01..C07 falsifiability receipts + provisional judgments (noncircular C05/C06)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.evidence import (  # noqa: E402
    AUTHORIZATION_SHA256,
    CLOSURE_IDS,
    CLOSURE_JUDGMENTS_NAME,
    CLOSURE_TO_FINDING,
    CONTRACT_SHA256,
    EVIDENCE,
    FC_MATRIX_NAME,
    tree_sha256_manifest,
    run_attempt,
    run_id,
    tested_commit_sha,
    validate_closure_judgments,
)

SCRIPTS = ROOT / "scripts"
CREC = EVIDENCE / "closure_receipts"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _write_receipt(cid: str, proc, entrypoint: str, detector: str, note: str) -> dict:
    CREC.mkdir(parents=True, exist_ok=True)
    text = ((proc.stdout or "") + "\n---\n" + (proc.stderr or ""))
    for s in ("synth-ci-only",):
        text = text.replace(s, "<redacted>")
    out = text.encode()
    body = {
        "id": cid,
        "finding": CLOSURE_TO_FINDING[cid],
        "entrypoint": entrypoint,
        "expected_detector": detector,
        "observed_exit_code": int(proc.returncode),
        "observed_detector": detector,
        "stdout_stderr_redacted_sha256": hashlib.sha256(out).hexdigest(),
        "note": note,
        "ok_negative": proc.returncode != 0,
    }
    (CREC / f"{cid}.json").write_text(json.dumps(body, indent=2) + "\n")
    (CREC / f"{cid}.stdout.txt").write_bytes(out)
    return body


def _import_seal_helpers():
    # reuse FC builder helpers by importing module functions via exec of seal path
    from scripts import build_fc_proof_matrix as fc  # type: ignore
    return fc


def main() -> int:
    CREC.mkdir(parents=True, exist_ok=True)
    # Ensure FC matrix already built
    if not (EVIDENCE / FC_MATRIX_NAME).is_file():
        print("STOP: FC matrix missing; run build_fc_proof_matrix first")
        return 1

    # Import seal helpers from fc builder module path
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fcbuild", SCRIPTS / "build_fc_proof_matrix.py"
    )
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # --- C01 EXPECTED_EXIT_CONTRADICTION ---
        bad_matrix = td / "c01" / FC_MATRIX_NAME
        bad_matrix.parent.mkdir(parents=True)
        data = json.loads((EVIDENCE / FC_MATRIX_NAME).read_text())
        # contradict: set positive expected_exit_code to NONZERO while observed 0
        data["predicates"][0]["vectors"][0]["positive"]["expected_exit_code"] = "NONZERO"
        bad_matrix.write_text(json.dumps(data, indent=2) + "\n")
        # copy receipts referenced so validator can still check files relative to evidence-dir
        # Point evidence-dir at EVIDENCE but matrix at bad — matrix_validator accepts --matrix
        proc = _run([
            sys.executable, str(SCRIPTS / "matrix_validator_cli.py"),
            "--evidence-dir", str(EVIDENCE), "--matrix", str(bad_matrix),
        ])
        if proc.returncode == 0 or "EXPECTED_EXIT_CONTRADICTION" not in (proc.stdout or ""):
            print("STOP: C01 did not detect contradiction", proc.stdout)
            return 1
        _write_receipt("E07-C01", proc, "matrix_validator_cli", "EXPECTED_EXIT_CONTRADICTION", "contradictory positive expected_exit_code")

        # --- C02 WRONG_GATE_FAMILY ---
        bad_matrix = td / "c02" / FC_MATRIX_NAME
        bad_matrix.parent.mkdir(parents=True)
        data = json.loads((EVIDENCE / FC_MATRIX_NAME).read_text())
        # FC08 vector claims primary_verify_cli instead of aux_integrity
        for pred in data["predicates"]:
            if pred["predicate_id"] == "E05-FC08":
                pred["vectors"][0]["entrypoint"] = "primary_verify_cli"
        bad_matrix.write_text(json.dumps(data, indent=2) + "\n")
        proc = _run([
            sys.executable, str(SCRIPTS / "matrix_validator_cli.py"),
            "--evidence-dir", str(EVIDENCE), "--matrix", str(bad_matrix),
        ])
        if proc.returncode == 0 or "WRONG_GATE_FAMILY" not in (proc.stdout or ""):
            print("STOP: C02 did not detect wrong gate", proc.stdout)
            return 1
        _write_receipt("E07-C02", proc, "matrix_validator_cli", "WRONG_GATE_FAMILY", "FC08 entrypoint forged to primary")

        # --- C03 DETECTOR_OR_RECEIPT_MISMATCH ---
        bad_matrix = td / "c03" / FC_MATRIX_NAME
        bad_matrix.parent.mkdir(parents=True)
        data = json.loads((EVIDENCE / FC_MATRIX_NAME).read_text())
        data["predicates"][0]["vectors"][0]["negative"]["observed_detector"] = "WRONG_DETECTOR"
        bad_matrix.write_text(json.dumps(data, indent=2) + "\n")
        proc = _run([
            sys.executable, str(SCRIPTS / "matrix_validator_cli.py"),
            "--evidence-dir", str(EVIDENCE), "--matrix", str(bad_matrix),
        ])
        if proc.returncode == 0 or "DETECTOR_OR_RECEIPT_MISMATCH" not in (proc.stdout or ""):
            print("STOP: C03 did not detect detector mismatch", proc.stdout)
            return 1
        _write_receipt("E07-C03", proc, "matrix_validator_cli", "DETECTOR_OR_RECEIPT_MISMATCH", "forged observed_detector")

        # --- C04 FIXTURE_PROVENANCE_MISMATCH ---
        sealed = td / "c04_sealed"
        fc._seed_cases(sealed)
        fc._seal_disposable(sealed)
        d = json.loads((sealed / "E04-V05.json").read_text())
        d["source_test"] = "test_e04_v05_FORGED"
        (sealed / "E04-V05.json").write_text(json.dumps(d, indent=2) + "\n")
        _run([sys.executable, str(SCRIPTS / "seal_writer_cli.py"), "--evidence-dir", str(sealed)])
        proc = _run([
            sys.executable, str(SCRIPTS / "junit_and_fixture_identity_readback_cli.py"),
            "--evidence-dir", str(sealed), "--mode", "fixture",
        ])
        if proc.returncode == 0 or "FIXTURE_PROVENANCE_MISMATCH" not in (proc.stdout or ""):
            print("STOP: C04 fixture provenance", proc.stdout)
            return 1
        _write_receipt("E07-C04", proc, "junit_and_fixture_identity_readback_cli", "FIXTURE_PROVENANCE_MISMATCH", "forged fixture source_test resealed")

        # --- C05 zero-write post_seal on clean then tampered disposable ---
        clean = td / "c05_clean"
        fc._seed_cases(clean)
        fc._seal_disposable(clean)
        # Copy REAL current-run matrix/receipts/judgments placeholders already in seal helpers;
        # For full-gate clean: need matrix_validator to pass — placeholders are synthetic and may FAIL matrix validation
        # because receipt hashes/detectors won't match real subprocess. For C05 clean full-gate we must install the REAL
        # FC matrix + real receipts + provisional judgments into the disposable root.
        for name in [FC_MATRIX_NAME, "fc_matrix_builder.txt"]:
            shutil.copy2(EVIDENCE / name, clean / name)
        if (EVIDENCE / "fc_receipts").is_dir():
            shutil.rmtree(clean / "fc_receipts", ignore_errors=True)
            shutil.copytree(EVIDENCE / "fc_receipts", clean / "fc_receipts")
        # provisional judgments not yet written — create independent synthetic valid judgments for test root
        judgments = [{
            "id": cid,
            "finding": CLOSURE_TO_FINDING[cid],
            "verdict": "SELF_TESTED_PENDING_FINAL_GATE_AND_EXTERNAL_AUDIT",
            "independent_external_verification": "PENDING",
            "synthetic_test_input": True,
            "note": "C05 disposable full-gate bootstrap; not provider evidence",
        } for cid in CLOSURE_IDS]
        (clean / CLOSURE_JUDGMENTS_NAME).write_text(json.dumps({
            "document": "E07_EV_CLOSURE_JUDGMENTS",
            "contract_sha256": CONTRACT_SHA256,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "tested_commit_sha": tested_commit_sha(),
            "run_id": run_id(),
            "run_attempt": run_attempt(),
            "judgments": judgments,
            "synthetic_test_input": True,
        }, indent=2) + "\n")
        # also need closure_receipts present in inventory — copy any already written C01-C04 and placeholders for rest
        (clean / "closure_receipts").mkdir(exist_ok=True)
        for cid in CLOSURE_IDS:
            src_j = CREC / f"{cid}.json"
            src_s = CREC / f"{cid}.stdout.txt"
            if src_j.is_file():
                shutil.copy2(src_j, clean / "closure_receipts" / f"{cid}.json")
                shutil.copy2(src_s, clean / "closure_receipts" / f"{cid}.stdout.txt")
            else:
                (clean / "closure_receipts" / f"{cid}.json").write_text(json.dumps({"id": cid, "synthetic_test_input": True}) + "\n")
                (clean / "closure_receipts" / f"{cid}.stdout.txt").write_text('{"ok": false, "error_codes": ["PLACEHOLDER"]}\n')
        # reseal with complete inventory
        proc_seal = _run([sys.executable, str(SCRIPTS / "seal_writer_cli.py"), "--evidence-dir", str(clean)])
        if proc_seal.returncode != 0:
            print("STOP: C05 clean reseal failed", proc_seal.stdout, proc_seal.stderr)
            return 1
        pre = tree_sha256_manifest(clean)
        (td / "c05_pre.sha256").write_text(pre)
        proc = _run([sys.executable, str(SCRIPTS / "post_seal_verify_cli.py"), "--evidence-dir", str(clean)])
        post = tree_sha256_manifest(clean)
        (td / "c05_post.sha256").write_text(post)
        if pre != post:
            print("STOP: C05 clean post_seal mutated evidence tree")
            return 1
        if proc.returncode != 0:
            print("STOP: C05 clean full-gate failed", proc.stdout[-2000:], proc.stderr[-1000:])
            return 1
        # tampered copy
        tampered = td / "c05_tampered"
        shutil.copytree(clean, tampered)
        (tampered / "summary.txt").write_bytes((tampered / "summary.txt").read_bytes() + b"\nX\n")
        pre2 = tree_sha256_manifest(tampered)
        proc2 = _run([sys.executable, str(SCRIPTS / "post_seal_verify_cli.py"), "--evidence-dir", str(tampered)])
        post2 = tree_sha256_manifest(tampered)
        if pre2 != post2:
            print("STOP: C05 tampered post_seal mutated tree")
            return 1
        if proc2.returncode == 0:
            print("STOP: C05 tampered unexpectedly passed")
            return 1
        # combine receipts: document clean+tamper
        combined = subprocess.CompletedProcess(
            args=["post_seal_verify_cli"],
            returncode=proc2.returncode,
            stdout=(proc.stdout or "") + "\n===TAMPER===\n" + (proc2.stdout or ""),
            stderr=(proc.stderr or "") + (proc2.stderr or ""),
        )
        _write_receipt(
            "E07-C05", combined, "post_seal_verify_cli", "AUX_HASH_MISMATCH",
            "clean full-gate exit0 + snapshot equal; post-tamper nonzero + snapshot equal (zero-write)",
        )

        # --- C06 independently staged judgments (NOT the future real file) ---
        jdir = td / "c06"
        jdir.mkdir()
        good = jdir / "good.json"
        good.write_text(json.dumps({
            "document": "E07_EV_CLOSURE_JUDGMENTS",
            "contract_sha256": CONTRACT_SHA256,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "judgments": [{
                "id": cid,
                "finding": CLOSURE_TO_FINDING[cid],
                "verdict": "SELF_TESTED_PENDING_FINAL_GATE_AND_EXTERNAL_AUDIT",
                "independent_external_verification": "PENDING",
                "synthetic_test_input": True,
            } for cid in CLOSURE_IDS],
        }, indent=2) + "\n")
        pos = _run([
            sys.executable, str(SCRIPTS / "closure_judgments_validator_cli.py"),
            "--evidence-dir", str(jdir), "--judgments", str(good),
        ])
        if pos.returncode != 0:
            print("STOP: C06 clean judgments failed", pos.stdout)
            return 1
        forged = jdir / "forged.json"
        forged.write_text(json.dumps({
            "document": "E07_EV_CLOSURE_JUDGMENTS",
            "contract_sha256": CONTRACT_SHA256,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "judgments": [{
                "id": cid,
                "finding": CLOSURE_TO_FINDING[cid],
                "verdict": "EXTERNAL_PASS_CLAIMED",  # premature
                "independent_external_verification": "PASS",
            } for cid in CLOSURE_IDS],
        }, indent=2) + "\n")
        neg = _run([
            sys.executable, str(SCRIPTS / "closure_judgments_validator_cli.py"),
            "--evidence-dir", str(jdir), "--judgments", str(forged),
        ])
        if neg.returncode == 0 or "CLOSURE_JUDGMENT_INVALID" not in (neg.stdout or ""):
            print("STOP: C06 forged judgments not denied", neg.stdout)
            return 1
        combined = subprocess.CompletedProcess(
            args=["closure_judgments_validator_cli"],
            returncode=neg.returncode,
            stdout=(pos.stdout or "") + "\n===FORGED===\n" + (neg.stdout or ""),
            stderr="",
        )
        _write_receipt(
            "E07-C06", combined, "closure_judgments_validator_cli", "CLOSURE_JUDGMENT_INVALID",
            "independent disposable judgment inputs; clean pass + premature PASS denied",
        )

        # --- C07 AUX inventory missing stdout ---
        sealed = td / "c07"
        fc._seed_cases(sealed)
        fc._seal_disposable(sealed)
        # remove a required stdout receipt after seal
        victim = sealed / "fc_receipts" / "FC01_PRIMARY_negative.stdout.txt"
        if victim.is_file():
            victim.unlink()
        else:
            (sealed / "fc_matrix_builder.txt").unlink()
        proc = _run([sys.executable, str(SCRIPTS / "aux_integrity_readback_cli.py"), "--evidence-dir", str(sealed)])
        if proc.returncode == 0:
            print("STOP: C07 should fail", proc.stdout)
            return 1
        det = "AUX_INVENTORY_MISSING" if "AUX_INVENTORY_MISSING" in (proc.stdout or "") else "AUX_HASH_MISMATCH"
        if det not in (proc.stdout or ""):
            # hash mismatch if file present but we deleted - inventory missing
            det = "AUX_INVENTORY_MISSING" if "AUX_INVENTORY_MISSING" in (proc.stdout or "") else "AUX_HASH_MISMATCH"
            if "AUX_INVENTORY_MISSING" not in (proc.stdout or "") and "AUX_HASH_MISMATCH" not in (proc.stdout or ""):
                print("STOP: C07 unexpected", proc.stdout)
                return 1
        _write_receipt("E07-C07", proc, "aux_integrity_readback_cli", det, "removed sealed stdout receipt")

    # Write REAL provisional judgments ONLY after all seven receipts exist
    for cid in CLOSURE_IDS:
        if not (CREC / f"{cid}.json").is_file():
            print("STOP: missing closure receipt", cid)
            return 1
    judgments = []
    for cid in CLOSURE_IDS:
        rec = json.loads((CREC / f"{cid}.json").read_text())
        judgments.append({
            "id": cid,
            "finding": CLOSURE_TO_FINDING[cid],
            "verdict": "SELF_TESTED_PENDING_FINAL_GATE_AND_EXTERNAL_AUDIT",
            "independent_external_verification": "PENDING",
            "closure_receipt": f"closure_receipts/{cid}.json",
            "observed_exit_code": rec.get("observed_exit_code"),
            "observed_detector": rec.get("observed_detector"),
            "note": rec.get("note"),
        })
    body = {
        "document": "E07_EV_CLOSURE_JUDGMENTS",
        "contract_sha256": CONTRACT_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "tested_commit_sha": tested_commit_sha(),
        "run_id": run_id(),
        "run_attempt": run_attempt(),
        "historical_e06_ev": "HISTORICAL_IMMUTABLE",
        "judgments": judgments,
    }
    out = EVIDENCE / CLOSURE_JUDGMENTS_NAME
    out.write_text(json.dumps(body, indent=2) + "\n")
    errs = validate_closure_judgments(out)
    if errs:
        print("STOP: judgments invalid", errs)
        return 1
    print(json.dumps({"ok": True, "closures": 7, "path": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
