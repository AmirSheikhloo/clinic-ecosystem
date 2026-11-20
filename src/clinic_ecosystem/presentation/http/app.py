"""Minimal FastAPI application for BETA-01A auth + catalog read slice."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from clinic_ecosystem.infrastructure.auth.settings import (
    AuthSettings,
    AuthSettingsError,
    load_auth_settings,
    require_token_signing_secret,
)
from clinic_ecosystem.presentation.http import auth as auth_routes
from clinic_ecosystem.presentation.http import catalog as catalog_routes

logger = logging.getLogger("clinic_ecosystem.http")


def create_app(
    *,
    settings: AuthSettings | None = None,
    engine: AsyncEngine | None = None,
    create_engine_from_settings: bool = True,
) -> FastAPI:
    """Build the FastAPI app.

    Tests may inject ``settings`` and ``engine``. Production/dev entrypoints load
    settings from the environment and create an engine from CLINIC_DATABASE_URL.
    """

    resolved_settings = settings if settings is not None else load_auth_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned_engine: AsyncEngine | None = None
        try:
            require_token_signing_secret(resolved_settings)
        except AuthSettingsError as exc:
            logger.error("refusing to start: %s", exc)
            raise

        active_engine = engine
        if active_engine is None and create_engine_from_settings:
            if not resolved_settings.database_url:
                raise AuthSettingsError("CLINIC_DATABASE_URL is required to start the API")
            owned_engine = create_async_engine(
                resolved_settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
            )
            active_engine = owned_engine
        if active_engine is None:
            raise AuthSettingsError("database engine is required")

        app.state.auth_settings = resolved_settings
        app.state.engine = active_engine
        # Never log secrets, DSNs with passwords, or tokens.
        logger.info(
            "BETA-01A API starting env=%s realm_enabled=%s",
            resolved_settings.clinic_env,
            resolved_settings.auth_realm_enabled,
        )
        try:
            yield
        finally:
            if owned_engine is not None:
                await owned_engine.dispose()

    app = FastAPI(
        title="Clinic Ecosystem BETA-01A",
        version="0.1.0-beta-01a",
        lifespan=lifespan,
    )
    app.state.auth_settings = resolved_settings
    if engine is not None:
        app.state.engine = engine

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_routes.router)
    app.include_router(catalog_routes.router)
    return app
