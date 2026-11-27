"""Jalali (Persian) calendar helpers for Tehran local DATE arithmetic.

Algorithm: astronomical conversion used widely for civil Jalali dates.
Inputs/outputs are civil calendar dates (year, month, day) — not UTC instants.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JalaliDate:
    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if not (1 <= self.month <= 12):
            raise ValueError("jalali month out of range")
        length = jalali_month_length(self.year, self.month)
        if not (1 <= self.day <= length):
            raise ValueError("jalali day out of range for month")


def _div(a: int, b: int) -> int:
    return a // b


def to_jalali(gy: int, gm: int, gd: int) -> JalaliDate:
    """Gregorian civil date → Jalali civil date."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + _div(gy2 + 3, 4)
        - _div(gy2 + 99, 100)
        + _div(gy2 + 399, 400)
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * _div(days, 12053)
    days %= 12053
    jy += 4 * _div(days, 1461)
    days %= 1461
    if days > 365:
        jy += _div(days - 1, 365)
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + _div(days, 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + _div(days - 186, 30)
        jd = 1 + ((days - 186) % 30)
    return JalaliDate(jy, jm, jd)


def from_jalali(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Jalali civil date → Gregorian civil (y, m, d). Day must be valid for month."""
    length = jalali_month_length(jy, jm)
    if not (1 <= jm <= 12) or not (1 <= jd <= length):
        raise ValueError("invalid jalali date")
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (365 * jy) + (_div(jy, 33) * 8) + _div((jy % 33) + 3, 4) + 78 + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy += 400 * _div(days, 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * _div(days - 1, 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * _div(days, 1461)
    days %= 1461
    if days > 365:
        gy += _div(days - 1, 365)
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [
        0,
        31,
        29 if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def is_jalali_leap(jy: int) -> bool:
    """True when Esfand has 30 days.

    Uses the 33-year civil cycle embedded in the same conversion as
    ``from_jalali`` / ``to_jalali`` (8 leaps per 33 years). Matches the
    official Iranian calendar for modern clinic years including 1403 leap /
    1404 common (Intl ``ca-persian`` Nowruz boundaries).
    """
    return (jy % 33) in {1, 5, 9, 13, 17, 22, 26, 30}


def jalali_month_length(jy: int, jm: int) -> int:
    if not (1 <= jm <= 12):
        raise ValueError("jalali month out of range")
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def add_jalali_months(jy: int, jm: int, jd: int, months: int) -> JalaliDate:
    """Add calendar months; clamp day into target month (end-of-month / leap Esfand)."""
    if months < 0:
        raise ValueError("months must be non-negative for rolling forward")
    if not (1 <= jm <= 12):
        raise ValueError("jalali month out of range")
    # Allow source day up to month length; clamp into target.
    src_len = jalali_month_length(jy, jm)
    if not (1 <= jd <= src_len):
        raise ValueError("jalali day out of range for month")
    total = (jm - 1) + months
    ny = jy + total // 12
    nm = (total % 12) + 1
    nd = min(jd, jalali_month_length(ny, nm))
    return JalaliDate(ny, nm, nd)
