-- PROPOSED disposable ops tables for thermal print jobs (Task 34 R2 §22 / correction §10).
-- Not an official Alembic revision. Apply only under CLINIC_OPS_SCHEMA_MODE=disposable.
-- Print jobs are independent of checkout idempotency. Reprint never mutates finance.

CREATE TABLE IF NOT EXISTS thermal_print_jobs (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  job_kind VARCHAR(24) NOT NULL
    CHECK (job_kind IN ('RECEIPT', 'TEST', 'BATCH_ITEM', 'REPRINT')),
  status VARCHAR(24) NOT NULL
    CHECK (status IN ('QUEUED', 'SPOOLED', 'FAILED', 'UNKNOWN', 'CANCELLED')),
  invoice_id UUID,
  invoice_number VARCHAR(64),
  beneficiary_patient_id UUID,
  workstation_id VARCHAR(64) NOT NULL,
  width_mm SMALLINT NOT NULL CHECK (width_mm IN (58, 80)),
  batch_id UUID,
  parent_job_id UUID,
  attempt INT NOT NULL DEFAULT 1 CHECK (attempt >= 1 AND attempt <= 20),
  adapter_mode VARCHAR(32) NOT NULL DEFAULT 'simulated'
    CHECK (adapter_mode IN ('simulated', 'browser_fallback', 'qz_blocked')),
  hardware_claim VARCHAR(40) NOT NULL DEFAULT 'none'
    CHECK (hardware_claim IN ('none', 'browser_dialog', 'blocked_pending_approval')),
  -- Immutable print snapshot JSON (authorized fields only; no national ID / secrets).
  snapshot_json JSONB NOT NULL,
  rendered_text TEXT NOT NULL,
  adapter_detail VARCHAR(400) NOT NULL DEFAULT '',
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  created_by_user_id UUID,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id, beneficiary_patient_id)
    REFERENCES invoice_documents(tenant_id, id, beneficiary_patient_id) MATCH SIMPLE
);

CREATE INDEX IF NOT EXISTS thermal_print_jobs_invoice_idx
  ON thermal_print_jobs (tenant_id, invoice_id, created_at_utc DESC);

CREATE INDEX IF NOT EXISTS thermal_print_jobs_batch_idx
  ON thermal_print_jobs (tenant_id, batch_id)
  WHERE batch_id IS NOT NULL;

-- Auto-print dedupe: one successful auto intent per invoice+workstation+day key.
CREATE TABLE IF NOT EXISTS thermal_print_auto_intents (
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  intent_key VARCHAR(200) NOT NULL,
  job_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (tenant_id, intent_key),
  FOREIGN KEY (tenant_id, job_id) REFERENCES thermal_print_jobs(tenant_id, id) MATCH FULL
);
