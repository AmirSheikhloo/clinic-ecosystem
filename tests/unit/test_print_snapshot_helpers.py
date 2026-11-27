"""Unit tests for thermal print snapshot helpers (no DB)."""

from __future__ import annotations

from datetime import datetime, timezone

from clinic_ecosystem.presentation.http.finance import (
    _gregorian_to_jalali,
    _jalali_label_from_utc,
)


def test_gregorian_to_jalali_known_anchor() -> None:
    # 2025-03-21 ≈ 1404/01/01 (Nowruz) depending on leap tables; assert shape.
    jy, jm, jd = _gregorian_to_jalali(2025, 3, 21)
    assert jy == 1404
    assert jm == 1
    assert jd == 1


def test_jalali_label_format() -> None:
    label = _jalali_label_from_utc(datetime(2025, 3, 21, 12, 0, tzinfo=timezone.utc))
    assert label.count("/") == 2
    parts = label.split("/")
    assert len(parts[0]) == 4
    assert all(p.isdigit() for p in parts)
