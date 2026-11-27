#!/usr/bin/env python3
"""Fail fast when Asia/Tehran cannot be resolved (Windows without tzdata).

Exit codes:
  0 — ZoneInfo('Asia/Tehran') works
  1 — missing/invalid IANA data (install tzdata)
  2 — unexpected error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from clinic_ecosystem.infrastructure.timezones import tehran_zoneinfo_preflight  # noqa: E402


def main() -> int:
    result = tehran_zoneinfo_preflight()
    print(json.dumps(result, ensure_ascii=False))
    if result.get("ok"):
        return 0
    print(result.get("error") or "Asia/Tehran unavailable", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"timezone preflight crashed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
