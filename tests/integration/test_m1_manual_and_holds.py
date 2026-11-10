"""MANUAL overbooking, hold expiry worker, and concurrency smoke tests."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.domain.scheduling.exceptions import (
    ManualOverlapAcknowledgementRequired,
)
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool
from clinic_ecosystem.infrastructure.persistence.compose import build_handler_for_session
from clinic_ecosystem.infrastructure.persistence.hold_expiry_worker import HoldExpirationWorker
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


@pytest.mark.asyncio
async def test_manual_overlap_requires_ack_then_audits(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=12)
    end = start + timedelta(minutes=30)

    async def schedule(*, key: str, ack: bool):
        cmd = ScheduleAppointmentCommand(
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
        )
        async with session_factory() as session:
            return await build_handler_for_session(session).handle(cmd)

    await schedule(key="manual-1", ack=False)
    with pytest.raises(ManualOverlapAcknowledgementRequired):
        await schedule(key="manual-2", ack=False)
    result = await schedule(key="manual-3", ack=True)
    assert result.replayed is False

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        audits = await conn.fetchval(
            """
            SELECT count(*) FROM audit_entries
            WHERE tenant_id = $1 AND operation = 'ALLOW_MANUAL_OVERBOOKING'
            """,
            ids.tenant_id,
        )
        appts = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1 AND capacity_pool = 'MANUAL'",
            ids.tenant_id,
        )
        assert audits == 1
        assert appts == 2
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
    # Already expired hold
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
