#!/usr/bin/env python3
"""Assert required M1-01 pytest node IDs were collected/executed."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED = [
    "tests/unit/test_uuid7_provider.py::test_new_uuid7_returns_stdlib_uuid_version_7",
    "tests/unit/test_uuid7_provider.py::test_new_uuid7_unique_under_threads",
    "tests/unit/test_appointment_schedule_domain.py::test_schedule_online_hold_requires_expiry",
    "tests/unit/test_appointment_schedule_domain.py::test_schedule_manual_success",
    "tests/unit/test_schedule_handler_unit.py::test_idempotency_in_progress_raises_425_semantics",
    "tests/unit/test_schedule_handler_unit.py::test_manual_overlap_requires_acknowledgement",
    "tests/unit/test_schedule_handler_unit.py::test_manual_schedule_success_stages_outbox",
    "tests/unit/test_m1_migration_sql_contracts.py::test_tp0005_contains_online_exclude_predicate",
    "tests/unit/test_m1_migration_sql_contracts.py::test_tp0007_forces_rls_on_appointments",
    "tests/integration/test_m1_migrations.py::test_tenant_plane_upgrades_to_tp0007",
    "tests/integration/test_m1_migrations.py::test_local_hub_also_reaches_tp0007",
    "tests/integration/test_m1_schedule_appointment.py::test_schedule_online_creates_appointment_outbox_idempotency",
    "tests/integration/test_m1_schedule_appointment.py::test_online_overlap_raises_capacity_conflict",
    "tests/integration/test_m1_schedule_appointment.py::test_idempotency_fingerprint_conflict",
    "tests/integration/test_m1_manual_and_holds.py::test_manual_overlap_requires_ack_then_audits",
    "tests/integration/test_m1_manual_and_holds.py::test_hold_expiry_worker_claim_then_expire",
    "tests/integration/test_m1_manual_and_holds.py::test_concurrent_online_bookings_only_one_wins",
]


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def mode_collect(collect_log: Path) -> None:
    text = collect_log.read_text(encoding="utf-8")
    missing = [nid for nid in REQUIRED if nid not in text]
    if missing:
        _fail("missing collected node ids:\n" + "\n".join(missing))
    print(f"OK: collected {len(REQUIRED)} required M1 node ids")


def mode_junit(junit: Path, pytest_log: Path) -> None:
    tree = ET.parse(junit)
    root = tree.getroot()
    # pytest junit may nest testcase under testsuite
    cases = root.findall(".//testcase")
    executed = {
        f"{c.attrib.get('classname', '').replace('.', '/')}.py::{c.attrib.get('name')}"
        for c in cases
    }
    # Also accept raw node id forms from log
    log = pytest_log.read_text(encoding="utf-8")
    missing = []
    for nid in REQUIRED:
        short = nid.split("::", 1)[-1]
        if nid in log or short in log:
            continue
        # junit classname is dotted module path without tests prefix sometimes
        if any(short == c.attrib.get("name") for c in cases):
            continue
        missing.append(nid)
    if missing:
        _fail("required M1 tests not evidenced as executed:\n" + "\n".join(missing))
    # Fail if any required test failed
    for c in cases:
        name = c.attrib.get("name", "")
        if any(name == nid.split("::")[-1] for nid in REQUIRED):
            if c.find("failure") is not None or c.find("error") is not None:
                _fail(f"required test failed: {name}")
            if c.find("skipped") is not None:
                _fail(f"required test skipped: {name}")
    print(f"OK: executed {len(REQUIRED)} required M1 node ids; junit cases={len(cases)}")
    _ = executed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("collect", "junit"), required=True)
    parser.add_argument("--collect-log", type=Path)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--pytest-log", type=Path)
    args = parser.parse_args()
    if args.mode == "collect":
        if not args.collect_log:
            _fail("--collect-log required")
        mode_collect(args.collect_log)
    else:
        if not args.junit or not args.pytest_log:
            _fail("--junit and --pytest-log required")
        mode_junit(args.junit, args.pytest_log)


if __name__ == "__main__":
    main()
