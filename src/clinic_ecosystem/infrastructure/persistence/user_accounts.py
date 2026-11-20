"""user_accounts lookups and login lockout updates under an active tenant GUC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class UserAccountRecord:
    id: UUID
    tenant_id: UUID
    person_id: UUID
    login_identifier: str
    normalized_login_identifier: str
    password_hash_argon2id: str
    is_active: bool
    failed_login_attempts: int
    locked_until_utc: datetime | None


def _row_to_account(row) -> UserAccountRecord:
    return UserAccountRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        person_id=row["person_id"],
        login_identifier=row["login_identifier"],
        normalized_login_identifier=row["normalized_login_identifier"],
        password_hash_argon2id=row["password_hash_argon2id"],
        is_active=bool(row["is_active"]),
        failed_login_attempts=int(row["failed_login_attempts"]),
        locked_until_utc=row["locked_until_utc"],
    )


class SqlUserAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_normalized_login(
        self,
        *,
        tenant_id: UUID,
        normalized_login: str,
        for_update: bool = False,
    ) -> UserAccountRecord | None:
        lock = " FOR UPDATE" if for_update else ""
        result = await self._session.execute(
            text(
                f"""
                SELECT id, tenant_id, person_id, login_identifier,
                       normalized_login_identifier, password_hash_argon2id,
                       is_active, failed_login_attempts, locked_until_utc
                FROM user_accounts
                WHERE tenant_id = :tenant_id
                  AND normalized_login_identifier = :normalized_login
                LIMIT 1{lock}
                """
            ),
            {"tenant_id": tenant_id, "normalized_login": normalized_login},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_account(row)

    async def get_by_id(
        self, *, tenant_id: UUID, account_id: UUID
    ) -> UserAccountRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, tenant_id, person_id, login_identifier,
                       normalized_login_identifier, password_hash_argon2id,
                       is_active, failed_login_attempts, locked_until_utc
                FROM user_accounts
                WHERE tenant_id = :tenant_id AND id = :account_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "account_id": account_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_account(row)

    async def record_failed_login(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        max_failed_attempts: int,
        lockout_minutes: int,
        now: datetime | None = None,
    ) -> UserAccountRecord | None:
        """Atomically increment failures and apply lockout without read-modify-write races."""
        if max_failed_attempts < 1 or lockout_minutes < 1:
            raise ValueError("lockout thresholds must be positive")
        current = now or datetime.now(timezone.utc)
        lock_until = current + timedelta(minutes=lockout_minutes)
        result = await self._session.execute(
            text(
                """
                UPDATE user_accounts
                SET failed_login_attempts = failed_login_attempts + 1,
                    locked_until_utc = CASE
                        WHEN failed_login_attempts + 1 >= :max_failed THEN
                            CASE
                                WHEN locked_until_utc IS NULL
                                     OR locked_until_utc < :lock_until
                                THEN :lock_until
                                ELSE locked_until_utc
                            END
                        ELSE locked_until_utc
                    END,
                    updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :account_id
                RETURNING id, tenant_id, person_id, login_identifier,
                          normalized_login_identifier, password_hash_argon2id,
                          is_active, failed_login_attempts, locked_until_utc
                """
            ),
            {
                "max_failed": max_failed_attempts,
                "lock_until": lock_until,
                "now": current,
                "tenant_id": tenant_id,
                "account_id": account_id,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_account(row)

    async def clear_failed_logins(
        self, *, tenant_id: UUID, account_id: UUID, now: datetime | None = None
    ) -> UserAccountRecord | None:
        """Reset lockout state for a row already locked in the current transaction."""
        current = now or datetime.now(timezone.utc)
        result = await self._session.execute(
            text(
                """
                UPDATE user_accounts
                SET failed_login_attempts = 0,
                    locked_until_utc = NULL,
                    updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :account_id
                RETURNING id, tenant_id, person_id, login_identifier,
                          normalized_login_identifier, password_hash_argon2id,
                          is_active, failed_login_attempts, locked_until_utc
                """
            ),
            {
                "now": current,
                "tenant_id": tenant_id,
                "account_id": account_id,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_account(row)
