"""Composition helpers that keep UoW + repositories on one AsyncSession."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.application.scheduling.handler import ScheduleAppointmentHandler
from clinic_ecosystem.infrastructure.persistence.appointment_repository import (
    SqlAppointmentRepository,
)
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.idempotency import SqlIdempotencyStore
from clinic_ecosystem.infrastructure.persistence.outbox import SqlOutboxStore
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


class _SessionScopedContainer:
    def __init__(self, session: AsyncSession, *, owns_session: bool) -> None:
        self.session = session
        self.uow = SqlAlchemyUnitOfWork(session, owns_session=owns_session)
        self.appointments = SqlAppointmentRepository(session)
        self.idempotency = SqlIdempotencyStore(session)
        self.outbox = SqlOutboxStore(session)
        self.audit = SqlAuditStore(session)
        self.permissions = SqlPermissionService(session)


class _PortProxy:
    def __init__(self, holder: dict[str, _SessionScopedContainer], attr: str) -> None:
        self._holder = holder
        self._attr = attr

    def __getattr__(self, name: str):
        container = self._holder.get("active")
        if container is None:
            raise RuntimeError("no active scheduling UoW session")
        return getattr(getattr(container, self._attr), name)


def build_schedule_appointment_handler(engine: AsyncEngine) -> ScheduleAppointmentHandler:
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    holder: dict[str, _SessionScopedContainer] = {}

    @asynccontextmanager
    async def uow_factory() -> AsyncIterator[SqlAlchemyUnitOfWork]:
        session = session_factory()
        container = _SessionScopedContainer(session, owns_session=True)
        holder["active"] = container
        try:
            async with container.uow as uow:
                yield uow
        finally:
            holder.pop("active", None)

    return ScheduleAppointmentHandler(
        uow_factory=uow_factory,
        appointments=_PortProxy(holder, "appointments"),  # type: ignore[arg-type]
        idempotency=_PortProxy(holder, "idempotency"),  # type: ignore[arg-type]
        outbox=_PortProxy(holder, "outbox"),  # type: ignore[arg-type]
        audit=_PortProxy(holder, "audit"),  # type: ignore[arg-type]
        permissions=_PortProxy(holder, "permissions"),  # type: ignore[arg-type]
    )


def build_handler_for_session(session: AsyncSession) -> ScheduleAppointmentHandler:
    """Single externally managed session for the whole handle() call (tests)."""
    container = _SessionScopedContainer(session, owns_session=False)

    @asynccontextmanager
    async def uow_factory() -> AsyncIterator[SqlAlchemyUnitOfWork]:
        try:
            yield container.uow
        except Exception:
            if not container.uow._committed:
                await container.uow.rollback()
            raise

    return ScheduleAppointmentHandler(
        uow_factory=uow_factory,
        appointments=container.appointments,
        idempotency=container.idempotency,
        outbox=container.outbox,
        audit=container.audit,
        permissions=container.permissions,
    )
