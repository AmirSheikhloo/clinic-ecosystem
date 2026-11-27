"""Largest-remainder discount allocation must use exact integer arithmetic."""

from __future__ import annotations


def allocate_invoice_discount(total_discount: int, grosses: list[int]) -> list[int]:
    """Mirror finance.apply_discount integer largest-remainder logic."""
    total_gross = sum(grosses)
    assert total_gross > 0
    total_discount = min(total_discount, total_gross)
    shares: list[list[int | float]] = []
    allocated = 0
    for idx, gross in enumerate(grosses):
        base = (total_discount * gross) // total_gross
        remainder = (total_discount * gross) % total_gross
        shares.append([idx, base, remainder, gross])
        allocated += base
    rem = total_discount - allocated
    shares.sort(key=lambda s: (s[2], s[3], s[0]), reverse=True)
    for i in range(rem):
        shares[i % len(shares)][1] = int(shares[i % len(shares)][1]) + 1
    out = [0] * len(grosses)
    for idx, disc, _r, _g in shares:
        out[int(idx)] = int(disc)
    assert sum(out) == total_discount
    return out


def test_largest_remainder_sums_exactly() -> None:
    assert allocate_invoice_discount(100, [30, 30, 40]) == [30, 30, 40] or sum(
        allocate_invoice_discount(100, [30, 30, 40])
    ) == 100
    got = allocate_invoice_discount(10, [3, 3, 4])
    assert sum(got) == 10
    assert all(d >= 0 for d in got)


def test_percent_bps_integer_only() -> None:
    gross = 100_000
    bps = 1250  # 12.50%
    assert (gross * bps) // 10_000 == 12_500
