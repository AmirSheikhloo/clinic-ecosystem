"""Append-only audit store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlAuditStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        tenant_id: UUID,
        actor_type: str,
        actor_id: UUID | None,
        operation: str,
        target_type: str,
        target_id: UUID | None,
        details: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO audit_entries (
                    id, tenant_id, actor_type, actor_id, operation,
                    target_type, target_id, details_json, created_at_utc
                ) VALUES (
                    :id, :tenant_id, :actor_type, :actor_id, :operation,
                    :target_type, :target_id, CAST(:details AS jsonb), :now_utc
                )
                """
            ),
            {
                "id": new_uuid7(),
                "tenant_id": tenant_id,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "operation": operation,
                "target_type": target_type,
                "target_id": target_id,
                "details": json.dumps(details, default=str),
                "now_utc": now,
            },
        )
