"""Synthetic Cloud/Local admission policy (A04). Default DENY."""

from __future__ import annotations

from dataclasses import dataclass

# Explicit allowlist of synthetic head-set pairs (source -> dest).
# Heads are frozensets of version_num strings.
ALLOWED_PAIRS: dict[tuple[frozenset[str], frozenset[str]], str] = {
    (
        frozenset({"exp_e03_h8", "exp_e03_cat2"}),
        frozenset({"exp_e03_h8", "exp_e03_cat2"}),
    ): "both_heads_compatible_synthetic_v1",
    (
        frozenset({"exp_e03_cat2"}),
        frozenset({"exp_e03_cat2"}),
    ): "catalog_only_compatible_synthetic_v1",
}


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason: str
    source_heads: frozenset[str]
    dest_heads: frozenset[str]


def decide_admission(source_heads: set[str] | frozenset[str], dest_heads: set[str] | frozenset[str]) -> AdmissionDecision:
    src = frozenset(source_heads)
    dst = frozenset(dest_heads)
    if not src or not dst:
        return AdmissionDecision(False, "DENY_empty_or_missing_heads", src, dst)
    key = (src, dst)
    if key in ALLOWED_PAIRS:
        return AdmissionDecision(True, f"ALLOW_{ALLOWED_PAIRS[key]}", src, dst)
    # reverse direction of an allowed pair is still deny unless listed
    return AdmissionDecision(False, "DENY_unlisted_or_mismatched_heads", src, dst)
