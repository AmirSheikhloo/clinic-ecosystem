"""Transactional Outbox staging (clauses 213–224)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlOutboxStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def stage(self, *, tenant_id: UUID, message_type: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO outbox_messages (
                    id, tenant_id, message_type, payload_json, created_at_utc,
                    locked_until, lease_id, delivered_at_utc, attempt_count
                ) VALUES (
                    :id, :tenant_id, :message_type, CAST(:payload AS jsonb), :now_utc,
                    NULL, NULL, NULL, 0
                )
                """
            ),
            {
                "id": new_uuid7(),
                "tenant_id": tenant_id,
                "message_type": message_type,
                "payload": json.dumps(payload),
                "now_utc": now,
            },
        )
