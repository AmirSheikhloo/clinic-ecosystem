-- Logical package TP-OPS-LEDGER (official revision ID TBD after PO approval)
-- Apply AFTER tp0007. All statements under db_migrator ownership.

CREATE TABLE invoice_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_number VARCHAR(32) NULL,
  status VARCHAR(16) NOT NULL,
  -- DRAFT | POSTED | VOIDED
  beneficiary_patient_id UUID NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR',
  issued_at_utc TIMESTAMPTZ NULL,
  posted_at_utc TIMESTAMPTZ NULL,
  voided_at_utc TIMESTAMPTZ NULL,
  reception_group_key VARCHAR(64) NULL,
  notes_internal VARCHAR(500) NULL,
  aggregate_version INT NOT NULL DEFAULT 1,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT invoice_documents_status_chk CHECK (status IN ('DRAFT','POSTED','VOIDED')),
  CONSTRAINT invoice_documents_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT invoice_documents_patient_fk
    FOREIGN KEY (tenant_id, beneficiary_patient_id)
    REFERENCES patient_profiles (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_documents_number_uq UNIQUE (tenant_id, invoice_number)
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  line_no INT NOT NULL,
  appointment_id UUID NULL,
  service_id UUID NULL,
  inventory_item_id UUID NULL, -- nullable until inventory package; FK added when inventory lands OR deferred
  line_kind VARCHAR(24) NOT NULL, -- SERVICE | ITEM | ADJUSTMENT_PLACEHOLDER
  description_snapshot VARCHAR(200) NOT NULL,
  service_code_snapshot VARCHAR(64) NULL,
  quantity INT NOT NULL,
  unit_price_irr BIGINT NOT NULL,
  gross_service_amount BIGINT NOT NULL,
  discount_amount BIGINT NOT NULL DEFAULT 0,
  subsidy_amount BIGINT NOT NULL DEFAULT 0,
  rounding_reduction_amount BIGINT NOT NULL DEFAULT 0,
  rounding_surcharge_amount BIGINT NOT NULL DEFAULT 0,
  basic_insurance_expected_share BIGINT NOT NULL DEFAULT 0,
  supplementary_insurance_expected_share BIGINT NOT NULL DEFAULT 0,
  patient_payable_amount BIGINT NOT NULL,
  pricing_rule_version VARCHAR(64) NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT invoice_lines_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT invoice_lines_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id)
    REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT invoice_lines_appointment_fk
    FOREIGN KEY (tenant_id, appointment_id)
    REFERENCES appointments (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_lines_service_fk
    FOREIGN KEY (tenant_id, service_id)
    REFERENCES services (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_lines_qty_chk CHECK (quantity > 0),
  CONSTRAINT invoice_lines_money_nonneg_chk CHECK (
    unit_price_irr >= 0 AND gross_service_amount >= 0 AND discount_amount >= 0
    AND subsidy_amount >= 0 AND rounding_reduction_amount >= 0
    AND rounding_surcharge_amount >= 0 AND basic_insurance_expected_share >= 0
    AND supplementary_insurance_expected_share >= 0 AND patient_payable_amount >= 0
  ),
  CONSTRAINT invoice_lines_identity_chk CHECK (
    gross_service_amount - discount_amount - subsidy_amount - rounding_reduction_amount
      + rounding_surcharge_amount
    = basic_insurance_expected_share + supplementary_insurance_expected_share + patient_payable_amount
  ),
  CONSTRAINT invoice_lines_unique_line UNIQUE (tenant_id, invoice_id, line_no)
);

CREATE TABLE payment_receipts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_number VARCHAR(32) NULL,
  amount_irr BIGINT NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR',
  payment_method VARCHAR(24) NOT NULL, -- CASH | POS | BANK_TRANSFER | ONLINE | OTHER
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NOT NULL,
  payer_patient_id UUID NULL,
  shift_id UUID NULL,
  provider_reference VARCHAR(128) NULL,
  reconciliation_state VARCHAR(24) NOT NULL DEFAULT 'VERIFIED',
  -- VERIFIED | PENDING_RECONCILIATION (ONLINE only until Gate B)
  aggregate_version INT NOT NULL DEFAULT 1,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT payment_receipts_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT payment_receipts_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT payment_receipts_method_chk CHECK (payment_method IN ('CASH','POS','BANK_TRANSFER','ONLINE','OTHER')),
  CONSTRAINT payment_receipts_number_uq UNIQUE (tenant_id, receipt_number),
  CONSTRAINT payment_receipts_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id)
    REFERENCES user_accounts (tenant_id, id) MATCH FULL,
  CONSTRAINT payment_receipts_patient_fk
    FOREIGN KEY (tenant_id, payer_patient_id)
    REFERENCES patient_profiles (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE receipt_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  amount_irr BIGINT NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT receipt_allocations_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT receipt_allocations_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT receipt_allocations_receipt_fk
    FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH FULL,
  CONSTRAINT receipt_allocations_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT receipt_allocations_line_fk
    FOREIGN KEY (tenant_id, invoice_line_id) REFERENCES invoice_lines (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE patient_credits (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  source_receipt_id UUID NULL,
  remaining_irr BIGINT NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT patient_credits_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT patient_credits_remaining_chk CHECK (remaining_irr >= 0),
  CONSTRAINT patient_credits_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT patient_credits_receipt_fk
    FOREIGN KEY (tenant_id, source_receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE financial_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  adjustment_kind VARCHAR(32) NOT NULL,
  -- POST_PAYMENT_DISCOUNT | CORRECTION | WRITE_OFF | OTHER
  amount_irr BIGINT NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT financial_adjustments_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT financial_adjustments_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT financial_adjustments_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT financial_adjustments_line_fk
    FOREIGN KEY (tenant_id, invoice_line_id) REFERENCES invoice_lines (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT financial_adjustments_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

CREATE TABLE clinic_payment_refunds (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  refund_number VARCHAR(32) NULL,
  original_receipt_id UUID NOT NULL,
  amount_irr BIGINT NOT NULL,
  refund_method VARCHAR(24) NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  reconciliation_state VARCHAR(24) NOT NULL DEFAULT 'VERIFIED',
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT clinic_payment_refunds_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT clinic_payment_refunds_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT clinic_payment_refunds_number_uq UNIQUE (tenant_id, refund_number),
  CONSTRAINT clinic_payment_refunds_receipt_fk
    FOREIGN KEY (tenant_id, original_receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH FULL,
  CONSTRAINT clinic_payment_refunds_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

CREATE TABLE document_number_counters (
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  document_type VARCHAR(32) NOT NULL, -- INVOICE | RECEIPT | REFUND
  next_value BIGINT NOT NULL,
  PRIMARY KEY (tenant_id, document_type),
  CONSTRAINT document_number_counters_next_chk CHECK (next_value >= 1)
);

CREATE INDEX invoice_documents_tenant_patient_idx ON invoice_documents (tenant_id, beneficiary_patient_id, posted_at_utc DESC);
CREATE INDEX invoice_lines_tenant_appointment_idx ON invoice_lines (tenant_id, appointment_id);
CREATE INDEX payment_receipts_tenant_occurred_idx ON payment_receipts (tenant_id, occurred_at_utc DESC);
CREATE INDEX receipt_allocations_tenant_invoice_idx ON receipt_allocations (tenant_id, invoice_id);
CREATE INDEX clinic_payment_refunds_tenant_receipt_idx ON clinic_payment_refunds (tenant_id, original_receipt_id);
