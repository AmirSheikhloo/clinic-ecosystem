"""Disposable thermal print-job persistence (synthetic ops only)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlPrintJobs:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schema_ready(self) -> bool:
        row = await self._session.execute(
            text("SELECT to_regclass('public.thermal_print_jobs') IS NOT NULL AS ok")
        )
        return bool(row.mappings().one()["ok"])

    async def ensure_schema(self) -> None:
        """Create IF NOT EXISTS for disposable preview DBs already past ledger apply."""
        await self._session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS thermal_print_jobs (
                  id UUID PRIMARY KEY,
                  tenant_id UUID NOT NULL,
                  job_kind VARCHAR(24) NOT NULL,
                  status VARCHAR(24) NOT NULL,
                  invoice_id UUID,
                  invoice_number VARCHAR(64),
                  beneficiary_patient_id UUID,
                  workstation_id VARCHAR(64) NOT NULL,
                  width_mm SMALLINT NOT NULL,
                  batch_id UUID,
                  parent_job_id UUID,
                  attempt INT NOT NULL DEFAULT 1,
                  adapter_mode VARCHAR(32) NOT NULL DEFAULT 'simulated',
                  hardware_claim VARCHAR(40) NOT NULL DEFAULT 'none',
                  snapshot_json JSONB NOT NULL,
                  rendered_text TEXT NOT NULL,
                  adapter_detail VARCHAR(400) NOT NULL DEFAULT '',
                  created_at_utc TIMESTAMPTZ NOT NULL,
                  updated_at_utc TIMESTAMPTZ NOT NULL,
                  created_by_user_id UUID,
                  UNIQUE (tenant_id, id)
                )
                """
            )
        )
        await self._session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS thermal_print_auto_intents (
                  tenant_id UUID NOT NULL,
                  intent_key VARCHAR(200) NOT NULL,
                  job_id UUID NOT NULL,
                  created_at_utc TIMESTAMPTZ NOT NULL,
                  PRIMARY KEY (tenant_id, intent_key)
                )
                """
            )
        )

    async def insert_job(
        self,
        *,
        tenant_id: UUID,
        job_kind: str,
        status: str,
        invoice_id: UUID | None,
        invoice_number: str | None,
        beneficiary_patient_id: UUID | None,
        workstation_id: str,
        width_mm: int,
        batch_id: UUID | None,
        parent_job_id: UUID | None,
        attempt: int,
        adapter_mode: str,
        hardware_claim: str,
        snapshot: dict[str, Any],
        rendered_text: str,
        adapter_detail: str,
        user_id: UUID | None,
        now: datetime,
        auto_intent_key: str | None = None,
    ) -> UUID:
        job_id = new_uuid7()
        if auto_intent_key:
            existing = await self._session.execute(
                text(
                    """
                    SELECT job_id FROM thermal_print_auto_intents
                    WHERE tenant_id = :tenant_id AND intent_key = :intent_key
                    """
                ),
                {"tenant_id": tenant_id, "intent_key": auto_intent_key},
            )
            row = existing.mappings().one_or_none()
            if row is not None:
                raise ValueError("auto_print_duplicate")

        await self._session.execute(
            text(
                """
                INSERT INTO thermal_print_jobs (
                  id, tenant_id, job_kind, status, invoice_id, invoice_number,
                  beneficiary_patient_id, workstation_id, width_mm, batch_id,
                  parent_job_id, attempt, adapter_mode, hardware_claim,
                  snapshot_json, rendered_text, adapter_detail,
                  created_at_utc, updated_at_utc, created_by_user_id
                ) VALUES (
                  :id, :tenant_id, :job_kind, :status, :invoice_id, :invoice_number,
                  :beneficiary_patient_id, :workstation_id, :width_mm, :batch_id,
                  :parent_job_id, :attempt, :adapter_mode, :hardware_claim,
                  CAST(:snapshot_json AS jsonb), :rendered_text, :adapter_detail,
                  :now, :now, :user_id
                )
                """
            ),
            {
                "id": job_id,
                "tenant_id": tenant_id,
                "job_kind": job_kind,
                "status": status,
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "beneficiary_patient_id": beneficiary_patient_id,
                "workstation_id": workstation_id,
                "width_mm": width_mm,
                "batch_id": batch_id,
                "parent_job_id": parent_job_id,
                "attempt": attempt,
                "adapter_mode": adapter_mode,
                "hardware_claim": hardware_claim,
                "snapshot_json": json.dumps(snapshot, ensure_ascii=False),
                "rendered_text": rendered_text,
                "adapter_detail": adapter_detail[:400],
                "now": now,
                "user_id": user_id,
            },
        )
        if auto_intent_key and status == "SPOOLED":
            await self._session.execute(
                text(
                    """
                    INSERT INTO thermal_print_auto_intents (
                      tenant_id, intent_key, job_id, created_at_utc
                    ) VALUES (:tenant_id, :intent_key, :job_id, :now)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "intent_key": auto_intent_key,
                    "job_id": job_id,
                    "now": now,
                },
            )
        return job_id

    async def get_job(self, *, tenant_id: UUID, job_id: UUID) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                """
                SELECT * FROM thermal_print_jobs
                WHERE tenant_id = :tenant_id AND id = :job_id
                """
            ),
            {"tenant_id": tenant_id, "job_id": job_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list_for_invoice(
        self, *, tenant_id: UUID, invoice_id: UUID
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, job_kind, status, invoice_number, workstation_id, width_mm,
                       batch_id, parent_job_id, attempt, adapter_mode, hardware_claim,
                       adapter_detail, created_at_utc, updated_at_utc
                FROM thermal_print_jobs
                WHERE tenant_id = :tenant_id AND invoice_id = :invoice_id
                ORDER BY created_at_utc
                """
            ),
            {"tenant_id": tenant_id, "invoice_id": invoice_id},
        )
        return [dict(r) for r in result.mappings().all()]
