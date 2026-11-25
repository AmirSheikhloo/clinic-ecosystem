"""Transactional idempotent execution shared by protected mutations (clauses 171-184).

The claim, business action, completion record, audit and outbox rows commit in
one transaction. Any failure rolls back the claim so a corrected retry can run.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import rfc8785
from sqlalchemy.exc import IntegrityError

from clinic_ecosystem.application.shared.errors import (
    IdempotencyInProgressError,
    IdempotencyKeyReuse,
    ValidationFailed,
)
from clinic_ecosystem.infrastructure.persistence.idempotency import SqlIdempotencyStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

MAX_KEY_LENGTH = 128


def fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def validate_key(key: str | None) -> str:
    if not key or not key.strip():
        raise ValidationFailed(
            "Idempotency-Key header is required", code="idempotency_key_required"
        )
    key = key.strip()
    if len(key) > MAX_KEY_LENGTH:
        raise ValidationFailed("Idempotency-Key is too long", code="idempotency_key_invalid")
    return key


async def run_idempotent(
    uow: SqlAlchemyUnitOfWork,
    *,
    tenant_id: UUID,
    principal_id: UUID,
    scope: str,
    key: str,
    request_payload: dict[str, Any],
    action: Callable[[], Awaitable[dict[str, Any]]],
) -> tuple[dict[str, Any], bool]:
    """Run ``action`` once per (principal, scope, key); return (response, replayed)."""
    store = SqlIdempotencyStore(uow.session)
    owner = new_uuid7()
    try:
        claim = await store.claim(
            tenant_id=tenant_id,
            principal_id=principal_id,
            operation_scope=scope,
            idempotency_key=key,
            request_fingerprint=fingerprint(request_payload),
            owner_token=owner,
        )
    except IntegrityError as exc:
        await uow.rollback()
        raise IdempotencyInProgressError("Another request with this key is in progress") from exc
    status = claim["status"]
    if status == "COMPLETED":
        await uow.commit()
        return claim["response_payload"], True
    if status == "IN_PROGRESS":
        await uow.rollback()
        raise IdempotencyInProgressError("Another request with this key is in progress")
    if status == "FINGERPRINT_CONFLICT":
        await uow.rollback()
        raise IdempotencyKeyReuse("Idempotency-Key was used with a different request")
    try:
        response = await action()
        await store.complete(
            tenant_id=tenant_id,
            principal_id=principal_id,
            operation_scope=scope,
            idempotency_key=key,
            owner_token=owner,
            response_payload=response,
        )
    except BaseException:
        await uow.rollback()
        raise
    await uow.commit()
    return response, False
