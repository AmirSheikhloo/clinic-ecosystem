"""ScheduleAppointmentHandler integration evidence (happy path, idempotency, ONLINE conflict)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clinic_ecosystem.application.scheduling.commands import ScheduleAppointmentCommand
from clinic_ecosystem.application.scheduling.exceptions import IdempotencyConflict
from clinic_ecosystem.domain.scheduling.exceptions import CapacityConflictException
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool
from clinic_ecosystem.infrastructure.persistence.compose import build_handler_for_session
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON
from tests.integration.m1_seed import seed_scheduling_graph

pytestmark = pytest.mark.integration


def _app_url(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    from urllib.parse import quote_plus

    return (
        f"postgresql+asyncpg://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


def _app_dsn(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    from urllib.parse import quote_plus

    return (
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


async def _ensure_migrated(plane_topology) -> None:
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())


@pytest.mark.asyncio
async def test_schedule_online_creates_appointment_outbox_idempotency(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    # Seed via migrator (bypasses RLS for fixture setup), then run handler as runtime.
    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await seed_conn.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(seed_conn)
        await seed_conn.execute("RESET ROLE")
    finally:
        await seed_conn.close()

    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    end = start + timedelta(minutes=30)
    hold = start + timedelta(minutes=15)
    command = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="online-1",
        request_fingerprint="fp-online-1",
        principal_id=ids.user_account_id,
        actor_type="USER",
        tenant_id=ids.tenant_id,
        beneficiary_patient_id=ids.patient_id,
        booker_person_id=ids.person_id,
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
        handler = build_handler_for_session(session)
        result = await handler.handle(command)
    assert result.replayed is False

    # Replay
    async with session_factory() as session:
        handler = build_handler_for_session(session)
        replay = await handler.handle(command)
    assert replay.replayed is True
    assert replay.appointment_id == result.appointment_id

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        appt_count = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1", ids.tenant_id
        )
        outbox_count = await conn.fetchval(
            "SELECT count(*) FROM outbox_messages WHERE tenant_id = $1 AND message_type = 'appointment.scheduled'",
            ids.tenant_id,
        )
        idem = await conn.fetchrow(
            """
            SELECT state, response_payload->>'appointment_id' AS appt
            FROM idempotency_records
            WHERE tenant_id = $1 AND idempotency_key = 'online-1'
            """,
            ids.tenant_id,
        )
        hold_items = await conn.fetchval(
            "SELECT count(*) FROM hold_expiry_work_items WHERE tenant_id = $1",
            ids.tenant_id,
        )
        assert appt_count == 1
        assert outbox_count == 1
        assert idem["state"] == "COMPLETED"
        assert UUID(idem["appt"]) == result.appointment_id
        assert hold_items == 1
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_online_overlap_raises_capacity_conflict(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)

    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await seed_conn.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(seed_conn)
        await seed_conn.execute("RESET ROLE")
    finally:
        await seed_conn.close()

    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=5)
    end = start + timedelta(minutes=30)
    hold = start + timedelta(minutes=10)
    base_kwargs = dict(
        principal_id=ids.user_account_id,
        actor_type="USER",
        tenant_id=ids.tenant_id,
        beneficiary_patient_id=ids.patient_id,
        booker_person_id=ids.person_id,
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
    first = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="online-a",
        request_fingerprint="fp-a",
        **base_kwargs,
    )
    second = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="online-b",
        request_fingerprint="fp-b",
        **base_kwargs,
    )
    async with session_factory() as session:
        handler = build_handler_for_session(session)
        await handler.handle(first)

    async with session_factory() as session:
        handler = build_handler_for_session(session)
        with pytest.raises(CapacityConflictException):
            await handler.handle(second)
    await engine.dispose()


@pytest.mark.asyncio
async def test_idempotency_fingerprint_conflict(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await _ensure_migrated(plane_topology)
    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await seed_conn.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(seed_conn)
        await seed_conn.execute("RESET ROLE")
    finally:
        await seed_conn.close()

    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=8)
    end = start + timedelta(minutes=30)
    cmd1 = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="same-key",
        request_fingerprint="fp-1",
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
        acknowledge_overlap=False,
    )
    async with session_factory() as session:
        await build_handler_for_session(session).handle(cmd1)

    cmd2 = ScheduleAppointmentCommand(
        correlation_id=new_uuid7(),
        idempotency_key="same-key",
        request_fingerprint="fp-DIFFERENT",
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
        acknowledge_overlap=False,
    )
    async with session_factory() as session:
        with pytest.raises(IdempotencyConflict):
            await build_handler_for_session(session).handle(cmd2)
    await engine.dispose()
