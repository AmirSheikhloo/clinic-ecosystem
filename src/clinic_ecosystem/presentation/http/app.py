"""FastAPI application for BETA-01A auth/catalog + BETA-01B reception APIs."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from clinic_ecosystem.infrastructure.auth.db_role_preflight import (
    UnsafeDatabaseRoleError,
    verify_runtime_db_role,
)
from clinic_ecosystem.infrastructure.auth.settings import (
    AuthSettings,
    AuthSettingsError,
    load_auth_settings,
    require_token_signing_secret,
)
from clinic_ecosystem.presentation.http import access as access_routes
from clinic_ecosystem.presentation.http import appointment_admin as appointment_admin_routes
from clinic_ecosystem.presentation.http import appointments as appointment_routes
from clinic_ecosystem.presentation.http import audit as audit_routes
from clinic_ecosystem.presentation.http import auth as auth_routes
from clinic_ecosystem.presentation.http import catalog as catalog_routes
from clinic_ecosystem.presentation.http import catalog_admin as catalog_admin_routes
from clinic_ecosystem.presentation.http import finance as finance_routes
from clinic_ecosystem.presentation.http import historical as historical_routes
from clinic_ecosystem.presentation.http import ops_management as ops_management_routes
from clinic_ecosystem.presentation.http import overview as overview_routes
from clinic_ecosystem.presentation.http import patient_ops as patient_ops_routes
from clinic_ecosystem.presentation.http import patient_registry as patient_registry_routes
from clinic_ecosystem.presentation.http import patients as patient_routes
from clinic_ecosystem.presentation.http.common import install_problem_handlers
from clinic_ecosystem.presentation.http import resources as resource_routes
from clinic_ecosystem.presentation.http import staff as staff_routes
from clinic_ecosystem.presentation.http import waitlist as waitlist_routes

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

    When a real ``AsyncEngine`` is present, a fail-closed runtime-role preflight
    runs before serving. Non-engine test doubles skip that probe so unit tests can
    inject dependencies without a privilege-check bypass switch.
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
        app.state.db_role_verified = False

        if isinstance(active_engine, AsyncEngine):
            try:
                await verify_runtime_db_role(active_engine)
            except UnsafeDatabaseRoleError as exc:
                logger.error("refusing to start: unsafe database role")
                raise AuthSettingsError(str(exc)) from exc
            app.state.db_role_verified = True

        # Never log secrets, DSNs with passwords, or tokens.
        logger.info(
            "BETA-01B API starting env=%s realm_enabled=%s db_role_verified=%s",
            resolved_settings.clinic_env,
            resolved_settings.auth_realm_enabled,
            app.state.db_role_verified,
        )
        try:
            yield
        finally:
            if owned_engine is not None:
                await owned_engine.dispose()

    app = FastAPI(
        title="Clinic Ecosystem BETA-01B",
        version="0.1.0-beta-01b",
        lifespan=lifespan,
    )
    app.state.auth_settings = resolved_settings
    app.state.db_role_verified = False
    if engine is not None:
        app.state.engine = engine

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    install_problem_handlers(app)
    app.include_router(auth_routes.router)
    app.include_router(catalog_routes.router)
    app.include_router(catalog_admin_routes.router)
    app.include_router(resource_routes.router)
    app.include_router(patient_routes.router)
    app.include_router(patient_registry_routes.router)
    app.include_router(staff_routes.router)
    app.include_router(access_routes.router)
    app.include_router(audit_routes.router)
    app.include_router(overview_routes.router)
    app.include_router(appointment_routes.router)
    app.include_router(appointment_admin_routes.router)
    app.include_router(finance_routes.router)
    app.include_router(waitlist_routes.router)
    app.include_router(ops_management_routes.router)
    app.include_router(patient_ops_routes.router)
    app.include_router(historical_routes.router)
    return app
