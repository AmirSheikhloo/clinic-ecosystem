"""Integer IRR largest-remainder discount allocation (desk checkout parity)."""

from __future__ import annotations


def allocate_fixed_discount_irr(grosses: list[int], total_discount: int) -> list[int]:
    n = len(grosses)
    if n == 0 or total_discount <= 0:
        return [0] * n
    total_gross = sum(grosses)
    if total_gross <= 0:
        return [0] * n
    capped = min(total_discount, total_gross)
    exact = [(capped * g) / total_gross for g in grosses]
    floors = [int(v) for v in exact]
    rem = capped - sum(floors)
    order = sorted(
        ((i, exact[i] - floors[i]) for i in range(n)),
        key=lambda t: (-t[1], t[0]),
    )
    out = list(floors)
    for i, _ in order:
        if rem <= 0:
            break
        room = max(0, grosses[i] - out[i])
        if room <= 0:
            continue
        out[i] += 1
        rem -= 1
    return out


def test_largest_remainder_three_equal_lines() -> None:
    assert allocate_fixed_discount_irr([100, 100, 100], 100) == [34, 33, 33]


def test_caps_at_line_gross() -> None:
    assert allocate_fixed_discount_irr([50, 50], 200) == [50, 50]


def test_proportional_uneven() -> None:
    assert allocate_fixed_discount_irr([1000, 1], 500) == [500, 0]
