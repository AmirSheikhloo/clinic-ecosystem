#!/usr/bin/env python3
"""Fail CI if required M0 unit/integration tests were not discovered or ran skipped."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Previously passing suites retained, plus Appendix E security/ownership closures.
REQUIRED_TESTS = (
    # Unit — F.2 verbatim + E.4 downgrade / E.3 no CP0000
    "tests/unit/test_tp0001_verbatim_sql.py::test_tp0001_contains_verbatim_f2_tenant_registry",
    "tests/unit/test_tp0001_verbatim_sql.py::test_spec_still_contains_same_f2_contract",
    "tests/unit/test_tp0001_downgrade_policy.py::test_tp0001_downgrade_is_explicitly_irreversible",
    "tests/unit/test_tp0001_downgrade_policy.py::test_cp0000_revision_file_absent",
    # Isolation — prior CONNECT + PUBLIC + Local Hub
    "tests/integration/test_plane_isolation.py::test_tenant_login_cannot_connect_to_control_plane",
    "tests/integration/test_plane_isolation.py::test_control_login_cannot_connect_to_tenant_app",
    "tests/integration/test_plane_isolation.py::test_same_plane_connect_allowed",
    "tests/integration/test_plane_isolation.py::test_public_connect_revoked_on_cloud_databases",
    "tests/integration/test_plane_isolation.py::test_local_hub_reuses_tenant_group_role_names",
    # Isolation — migrator CONNECT + assigned-DB matrix
    "tests/integration/test_plane_isolation.py::test_tenant_migrator_cannot_connect_to_control_plane",
    "tests/integration/test_plane_isolation.py::test_control_migrator_cannot_connect_to_tenant_app",
    "tests/integration/test_plane_isolation.py::test_plane_logins_connect_only_to_assigned_databases",
    "tests/integration/test_plane_isolation.py::test_local_hub_logins_can_connect",
    # Membership / SET ROLE
    "tests/integration/test_role_membership.py::test_cloud_runtime_membership_direct_and_transitive",
    "tests/integration/test_role_membership.py::test_local_hub_runtime_membership",
    "tests/integration/test_role_membership.py::test_runtime_cannot_set_role_to_migrator_or_other_plane",
    "tests/integration/test_role_membership.py::test_migrator_logins_assume_only_own_migrator_role",
    "tests/integration/test_role_membership.py::test_local_hub_set_role_boundaries",
    # Schema/object privileges
    "tests/integration/test_plane_privileges.py::test_runtime_roles_lack_dangerous_attributes",
    "tests/integration/test_plane_privileges.py::test_runtime_schema_and_table_privileges_after_tp0001",
    "tests/integration/test_plane_privileges.py::test_runtime_login_cannot_ddl_or_truncate",
    "tests/integration/test_plane_privileges.py::test_default_privileges_do_not_grant_public_or_other_plane",
    # TP0001 / CP version tracking
    "tests/integration/test_tp0001_migration.py::test_tp0001_applies_to_cloud_tenant_and_local_hub",
    "tests/integration/test_tp0001_migration.py::test_tp0001_objects_owned_by_db_migrator",
    "tests/integration/test_tp0001_migration.py::test_tp0001_rejects_invalid_status",
    "tests/integration/test_tp0001_migration.py::test_tp0001_does_not_mutate_control_plane_db",
    "tests/integration/test_tp0001_migration.py::test_separate_alembic_version_tables",
)

REQUIRED_INTEGRATION_PREFIXES = (
    "tests/integration/test_plane_isolation.py::",
    "tests/integration/test_role_membership.py::",
    "tests/integration/test_plane_privileges.py::",
    "tests/integration/test_tp0001_migration.py::",
)


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def assert_collect(collect_log: Path) -> None:
    text = collect_log.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_TESTS if name not in text]
    if missing:
        _fail(
            "Required M0 tests were not discovered:\n  - "
            + "\n  - ".join(missing)
        )
    print(f"OK: discovered all {len(REQUIRED_TESTS)} required M0 tests")


def _classname_to_nodeid(classname: str, name: str) -> str:
    path = classname.replace(".", "/") + ".py"
    return f"{path}::{name}"


def assert_junit(junit_path: Path, pytest_log: Path | None) -> None:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    suites = root.findall("testsuite")
    if root.tag == "testsuite":
        suites = [root]
    cases = []
    for suite in suites:
        cases.extend(suite.findall("testcase"))

    by_id: dict[str, ET.Element] = {}
    for case in cases:
        nodeid = _classname_to_nodeid(case.get("classname", ""), case.get("name", ""))
        by_id[nodeid] = case

    missing = [name for name in REQUIRED_TESTS if name not in by_id]
    if missing:
        _fail(
            "Required M0 tests missing from junit results:\n  - "
            + "\n  - ".join(missing)
        )

    skipped_required: list[str] = []
    failed_required: list[str] = []
    for name in REQUIRED_TESTS:
        case = by_id[name]
        if case.find("skipped") is not None:
            skipped_required.append(name)
        if case.find("failure") is not None or case.find("error") is not None:
            failed_required.append(name)

    if skipped_required:
        _fail(
            "Required M0 tests were skipped (not acceptable for CI evidence):\n  - "
            + "\n  - ".join(skipped_required)
        )
    if failed_required:
        _fail(
            "Required M0 tests failed:\n  - " + "\n  - ".join(failed_required)
        )

    for nodeid, case in by_id.items():
        if nodeid.startswith(REQUIRED_INTEGRATION_PREFIXES) and case.find(
            "skipped"
        ) is not None:
            _fail(f"Integration test skipped: {nodeid}")

    if pytest_log is not None and pytest_log.exists():
        log = pytest_log.read_text(encoding="utf-8")
        if "SKIPPED" in log and "tests/integration/" in log:
            for line in log.splitlines():
                if "skipped" in line.lower() and "tests/integration" in line:
                    _fail(f"Pytest log indicates skipped integration tests: {line}")

    print(
        f"OK: {len(REQUIRED_TESTS)} required tests present in junit; "
        "0 required skips; integration suites executed"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("collect", "junit"), required=True)
    parser.add_argument("--collect-log", type=Path)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--pytest-log", type=Path)
    args = parser.parse_args()

    if args.mode == "collect":
        if not args.collect_log:
            _fail("--collect-log is required for collect mode")
        assert_collect(args.collect_log)
    else:
        if not args.junit:
            _fail("--junit is required for junit mode")
        assert_junit(args.junit, args.pytest_log)


if __name__ == "__main__":
    main()
