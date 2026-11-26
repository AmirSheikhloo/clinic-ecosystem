"""Appointment + allocation fixture builders anchored to Tehran calendar days."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from clinic_ecosystem.infrastructure.demo.builders_catalog import CatalogBundle, ResourceRow
from clinic_ecosystem.infrastructure.demo.builders_people import PatientRow, StaffRow
from clinic_ecosystem.infrastructure.demo.ids import demo_uuid
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets

TEHRAN = ZoneInfo("Asia/Tehran")

# Final statuses we insert directly (valid CHECK / enum values).
STATUS_WEIGHTS = (
    ("CONFIRMED", 45),
    ("CHECKED_IN", 10),
    ("COMPLETED", 25),
    ("CANCELLED", 12),
    ("NO_SHOW", 8),
)


@dataclass
class AppointmentRow:
    id: UUID
    patient_id: UUID
    booker_person_id: UUID | None
    service_id: UUID
    status: str
    booking_channel: str
    capacity_pool: str
    start_utc: datetime
    end_utc: datetime
    note: str | None
    resource_id: UUID
    allocation_status: str
    created_at: datetime


@dataclass
class AppointmentBundle:
    appointments: list[AppointmentRow] = field(default_factory=list)
    multi_service_group_count: int = 0
    manual_overlap_pairs: int = 0
    checked_in_waiting_today: int = 0


def tehran_today(now_utc: datetime | None = None) -> date:
    clock = now_utc or datetime.now(timezone.utc)
    return clock.astimezone(TEHRAN).date()


def tehran_day_window(day: date, hour: int, minute: int, duration_min: int) -> tuple[datetime, datetime]:
    start_local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TEHRAN)
    start = start_local.astimezone(timezone.utc)
    end = start + timedelta(minutes=duration_min)
    return start, end


def _pick_status(index: int, *, day: date, today: date) -> str:
    # Past days lean COMPLETED/NO_SHOW/CANCELLED; future lean CONFIRMED.
    if day > today:
        return "CONFIRMED"
    if day == today:
        bucket = ("CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "CONFIRMED")
        return bucket[index % len(bucket)]
    # Historical
    total = sum(w for _, w in STATUS_WEIGHTS)
    cursor = index % total
    for status, weight in STATUS_WEIGHTS:
        cursor -= weight
        if cursor < 0:
            # NO_SHOW only valid conceptually after start — historical days OK.
            return status
    return "COMPLETED"


def build_appointments(
    targets: DemoTargets,
    *,
    patients: list[PatientRow],
    catalog: CatalogBundle,
    staff: list[StaffRow],
    receptionist_person_id: UUID,
    now_utc: datetime | None = None,
) -> AppointmentBundle:
    now = now_utc or datetime.now(timezone.utc)
    today = tehran_today(now)
    tomorrow = today + timedelta(days=1)
    rooms = catalog.rooms
    services = catalog.services
    active_patients = [p for p in patients if p.is_active] or patients
    bundle = AppointmentBundle()

    def add(
        *,
        seq: int,
        patient: PatientRow,
        service_idx: int,
        room: ResourceRow,
        day: date,
        hour: int,
        minute: int,
        status: str,
        note: str | None,
        manual: bool,
        duration: int | None = None,
    ) -> AppointmentRow:
        svc = services[service_idx % len(services)]
        dur = duration or svc.duration_minutes
        start, end = tehran_day_window(day, hour, minute, dur)
        channel = "MANUAL_STAFF" if manual else "ONLINE_WEB"
        pool = "MANUAL" if manual else "ONLINE"
        # Occupying vs released allocation status mirrors appointment status.
        alloc = status
        row = AppointmentRow(
            id=demo_uuid(targets.seed, "appointment", seq),
            patient_id=patient.id,
            booker_person_id=receptionist_person_id,
            service_id=svc.id,
            status=status,
            booking_channel=channel,
            capacity_pool=pool,
            start_utc=start,
            end_utc=end,
            note=note,
            resource_id=room.id,
            allocation_status=alloc,
            created_at=start - timedelta(days=1),
        )
        bundle.appointments.append(row)
        return row

    seq = 0

    # Today: enough volume + CHECKED_IN waiting.
    for i in range(targets.appointments_today):
        patient = active_patients[i % len(active_patients)]
        room = rooms[i % len(rooms)]
        hour = 8 + (i % 10)
        minute = (i * 7) % 60
        status = "CHECKED_IN" if i < targets.checked_in_waiting_today else _pick_status(i, day=today, today=today)
        if status == "CHECKED_IN":
            bundle.checked_in_waiting_today += 1
        add(
            seq=seq,
            patient=patient,
            service_idx=i,
            room=room,
            day=today,
            hour=hour,
            minute=minute,
            status=status,
            note=None,
            manual=True,
        )
        seq += 1

    # Tomorrow.
    for i in range(targets.appointments_tomorrow):
        patient = active_patients[(i + 17) % len(active_patients)]
        add(
            seq=seq,
            patient=patient,
            service_idx=i + 3,
            room=rooms[i % len(rooms)],
            day=tomorrow,
            hour=9 + (i % 8),
            minute=(i * 11) % 60,
            status="CONFIRMED",
            note=None,
            manual=True,
        )
        seq += 1

    # Multi-service groups: same patient, same reception day, GROUP: prefix.
    for g in range(targets.multi_service_groups):
        patient = active_patients[(g * 3) % len(active_patients)]
        day = today if g % 2 == 0 else today - timedelta(days=(g % 14) + 1)
        group_token = f"GROUP:G{g:04d}"
        lines = 2 + (g % 2)
        for line in range(lines):
            add(
                seq=seq,
                patient=patient,
                service_idx=g + line,
                room=rooms[(g + line) % len(rooms)],
                day=day,
                hour=10 + line,
                minute=15 * line,
                status="CONFIRMED" if day >= today else "COMPLETED",
                note=f"{group_token} line={line + 1}/{lines}",
                manual=True,
            )
            seq += 1
        bundle.multi_service_group_count += 1

    # Manual overlap pairs on the same room/time (MANUAL pool bypasses ONLINE EXCLUDE).
    overlap_room = rooms[0]
    for o in range(targets.manual_overlap_pairs):
        day = today - timedelta(days=(o % 5))
        hour = 14
        minute = 0
        for side in (0, 1):
            patient = active_patients[(o * 2 + side) % len(active_patients)]
            add(
                seq=seq,
                patient=patient,
                service_idx=o,
                room=overlap_room,
                day=day,
                hour=hour,
                minute=minute,
                status="CONFIRMED",
                note=f"OVERLAP pair={o} side={side}",
                manual=True,
                duration=30,
            )
            seq += 1
        bundle.manual_overlap_pairs += 1

    # Non-overlapping ONLINE sample (EXCLUDE applies only to occupying ONLINE rows).
    online_count = min(200, max(20, targets.appointments // 100))
    for i in range(online_count):
        day = today + timedelta(days=3 + (i // (12 * len(rooms))))
        room = rooms[i % len(rooms)]
        # 30-minute slots, unique per room across the sample.
        slot_index = i // len(rooms)
        hour = 8 + (slot_index // 2) % 8
        minute = 0 if slot_index % 2 == 0 else 30
        patient = active_patients[(i + 41) % len(active_patients)]
        add(
            seq=seq,
            patient=patient,
            service_idx=i,
            room=room,
            day=day,
            hour=hour,
            minute=minute,
            status="CONFIRMED",
            note="ONLINE sample",
            manual=False,
            duration=30,
        )
        seq += 1

    # Fill remaining volume as MANUAL across past/future (overlap-safe).
    past_days = 45
    future_days = 21
    while len(bundle.appointments) < targets.appointments:
        i = seq
        slot = i % 10
        if slot < 7:
            day = today - timedelta(days=1 + (i % past_days))
        else:
            day = today + timedelta(days=2 + (i % future_days))
        patient = active_patients[i % len(active_patients)]
        room = rooms[i % len(rooms)]
        status = _pick_status(i, day=day, today=today)
        add(
            seq=seq,
            patient=patient,
            service_idx=i,
            room=room,
            day=day,
            hour=8 + (i % 10),
            minute=(i * 13) % 60,
            status=status,
            note=None,
            manual=True,
        )
        seq += 1

    return bundle
