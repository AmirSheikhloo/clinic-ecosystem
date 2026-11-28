"""Login and principal resolution for BETA-01A."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from clinic_ecosystem.application.auth.exceptions import (
    AccountUnavailable,
    AuthRealmUnavailable,
    InvalidCredentials,
)
from clinic_ecosystem.infrastructure.auth.access_tokens import (
    AccessTokenClaims,
    issue_access_token,
)
from clinic_ecosystem.infrastructure.auth.demo_aliases import resolve_login_identifier
from clinic_ecosystem.infrastructure.auth.passwords import verify_password
from clinic_ecosystem.infrastructure.auth.settings import (
    AuthSettings,
    require_usable_auth_realm,
    AuthSettingsError,
)
from clinic_ecosystem.infrastructure.persistence.user_accounts import (
    SqlUserAccountRepository,
    UserAccountRecord,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    token_type: str
    expires_in: int
    claims: AccessTokenClaims
    account: UserAccountRecord


def normalize_login_identifier(raw: str) -> str:
    return raw.strip().lower()


class AuthService:
    def __init__(self, *, settings: AuthSettings) -> None:
        self._settings = settings

    async def login(
        self,
        *,
        uow: SqlAlchemyUnitOfWork,
        login_identifier: str,
        password: str,
        now: datetime | None = None,
    ) -> LoginResult:
        current = now or datetime.now(timezone.utc)
        try:
            realm_tenant_id = require_usable_auth_realm(self._settings)
        except AuthSettingsError as exc:
            raise AuthRealmUnavailable() from exc

        # Pre-auth scope: bind ONLY the server-configured synthetic realm tenant.
        # Never accept a client-supplied tenant_id for app.current_tenant_id.
        await uow.bind_tenant(realm_tenant_id)
        users = SqlUserAccountRepository(uow.session)
        # Isolated-preview aliases only (fail closed when catalog disabled).
        resolved = resolve_login_identifier(login_identifier)
        normalized = normalize_login_identifier(resolved)
        # Row lock serializes concurrent failure counting / successful reset.
        account = await users.find_by_normalized_login(
            tenant_id=realm_tenant_id,
            normalized_login=normalized,
            for_update=True,
        )
        if account is None:
            raise InvalidCredentials()

        if not account.is_active:
            raise AccountUnavailable()
        if account.locked_until_utc is not None and account.locked_until_utc > current:
            raise AccountUnavailable()

        if not verify_password(account.password_hash_argon2id, password):
            await users.record_failed_login(
                tenant_id=realm_tenant_id,
                account_id=account.id,
                max_failed_attempts=self._settings.max_failed_login_attempts,
                lockout_minutes=self._settings.lockout_minutes,
                now=current,
            )
            await uow.commit()
            raise InvalidCredentials()

        await users.clear_failed_logins(
            tenant_id=realm_tenant_id, account_id=account.id, now=current
        )
        token, claims = issue_access_token(
            settings=self._settings,
            principal_id=account.id,
            tenant_id=account.tenant_id,
            now=current,
        )
        await uow.commit()
        return LoginResult(
            access_token=token,
            token_type="Bearer",
            expires_in=self._settings.access_token_ttl_seconds,
            claims=claims,
            account=account,
        )

    async def load_active_account(
        self,
        *,
        uow: SqlAlchemyUnitOfWork,
        tenant_id: UUID,
        principal_id: UUID,
        now: datetime | None = None,
    ) -> UserAccountRecord:
        current = now or datetime.now(timezone.utc)
        await uow.bind_tenant(tenant_id)
        users = SqlUserAccountRepository(uow.session)
        account = await users.get_by_id(tenant_id=tenant_id, account_id=principal_id)
        if account is None or not account.is_active:
            raise InvalidCredentials()
        if account.locked_until_utc is not None and account.locked_until_utc > current:
            raise InvalidCredentials()
        if account.tenant_id != tenant_id:
            raise InvalidCredentials()
        return account
