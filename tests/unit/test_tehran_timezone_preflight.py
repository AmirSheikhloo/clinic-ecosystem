"""Regression: Asia/Tehran must resolve via tzdata (Windows has no system IANA DB)."""

from __future__ import annotations

import importlib
from zoneinfo import ZoneInfo

import pytest

from clinic_ecosystem.infrastructure.timezones import (
    TEHRAN_TZ_KEY,
    require_tehran_zoneinfo,
    tehran_zoneinfo_preflight,
)


def test_tzdata_package_is_importable() -> None:
    """Runtime dependency declared in pyproject.toml must be installed."""
    importlib.import_module("tzdata")


def test_asia_tehran_zoneinfo_resolves() -> None:
    zone = require_tehran_zoneinfo()
    assert isinstance(zone, ZoneInfo)
    assert getattr(zone, "key", TEHRAN_TZ_KEY) == TEHRAN_TZ_KEY
    # Same key via stdlib path used by builders_appointments.
    assert ZoneInfo("Asia/Tehran").key == "Asia/Tehran"


def test_tehran_zoneinfo_preflight_ok() -> None:
    result = tehran_zoneinfo_preflight()
    assert result["ok"] is True
    assert result["key"] == "Asia/Tehran"


def test_check_tehran_timezone_script_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    import json
    import runpy
    from pathlib import Path

    # Execute as the Windows launcher does: python scripts/check_tehran_timezone.py
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_tehran_timezone.py"
    ns = runpy.run_path(str(script))
    assert ns["main"]() == 0
    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["key"] == "Asia/Tehran"
