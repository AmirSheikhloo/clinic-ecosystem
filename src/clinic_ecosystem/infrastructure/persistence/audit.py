"""Append-only audit store (write) and supervisory read queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(frozen=True, slots=True)
class AuditEntryRow:
    id: UUID
    actor_type: str
    actor_id: UUID | None
    actor_login: str | None
    operation: str
    target_type: str
    target_id: UUID | None
    details_json: dict[str, Any]
    created_at_utc: datetime


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

    async def list_page(
        self,
        *,
        tenant_id: UUID,
        operation: str | None,
        target_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AuditEntryRow], int]:
        """Newest-first page over audit_entries. Never decrypts or returns ciphertext."""
        where = ["ae.tenant_id = :tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "limit": limit,
            "offset": offset,
        }
        if operation:
            where.append("ae.operation = :operation")
            params["operation"] = operation
        if target_type:
            where.append("ae.target_type = :target_type")
            params["target_type"] = target_type
        clause = " AND ".join(where)
        total = await self._session.execute(
            text(f"SELECT count(*) FROM audit_entries ae WHERE {clause}"),
            params,
        )
        rows = await self._session.execute(
            text(
                f"""
                SELECT ae.id, ae.actor_type, ae.actor_id, ua.login_identifier AS actor_login,
                       ae.operation, ae.target_type, ae.target_id, ae.details_json,
                       ae.created_at_utc
                FROM audit_entries ae
                LEFT JOIN user_accounts ua
                  ON ua.tenant_id = ae.tenant_id AND ua.id = ae.actor_id
                WHERE {clause}
                ORDER BY ae.created_at_utc DESC, ae.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        items: list[AuditEntryRow] = []
        for row in rows.mappings():
            details = row["details_json"]
            if isinstance(details, str):
                details = json.loads(details)
            items.append(
                AuditEntryRow(
                    id=row["id"],
                    actor_type=row["actor_type"],
                    actor_id=row["actor_id"],
                    actor_login=row["actor_login"],
                    operation=row["operation"],
                    target_type=row["target_type"],
                    target_id=row["target_id"],
                    details_json=dict(details or {}),
                    created_at_utc=row["created_at_utc"],
                )
            )
        return items, int(total.scalar_one())
