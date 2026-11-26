#!/usr/bin/env python3
"""Benchmark appointment list/filter queries against a temporary 100k-row set.

Uses CLINIC_BENCH_DSN or CLINIC_DATABASE_URL against a running preview/E2E Postgres.
Inserts synthetic appointments (+ allocations) into the seeded tenant, times
representative queries, then deletes only rows tagged with this run's note marker.

No new migrations. Synthetic data only.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7  # noqa: E402


async def _dsn_from_env() -> str:
    dsn = os.environ.get("CLINIC_BENCH_DSN", "").strip()
    if dsn:
        return dsn
    url = os.environ.get("CLINIC_DATABASE_URL", "").strip()
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    raise SystemExit("Set CLINIC_BENCH_DSN or CLINIC_DATABASE_URL")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out", type=Path, default=Path("/tmp/bench_100k.json"))
    args = parser.parse_args()

    marker = f"bench100k:{new_uuid7()}"
    conn = await asyncpg.connect(await _dsn_from_env())
    report: dict = {"count": args.count, "marker": marker, "queries": []}
    try:
        tenant = await conn.fetchval(
            "SELECT tenant_id FROM tenant_registry ORDER BY tenant_id LIMIT 1"
        )
        if tenant is None:
            raise SystemExit("No tenant_registry row")
        patients = await conn.fetch(
            "SELECT id FROM patient_profiles WHERE tenant_id=$1 AND is_active LIMIT 200",
            tenant,
        )
        services = await conn.fetch(
            "SELECT id FROM services WHERE tenant_id=$1 AND is_active LIMIT 50",
            tenant,
        )
        resources = await conn.fetch(
            "SELECT id FROM bookable_resources WHERE tenant_id=$1 AND is_active LIMIT 50",
            tenant,
        )
        if not patients or not services or not resources:
            raise SystemExit("Need seeded patients/services/resources")

        print(f"Inserting {args.count} synthetic appointments (marker={marker})…", flush=True)
        now = datetime.now(timezone.utc)
        appt_batch: list[tuple] = []
        alloc_batch: list[tuple] = []

        async def flush() -> None:
            nonlocal appt_batch, alloc_batch
            if not appt_batch:
                return
            await conn.copy_records_to_table(
                "appointments",
                records=appt_batch,
                columns=[
                    "id",
                    "tenant_id",
                    "beneficiary_patient_id",
                    "booker_person_id",
                    "patient_booking_note",
                    "service_id",
                    "status",
                    "booking_channel",
                    "capacity_pool",
                    "scheduled_start_at_utc",
                    "scheduled_end_at_utc",
                    "hold_expires_at_utc",
                    "aggregate_version",
                    "created_at_utc",
                    "updated_at_utc",
                ],
            )
            await conn.executemany(
                """
                INSERT INTO appointment_resource_allocations (
                    id, tenant_id, appointment_id, resource_id, booking_channel,
                    capacity_pool, allocation_status, time_slot, created_at_utc
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7, tstzrange($8::timestamptz, $9::timestamptz, '[)'), $10
                )
                """,
                alloc_batch,
            )
            appt_batch = []
            alloc_batch = []

        for i in range(args.count):
            appt_id = new_uuid7()
            start = now + timedelta(minutes=(i % 10_080) - 5_040)
            end = start + timedelta(minutes=30)
            status = "CHECKED_IN" if i % 5 == 0 else "CONFIRMED"
            appt_batch.append(
                (
                    appt_id,
                    tenant,
                    patients[i % len(patients)]["id"],
                    None,
                    marker,
                    services[i % len(services)]["id"],
                    status,
                    "MANUAL_STAFF",
                    "MANUAL",
                    start,
                    end,
                    None,
                    1,
                    now,
                    now,
                )
            )
            alloc_batch.append(
                (
                    new_uuid7(),
                    tenant,
                    appt_id,
                    resources[i % len(resources)]["id"],
                    "MANUAL_STAFF",
                    "MANUAL",
                    status,
                    start,
                    end,
                    now,
                )
            )
            if len(appt_batch) >= 2000:
                await flush()
                if (i + 1) % 20_000 == 0:
                    print(f"  …{i + 1}", flush=True)
        await flush()

        async def timed(label: str, sql: str, *params) -> None:
            samples: list[float] = []
            last = 0
            for _ in range(args.repeats):
                t0 = time.perf_counter()
                last = await conn.fetchval(sql, *params)
                samples.append((time.perf_counter() - t0) * 1000)
            report["queries"].append(
                {
                    "label": label,
                    "median_ms": statistics.median(samples),
                    "samples_ms": samples,
                    "result": last,
                }
            )
            print(
                f"{label:40s} median={statistics.median(samples):7.1f}ms  n={last}",
                flush=True,
            )

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        await timed(
            "count_all_tenant",
            "SELECT count(*) FROM appointments WHERE tenant_id=$1",
            tenant,
        )
        await timed(
            "count_status_checked_in",
            "SELECT count(*) FROM appointments WHERE tenant_id=$1 AND status='CHECKED_IN'",
            tenant,
        )
        await timed(
            "count_day_window",
            """
            SELECT count(*) FROM appointments
            WHERE tenant_id=$1 AND scheduled_start_at_utc >= $2 AND scheduled_start_at_utc < $3
            """,
            tenant,
            day_start,
            day_end,
        )
        await timed(
            "page_day_limit_50",
            """
            SELECT count(*) FROM (
              SELECT id FROM appointments
              WHERE tenant_id=$1 AND scheduled_start_at_utc >= $2 AND scheduled_start_at_utc < $3
              ORDER BY scheduled_start_at_utc, id
              LIMIT 50 OFFSET 0
            ) t
            """,
            tenant,
            day_start,
            day_end,
        )
        await timed(
            "filter_service_page",
            """
            SELECT count(*) FROM (
              SELECT id FROM appointments
              WHERE tenant_id=$1 AND service_id=$2
              ORDER BY scheduled_start_at_utc DESC, id
              LIMIT 50 OFFSET 0
            ) t
            """,
            tenant,
            services[0]["id"],
        )

        report["tenant_id"] = str(tenant)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}", flush=True)
        return 0
    finally:
        deleted_alloc = await conn.execute(
            """
            DELETE FROM appointment_resource_allocations a
            USING appointments ap
            WHERE a.tenant_id = ap.tenant_id
              AND a.appointment_id = ap.id
              AND ap.patient_booking_note = $1
            """,
            marker,
        )
        deleted_appt = await conn.execute(
            "DELETE FROM appointments WHERE patient_booking_note=$1",
            marker,
        )
        print(f"Cleanup: {deleted_alloc}; {deleted_appt}", flush=True)
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
