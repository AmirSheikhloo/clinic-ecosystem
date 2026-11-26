"""Deterministic rich demo dataset for Product Owner preview (D0.5 / Task 28)."""

from clinic_ecosystem.infrastructure.demo.loader import load_demo_dataset
from clinic_ecosystem.infrastructure.demo.profiles import DEMO_SEED, ProfileName, resolve_profile
from clinic_ecosystem.infrastructure.demo.validate import collect_counts, validate_demo_counts

__all__ = [
    "DEMO_SEED",
    "ProfileName",
    "collect_counts",
    "load_demo_dataset",
    "resolve_profile",
    "validate_demo_counts",
]
