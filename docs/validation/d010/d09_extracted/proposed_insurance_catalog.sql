-- PROPOSED disposable insurance catalog (Task 34 §13 / PAT-02). Not official Alembic.

CREATE TABLE IF NOT EXISTS insurance_catalog_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  insurer_code VARCHAR(64) NOT NULL,
  insurer_name_fa VARCHAR(160) NOT NULL,
  coverage_kind VARCHAR(24) NOT NULL
    CHECK (coverage_kind IN ('BASIC','SUPPLEMENTARY','NONE','UNKNOWN')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  clinic_contract_active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, insurer_code)
);
