"""SQLAlchemy async Unit of Work with transaction-local tenant binding."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession, *, owns_session: bool = False) -> None:
        self.session = session
        self._owns_session = owns_session
        self._committed = False

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None and not self._committed:
            await self.rollback()
        if self._owns_session:
            await self.session.close()

    async def bind_tenant(self, tenant_id: UUID) -> None:
        # Transaction-local GUC; must not leak across pooled connections (clause 747).
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )

    async def commit(self) -> None:
        await self.session.commit()
        self._committed = True

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()


def uow_factory_from_engine(engine: AsyncEngine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @asynccontextmanager
    async def _factory() -> AsyncIterator[SqlAlchemyUnitOfWork]:
        session = factory()
        uow = SqlAlchemyUnitOfWork(session, owns_session=True)
        async with uow:
            yield uow

    return _factory
