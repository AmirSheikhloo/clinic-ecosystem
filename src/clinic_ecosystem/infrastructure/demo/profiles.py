"""Demo dataset profile targets (minimal | demo | performance)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ProfileName = Literal["minimal", "demo", "performance"]

DEMO_SEED = 20261126


@dataclass(frozen=True)
class DemoTargets:
    """Minimum counts the generator aims to meet for implemented modules."""

    patients: int
    inactive_patients: int
    similar_name_clusters: int
    shared_phone_families: int
    national_id_patients: int
    exceptional_identity_patients: int
    staff_total: int
    receptionist_logins: int
    practitioner_no_login: int
    services: int
    resources_rooms: int
    appointments: int
    appointments_today: int
    appointments_tomorrow: int
    manual_overlap_pairs: int
    checked_in_waiting_today: int
    multi_service_groups: int
    audit_entries: int
    seed: int = DEMO_SEED


MINIMAL = DemoTargets(
    patients=25,
    inactive_patients=5,
    similar_name_clusters=3,
    shared_phone_families=2,
    national_id_patients=5,
    exceptional_identity_patients=5,
    staff_total=8,
    receptionist_logins=2,
    practitioner_no_login=6,
    services=6,
    resources_rooms=3,
    appointments=80,
    appointments_today=12,
    appointments_tomorrow=8,
    manual_overlap_pairs=3,
    checked_in_waiting_today=4,
    multi_service_groups=5,
    audit_entries=100,
)

DEMO = DemoTargets(
    patients=520,
    inactive_patients=40,
    similar_name_clusters=25,
    shared_phone_families=32,
    national_id_patients=36,
    exceptional_identity_patients=32,
    staff_total=42,
    receptionist_logins=8,
    practitioner_no_login=34,
    services=32,
    resources_rooms=12,
    appointments=10_500,
    appointments_today=220,
    appointments_tomorrow=110,
    manual_overlap_pairs=32,
    checked_in_waiting_today=36,
    multi_service_groups=110,
    audit_entries=5_200,
)

# Performance stub: larger volume for stress preview; same shape as demo.
PERFORMANCE = DemoTargets(
    patients=1_200,
    inactive_patients=80,
    similar_name_clusters=40,
    shared_phone_families=40,
    national_id_patients=60,
    exceptional_identity_patients=40,
    staff_total=60,
    receptionist_logins=12,
    practitioner_no_login=48,
    services=40,
    resources_rooms=16,
    appointments=25_000,
    appointments_today=400,
    appointments_tomorrow=200,
    manual_overlap_pairs=40,
    checked_in_waiting_today=50,
    multi_service_groups=200,
    audit_entries=12_000,
)

PROFILES: dict[ProfileName, DemoTargets] = {
    "minimal": MINIMAL,
    "demo": DEMO,
    "performance": PERFORMANCE,
}


def resolve_profile(name: str | None) -> tuple[ProfileName, DemoTargets]:
    key: ProfileName = "demo"
    if name:
        normalized = name.strip().lower()
        if normalized not in PROFILES:
            raise ValueError(f"unknown demo profile: {name!r}; expected {sorted(PROFILES)}")
        key = normalized  # type: ignore[assignment]
    return key, PROFILES[key]


def targets_as_dict(targets: DemoTargets) -> dict:
    return asdict(targets)
