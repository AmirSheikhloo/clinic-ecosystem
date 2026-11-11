"""Transactional idempotency store (clauses 171–184)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlIdempotencyStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        tenant_id: UUID,
        principal_id: UUID,
        operation_scope: str,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token: UUID,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        # Serialize concurrent claimants on the identity row.
        existing = await self._session.execute(
            text(
                """
                SELECT id, request_fingerprint, state, response_payload, owner_token
                FROM idempotency_records
                WHERE tenant_id = :tenant_id
                  AND principal_id = :principal_id
                  AND operation_scope = :operation_scope
                  AND idempotency_key = :idempotency_key
                FOR UPDATE
                """
            ),
            {
                "tenant_id": tenant_id,
                "principal_id": principal_id,
                "operation_scope": operation_scope,
                "idempotency_key": idempotency_key,
            },
        )
        row = existing.first()
        if row is None:
            await self._session.execute(
                text(
                    """
                    INSERT INTO idempotency_records (
                        id, tenant_id, principal_id, operation_scope, idempotency_key,
                        request_fingerprint, state, response_payload, owner_token,
                        created_at_utc, updated_at_utc
                    ) VALUES (
                        :id, :tenant_id, :principal_id, :operation_scope, :idempotency_key,
                        :request_fingerprint, 'IN_PROGRESS', NULL, :owner_token,
                        :now_utc, :now_utc
                    )
                    """
                ),
                {
                    "id": new_uuid7(),
                    "tenant_id": tenant_id,
                    "principal_id": principal_id,
                    "operation_scope": operation_scope,
                    "idempotency_key": idempotency_key,
                    "request_fingerprint": request_fingerprint,
                    "owner_token": owner_token,
                    "now_utc": now,
                },
            )
            return {"status": "CLAIMED"}

        if row.request_fingerprint != request_fingerprint:
            return {"status": "FINGERPRINT_CONFLICT"}
        if row.state == "COMPLETED":
            payload = row.response_payload
            if isinstance(payload, str):
                payload = json.loads(payload)
            return {"status": "COMPLETED", "response_payload": payload}
        if row.state == "IN_PROGRESS":
            return {"status": "IN_PROGRESS"}
        # FAILED → reclaim
        await self._session.execute(
            text(
                """
                UPDATE idempotency_records
                SET state = 'IN_PROGRESS',
                    owner_token = :owner_token,
                    request_fingerprint = :request_fingerprint,
                    response_payload = NULL,
                    updated_at_utc = :now_utc
                WHERE id = :id AND tenant_id = :tenant_id
                """
            ),
            {
                "id": row.id,
                "tenant_id": tenant_id,
                "owner_token": owner_token,
                "request_fingerprint": request_fingerprint,
                "now_utc": now,
            },
        )
        return {"status": "CLAIMED"}

    async def complete(
        self,
        *,
        tenant_id: UUID,
        principal_id: UUID,
        operation_scope: str,
        idempotency_key: str,
        owner_token: UUID,
        response_payload: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            text(
                """
                UPDATE idempotency_records
                SET state = 'COMPLETED',
                    response_payload = CAST(:payload AS jsonb),
                    updated_at_utc = :now_utc
                WHERE tenant_id = :tenant_id
                  AND principal_id = :principal_id
                  AND operation_scope = :operation_scope
                  AND idempotency_key = :idempotency_key
                  AND owner_token = :owner_token
                  AND state = 'IN_PROGRESS'
                """
            ),
            {
                "tenant_id": tenant_id,
                "principal_id": principal_id,
                "operation_scope": operation_scope,
                "idempotency_key": idempotency_key,
                "owner_token": owner_token,
                "payload": json.dumps(response_payload),
                "now_utc": now,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError("idempotency complete failed: owner mismatch or missing claim")
