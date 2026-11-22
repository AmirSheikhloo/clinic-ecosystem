"""Pin F0.5 roster integrity and emit non-waiving outcome inventory."""
from __future__ import annotations

from pathlib import Path

from tests.acceptance.package1_inventory import (
    EXPECTED_CSV_SHA256,
    build_inventory,
    fixture_sha256,
    inventory_summary,
    write_inventory_json,
)


def test_f05_csv_digest_and_ninety_unique_case_ids():
    assert fixture_sha256() == EXPECTED_CSV_SHA256
    outcomes = build_inventory()
    assert len(outcomes) == 90
    assert len({row.case_id for row in outcomes}) == 90
    assert {row.outcome for row in outcomes} <= {"PASS", "FAIL", "BLOCKED", "NOT_EXECUTED"}
    assert "SKIP" not in {row.outcome for row in outcomes}


def test_inventory_summary_has_no_fail_on_current_branch(tmp_path: Path):
    summary = inventory_summary()
    assert summary["case_count"] == 90
    assert summary["counts"]["FAIL"] == 0
    assert summary["counts"]["PASS"] >= 1
    assert summary["counts"]["BLOCKED"] >= 1
    assert summary["counts"]["NOT_EXECUTED"] >= 1
    out = tmp_path / "package1_inventory.json"
    written = write_inventory_json(out)
    assert out.exists()
    assert written["counts"] == summary["counts"]
