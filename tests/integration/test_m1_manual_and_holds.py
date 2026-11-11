"""MANUAL overbooking, hold expiry worker, and concurrency smoke tests."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import (
    ManualOverlapAcknowledgementRequired,
    UnauthorizedScheduling,
)
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool
from clinic_ecosystem.infrastructure.persistence.compose import build_handler_for_session
from clinic_ecosystem.infrastructure.persistence.hold_expiry_worker import HoldExpirationWorker
from clinic_ecosystem.presentation.scheduling import serialize_manual_conflict_response
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON
from tests.integration.m1_seed import seed_scheduling_graph
from tests.integration.test_m1_schedule_appointment import _app_dsn, _app_url

pytestmark = pytest.mark.integration


async def _seed(plane_topology, **kwargs):
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await seed_conn.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(seed_conn, **kwargs)
        await seed_conn.execute("RESET ROLE")
        return ids
    finally:
        await seed_conn.close()


def _cmd(ids, *, key: str, ack: bool, ack_ids=(), start=None, end=None):
    start = start or (datetime.now(timezone.utc) + timedelta(hours=12))
    end = end or (start + timedelta(minutes=30))
    return ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key=key,
        request_fingerprint=key,
        principal_id=ids.user_account_id,
        actor_type="USER",
        tenant_id=ids.tenant_id,
        beneficiary_patient_id=ids.patient_id,
        booker_person_id=None,
        patient_booking_note=None,
        service_id=ids.service_id,
        booking_channel=BookingChannel.MANUAL_STAFF,
        capacity_pool=CapacityPool.MANUAL,
        resource_ids=(ids.resource_id,),
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=None,
        acknowledge_overlap=ack,
        acknowledged_conflict_ids=tuple(ack_ids),
    )


@pytest.mark.asyncio
async def test_manual_overlap_requires_ack_then_audits(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=12)
    end = start + timedelta(minutes=30)

    async def schedule(*, key: str, ack: bool, ack_ids=()):
        async with session_factory() as session:
            return await build_handler_for_session(session).handle(
                _cmd(ids, key=key, ack=ack, ack_ids=ack_ids, start=start, end=end)
            )

    first = await schedule(key="manual-1", ack=False)
    with pytest.raises(ManualOverlapAcknowledgementRequired) as excinfo:
        await schedule(key="manual-2", ack=False)
    body = serialize_manual_conflict_response(excinfo.value)
    assert body["conflicts"][0]["display_safe_patient_name"] == "Ada Clinic"
    assert body["conflicts"][0]["appointment_id"] == str(first.appointment_id)

    result = await schedule(
        key="manual-3", ack=True, ack_ids=(first.appointment_id,)
    )
    assert result.replayed is False

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        audits = await conn.fetch(
            """
            SELECT details_json FROM audit_entries
            WHERE tenant_id = $1 AND operation = 'ALLOW_MANUAL_OVERBOOKING'
            """,
            ids.tenant_id,
        )
        assert len(audits) == 1
        details = audits[0]["details_json"]
        snap = details["conflict_snapshot"]
        assert len(snap) == 1
        assert snap[0]["appointment_id"] == str(first.appointment_id)
        assert str(result.appointment_id) not in {
            row["appointment_id"] for row in snap
        }
        assert "display_safe_patient_name" not in snap[0]
        appts = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1 AND capacity_pool = 'MANUAL'",
            ids.tenant_id,
        )
        assert appts == 2
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_manual_denied_without_permission_rolls_back(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=False)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=14)
    end = start + timedelta(minutes=30)

    async with session_factory() as session:
        first = await build_handler_for_session(session).handle(
            _cmd(ids, key="deny-1", ack=False, start=start, end=end)
        )
    with pytest.raises(UnauthorizedScheduling):
        async with session_factory() as session:
            await build_handler_for_session(session).handle(
                _cmd(
                    ids,
                    key="deny-2",
                    ack=True,
                    ack_ids=(first.appointment_id,),
                    start=start,
                    end=end,
                )
            )

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM appointments WHERE tenant_id = $1", ids.tenant_id
            )
            == 1
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM audit_entries WHERE tenant_id = $1", ids.tenant_id
            )
            == 0
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM outbox_messages WHERE tenant_id = $1",
                ids.tenant_id,
            )
            == 1
        )
        assert (
            await conn.fetchval(
                """
                SELECT count(*) FROM idempotency_records
                WHERE tenant_id = $1 AND idempotency_key = 'deny-2' AND state = 'COMPLETED'
                """,
                ids.tenant_id,
            )
            == 0
        )
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hold_expiry_worker_claim_then_expire(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology)
    engine = create_async_engine(_app_url(plane_topology), pool_size=4)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    end = start + timedelta(minutes=30)
    hold = datetime.now(timezone.utc) - timedelta(minutes=1)
    cmd = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="hold-1",
        request_fingerprint="hold-1",
        principal_id=ids.user_account_id,
        actor_type="USER",
        tenant_id=ids.tenant_id,
        beneficiary_patient_id=ids.patient_id,
        booker_person_id=None,
        patient_booking_note=None,
        service_id=ids.service_id,
        booking_channel=BookingChannel.ONLINE_WEB,
        capacity_pool=CapacityPool.ONLINE,
        resource_ids=(ids.resource_id,),
        start_at_utc=start,
        end_at_utc=end,
        hold_expires_at_utc=hold,
        acknowledge_overlap=False,
    )
    async with session_factory() as session:
        await build_handler_for_session(session).handle(cmd)

    @asynccontextmanager
    async def session_cm():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    worker = HoldExpirationWorker(
        claim_session_factory=session_cm,
        scheduling_session_factory=session_cm,
        worker_id="worker-1",
    )
    claim = await worker.claim_due_work(tenant_id=ids.tenant_id)
    assert claim is not None
    outcome = await worker.process_claim(claim)
    assert outcome == "DONE"

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        status = await conn.fetchval(
            "SELECT status FROM appointments WHERE tenant_id = $1", ids.tenant_id
        )
        alloc = await conn.fetchval(
            "SELECT allocation_status FROM appointment_resource_allocations WHERE tenant_id = $1",
            ids.tenant_id,
        )
        work = await conn.fetchval(
            "SELECT work_state FROM hold_expiry_work_items WHERE tenant_id = $1",
            ids.tenant_id,
        )
        assert status == "EXPIRED_HOLD"
        assert alloc == "EXPIRED_HOLD"
        assert work == "DONE"
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_online_bookings_only_one_wins(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology)
    engine = create_async_engine(_app_url(plane_topology), pool_size=8)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=20)
    end = start + timedelta(minutes=30)
    hold = start + timedelta(minutes=10)

    async def attempt(i: int) -> str:
        cmd = ScheduleAppointmentCommand(
            correlation_id=new_uuid7(),
            idempotency_key=f"concurrent-{i}",
            request_fingerprint=f"concurrent-{i}",
            principal_id=ids.user_account_id,
            actor_type="USER",
            tenant_id=ids.tenant_id,
            beneficiary_patient_id=ids.patient_id,
            booker_person_id=None,
            patient_booking_note=None,
            service_id=ids.service_id,
            booking_channel=BookingChannel.ONLINE_WEB,
            capacity_pool=CapacityPool.ONLINE,
            resource_ids=(ids.resource_id,),
            start_at_utc=start,
            end_at_utc=end,
            hold_expires_at_utc=hold,
            acknowledge_overlap=False,
        )
        try:
            async with session_factory() as session:
                await build_handler_for_session(session).handle(cmd)
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__

    results = await asyncio.gather(*[attempt(i) for i in range(8)])
    assert results.count("ok") == 1
    assert results.count("CapacityConflictException") >= 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_manual_writers_serialize_on_resource_lock(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=8)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=22)
    end = start + timedelta(minutes=30)

    async with session_factory() as session:
        first = await build_handler_for_session(session).handle(
            _cmd(ids, key="man-c-seed", ack=False, start=start, end=end)
        )

    async def attempt(i: int) -> str:
        try:
            async with session_factory() as session:
                await build_handler_for_session(session).handle(
                    _cmd(
                        ids,
                        key=f"man-c-{i}",
                        ack=True,
                        ack_ids=(first.appointment_id,),
                        start=start,
                        end=end,
                    )
                )
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__

    results = await asyncio.gather(*[attempt(i) for i in range(6)])
    # Exactly one additional MANUAL booking may succeed with the same ack set;
    # others must observe a changed conflict set and require re-ack.
    assert results.count("ok") == 1
    assert results.count("ManualOverlapAcknowledgementRequired") >= 1
    await engine.dispose()
