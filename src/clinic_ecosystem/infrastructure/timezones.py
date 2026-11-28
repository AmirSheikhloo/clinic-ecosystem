"""IANA timezone helpers used by demo/preview and scheduling boundaries."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TEHRAN_TZ_KEY = "Asia/Tehran"


def require_tehran_zoneinfo() -> ZoneInfo:
    """Resolve Asia/Tehran or raise a clear install hint (Windows needs tzdata)."""
    try:
        return ZoneInfo(TEHRAN_TZ_KEY)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            "IANA timezone data is missing: cannot resolve Asia/Tehran. "
            "Install the project runtime dependency 'tzdata' into this Python "
            "environment (pip install -e '.[dev]' or pip install tzdata) and retry."
        ) from exc


def tehran_zoneinfo_preflight() -> dict[str, str | bool]:
    """Return a machine-readable preflight result for preview launchers."""
    try:
        zone = require_tehran_zoneinfo()
        return {
            "ok": True,
            "key": TEHRAN_TZ_KEY,
            "keyname": getattr(zone, "key", TEHRAN_TZ_KEY),
        }
    except RuntimeError as exc:
        return {"ok": False, "key": TEHRAN_TZ_KEY, "error": str(exc)}
