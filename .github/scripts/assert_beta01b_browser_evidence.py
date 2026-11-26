#!/usr/bin/env python3
"""Assert BETA-01B Playwright browser E2E evidence (no silent skips)."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_TITLES = [
    "BETA-01B reception browser acceptance gate",
    "unauthorized principal cannot use reception catalog",
]


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    if not args.junit.is_file():
        _fail(f"missing junit file: {args.junit}")
    if not args.log.is_file():
        _fail(f"missing log file: {args.log}")

    log = args.log.read_text(encoding="utf-8", errors="replace")
    if "BETA-01B browser E2E PASSED" not in log:
        _fail("orchestrator log missing PASS marker")
    if "SKIP_BROWSER_E2E" in log:
        _fail("browser E2E was skipped")

    tree = ET.parse(args.junit)
    root = tree.getroot()
    cases = root.findall(".//testcase")
    if not cases:
        _fail("junit contains no testcase elements")

    names = {c.attrib.get("name", "") for c in cases}
    for title in REQUIRED_TITLES:
        if title not in names and not any(title in n for n in names):
            _fail(f"required browser test missing from junit: {title}")

    passed = failed = skipped = 0
    for case in cases:
        if case.find("skipped") is not None:
            skipped += 1
            _fail(f"required browser test skipped: {case.attrib.get('name')}")
        elif case.find("failure") is not None or case.find("error") is not None:
            failed += 1
            _fail(f"required browser test failed: {case.attrib.get('name')}")
        else:
            passed += 1

    print(
        f"OK: browser E2E evidence PASS={passed} FAIL={failed} SKIP={skipped}; "
        f"required={len(REQUIRED_TITLES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
