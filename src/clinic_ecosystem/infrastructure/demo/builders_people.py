"""Patient and staff fixture builders (synthetic Persian identities)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from clinic_ecosystem.infrastructure.demo.ids import (
    demo_uuid,
    synthetic_mobile,
    synthetic_national_id,
)
from clinic_ecosystem.infrastructure.demo.names import (
    EXCEPTION_REASONS,
    pick_name,
    similar_pair,
    staff_name,
)
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets


@dataclass
class PersonRow:
    id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    gender: str | None = None


@dataclass
class PatientRow:
    id: UUID
    person_id: UUID
    dossier_number: str | None
    is_active: bool
    national_id: str | None = None
    exception_reason: str | None = None
    phone_e164: str | None = None
    shared_phone_family: int | None = None


_JOB_TITLES = {
    "RECEPTIONIST": "پذیرشگر",
    "PRACTITIONER": "پزشک",
    "MULTI_PRACTITIONER": "پزشک چندخدمتی",
    "DOCTOR": "پزشک",
}


@dataclass
class StaffRow:
    id: UUID
    person_id: UUID
    staff_kind: str
    medical_council_code: str | None
    is_active: bool
    with_login: bool
    login_identifier: str | None = None
    resource_id: UUID | None = None
    resource_name: str | None = None
    job_title: str | None = None


@dataclass
class PeopleBundle:
    persons: list[PersonRow] = field(default_factory=list)
    patients: list[PatientRow] = field(default_factory=list)
    staff: list[StaffRow] = field(default_factory=list)


def build_patients(targets: DemoTargets) -> PeopleBundle:
    bundle = PeopleBundle()
    # Similar-name clusters first (2–3 members each).
    idx = 0
    for c in range(targets.similar_name_clusters):
        for m in range(3):
            first, last = similar_pair(c, m)
            person_id = demo_uuid(targets.seed, "patient_person", idx)
            patient_id = demo_uuid(targets.seed, "patient", idx)
            bundle.persons.append(
                PersonRow(person_id, first, last, date(1985 + (idx % 30), 1 + (idx % 12), 1 + (idx % 27)))
            )
            bundle.patients.append(
                PatientRow(
                    id=patient_id,
                    person_id=person_id,
                    dossier_number=f"D-{idx:05d}",
                    is_active=True,
                    phone_e164=synthetic_mobile(targets.seed, idx),
                )
            )
            idx += 1

    # Exceptional identity (no National ID).
    for e in range(targets.exceptional_identity_patients):
        first, last = pick_name(idx + 17)
        person_id = demo_uuid(targets.seed, "patient_person", idx)
        patient_id = demo_uuid(targets.seed, "patient", idx)
        reason = EXCEPTION_REASONS[e % len(EXCEPTION_REASONS)]
        bundle.persons.append(PersonRow(person_id, first, last, None))
        bundle.patients.append(
            PatientRow(
                id=patient_id,
                person_id=person_id,
                dossier_number=f"EXC-{e:03d}",
                is_active=True,
                exception_reason=reason,
                phone_e164=synthetic_mobile(targets.seed, idx),
            )
        )
        idx += 1

    # Shared-phone family scenarios: 2–3 members share one phone (distinct surnames).
    for f in range(targets.shared_phone_families):
        shared = synthetic_mobile(targets.seed, 50_000 + f)
        members = 2 + (f % 2)
        for m in range(members):
            first, last = pick_name(idx + 31)
            person_id = demo_uuid(targets.seed, "patient_person", idx)
            patient_id = demo_uuid(targets.seed, "patient", idx)
            bundle.persons.append(
                PersonRow(person_id, first, last, date(1990 + m, 3, 10 + m))
            )
            bundle.patients.append(
                PatientRow(
                    id=patient_id,
                    person_id=person_id,
                    dossier_number=f"FAM-{f:03d}-{m}",
                    is_active=True,
                    phone_e164=shared,
                    shared_phone_family=f,
                    national_id=synthetic_national_id(targets.seed, 10_000 + idx)
                    if m == 0
                    else None,
                )
            )
            idx += 1

    # Fill remaining patients; mark some inactive; assign national IDs to a subset.
    nid_budget = targets.national_id_patients
    inactive_budget = targets.inactive_patients
    while idx < targets.patients:
        first, last = pick_name(idx)
        person_id = demo_uuid(targets.seed, "patient_person", idx)
        patient_id = demo_uuid(targets.seed, "patient", idx)
        is_active = inactive_budget <= 0 or idx % 13 != 0
        if not is_active:
            inactive_budget -= 1
        national = None
        if nid_budget > 0 and idx % 7 == 0:
            national = synthetic_national_id(targets.seed, idx)
            nid_budget -= 1
        bundle.persons.append(
            PersonRow(
                person_id,
                first,
                last,
                date(1970 + (idx % 40), 1 + (idx % 12), 1 + (idx % 28)),
            )
        )
        bundle.patients.append(
            PatientRow(
                id=patient_id,
                person_id=person_id,
                dossier_number=f"D-{idx:05d}",
                is_active=is_active,
                national_id=national,
                phone_e164=synthetic_mobile(targets.seed, idx),
            )
        )
        idx += 1

    # Ensure national-id quota even if modulo skipped some.
    # Use a dedicated high index band so HMAC lookup keys stay unique.
    used_nids = {p.national_id for p in bundle.patients if p.national_id}
    extra = 0
    for p in bundle.patients:
        if nid_budget <= 0:
            break
        if p.national_id is None and p.exception_reason is None:
            while True:
                candidate = synthetic_national_id(targets.seed, 2_000_000 + extra)
                extra += 1
                if candidate not in used_nids:
                    break
            p.national_id = candidate
            used_nids.add(candidate)
            nid_budget -= 1

    return bundle


def build_staff(targets: DemoTargets) -> PeopleBundle:
    bundle = PeopleBundle()
    for i in range(targets.staff_total):
        first, last = staff_name(i)
        person_id = demo_uuid(targets.seed, "staff_person", i)
        staff_id = demo_uuid(targets.seed, "staff", i)
        with_login = i < targets.receptionist_logins
        kind = "RECEPTIONIST" if with_login else ("MULTI_PRACTITIONER" if i % 3 == 0 else "PRACTITIONER")
        bundle.persons.append(PersonRow(person_id, first, last, date(1980 + (i % 25), 6, 15)))
        resource_id = None
        resource_name = None
        if not with_login:
            resource_id = demo_uuid(targets.seed, "practitioner_resource", i)
            resource_name = f"دکتر {first} {last}"
        bundle.staff.append(
            StaffRow(
                id=staff_id,
                person_id=person_id,
                staff_kind=kind,
                medical_council_code=None if with_login else f"MC-{1000 + i}",
                is_active=True,
                with_login=with_login,
                login_identifier=f"recv.demo.{i}@clinic.test" if with_login else None,
                resource_id=resource_id,
                resource_name=resource_name,
                job_title=_JOB_TITLES.get(kind, "کارشناس"),
            )
        )
    return bundle
