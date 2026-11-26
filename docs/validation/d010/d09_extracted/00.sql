CREATE TABLE billable_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(200) NOT NULL,
  unit_code VARCHAR(16) NOT NULL,
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  default_price_irr BIGINT NOT NULL CHECK (default_price_irr >= 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_code),
  UNIQUE (tenant_id, id, quantity_scale)
);

CREATE TABLE cashier_shifts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NULL,
  shift_label VARCHAR(100) NOT NULL,
  opened_by_user_id UUID NOT NULL,
  opened_at_utc TIMESTAMPTZ NOT NULL,
  opening_cash_irr BIGINT NOT NULL CHECK (opening_cash_irr >= 0),
  closed_by_user_id UUID NULL,
  closed_at_utc TIMESTAMPTZ NULL,
  expected_cash_irr BIGINT NULL,
  counted_cash_irr BIGINT NULL CHECK (counted_cash_irr >= 0),
  variance_irr BIGINT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, opened_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, closed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (closed_at_utc IS NULL AND closed_by_user_id IS NULL AND expected_cash_irr IS NULL AND counted_cash_irr IS NULL AND variance_irr IS NULL)
    OR (closed_at_utc IS NOT NULL AND closed_at_utc >= opened_at_utc AND closed_by_user_id IS NOT NULL
        AND expected_cash_irr IS NOT NULL AND counted_cash_irr IS NOT NULL AND variance_irr = counted_cash_irr - expected_cash_irr)
  )
);

CREATE TABLE clinic_payment_instruments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  instrument_kind VARCHAR(24) NOT NULL CHECK (instrument_kind IN ('POS_TERMINAL', 'BANK_DESTINATION', 'CASH_REGISTER', 'GATEWAY_MERCHANT')),
  instrument_label VARCHAR(100) NOT NULL,
  external_reference VARCHAR(128) NOT NULL,
  department_id UUID NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, instrument_kind, external_reference),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE
);
-- external_reference is a managed opaque terminal/merchant identifier, never a PAN or secret.
-- Gateway secrets remain in the approved encrypted tenant key hierarchy, never in this table.

CREATE TABLE invoice_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_number VARCHAR(32) NULL,
  status VARCHAR(16) NOT NULL CHECK (status IN ('DRAFT', 'POSTED', 'VOIDED')),
  beneficiary_patient_id UUID NOT NULL,
  visit_id UUID NULL,
  reception_group_id UUID NULL,
  department_id UUID NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR' CHECK (currency_code = 'IRR'),
  issued_at_utc TIMESTAMPTZ NULL,
  posted_at_utc TIMESTAMPTZ NULL,
  voided_at_utc TIMESTAMPTZ NULL,
  posted_by_user_id UUID NULL,
  voided_by_user_id UUID NULL,
  void_reason VARCHAR(200) NULL,
  notes_internal VARCHAR(500) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_number),
  UNIQUE (tenant_id, id, beneficiary_patient_id),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, visit_id, beneficiary_patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, reception_group_id, beneficiary_patient_id) REFERENCES reception_groups(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, posted_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, voided_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (status = 'DRAFT' AND posted_at_utc IS NULL AND issued_at_utc IS NULL AND invoice_number IS NULL AND posted_by_user_id IS NULL AND voided_at_utc IS NULL AND voided_by_user_id IS NULL AND void_reason IS NULL)
    OR (status = 'POSTED' AND posted_at_utc IS NOT NULL AND issued_at_utc IS NOT NULL AND invoice_number IS NOT NULL AND posted_by_user_id IS NOT NULL AND voided_at_utc IS NULL AND voided_by_user_id IS NULL AND void_reason IS NULL)
    OR (status = 'VOIDED' AND voided_at_utc IS NOT NULL AND voided_by_user_id IS NOT NULL AND NULLIF(btrim(void_reason), '') IS NOT NULL AND posted_at_utc IS NULL AND issued_at_utc IS NULL AND invoice_number IS NULL AND posted_by_user_id IS NULL)
  )
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  beneficiary_patient_id UUID NOT NULL,
  line_no INT NOT NULL CHECK (line_no > 0),
  line_status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (line_status IN ('ACTIVE', 'REMOVED')),
  department_id UUID NULL,
  practitioner_mapping_id UUID NULL,
  appointment_id UUID NULL,
  service_record_id UUID NULL,
  service_id UUID NULL,
  billable_item_id UUID NULL,
  line_kind VARCHAR(16) NOT NULL CHECK (line_kind IN ('SERVICE', 'ITEM')),
  description_snapshot VARCHAR(200) NOT NULL,
  code_snapshot VARCHAR(64) NOT NULL,
  quantity_scaled BIGINT NOT NULL CHECK (quantity_scaled > 0),
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  unit_code_snapshot VARCHAR(16) NOT NULL,
  unit_price_irr BIGINT NOT NULL CHECK (unit_price_irr >= 0),
  gross_service_amount BIGINT NOT NULL CHECK (gross_service_amount >= 0),
  discount_amount BIGINT NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
  subsidy_amount BIGINT NOT NULL DEFAULT 0 CHECK (subsidy_amount >= 0),
  rounding_reduction_amount BIGINT NOT NULL DEFAULT 0 CHECK (rounding_reduction_amount >= 0),
  rounding_surcharge_amount BIGINT NOT NULL DEFAULT 0 CHECK (rounding_surcharge_amount >= 0),
  basic_insurance_expected_share BIGINT NOT NULL DEFAULT 0 CHECK (basic_insurance_expected_share >= 0),
  supplementary_insurance_expected_share BIGINT NOT NULL DEFAULT 0 CHECK (supplementary_insurance_expected_share >= 0),
  patient_payable_amount BIGINT NOT NULL CHECK (patient_payable_amount >= 0),
  pricing_rule_version VARCHAR(64) NOT NULL,
  payer_policy_version VARCHAR(64) NOT NULL,
  revenue_policy_version VARCHAR(64) NOT NULL,
  charge_without_service_reason VARCHAR(200) NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_id, id),
  UNIQUE (tenant_id, invoice_id, line_no),
  FOREIGN KEY (tenant_id, invoice_id, beneficiary_patient_id) REFERENCES invoice_documents(tenant_id, id, beneficiary_patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, beneficiary_patient_id, service_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_record_id, beneficiary_patient_id, service_id) REFERENCES service_records(tenant_id, id, patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, billable_item_id) REFERENCES billable_items(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (line_kind = 'SERVICE' AND service_id IS NOT NULL AND billable_item_id IS NULL
      AND (appointment_id IS NOT NULL OR service_record_id IS NOT NULL OR NULLIF(btrim(charge_without_service_reason), '') IS NOT NULL))
    OR (line_kind = 'ITEM' AND billable_item_id IS NOT NULL AND service_id IS NULL AND service_record_id IS NULL AND appointment_id IS NULL AND charge_without_service_reason IS NULL)
  ),
  CHECK (
    gross_service_amount::numeric - discount_amount - subsidy_amount - rounding_reduction_amount + rounding_surcharge_amount
    = basic_insurance_expected_share::numeric + supplementary_insurance_expected_share + patient_payable_amount
  )
);

CREATE TABLE invoice_item_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  item_line_id UUID NOT NULL,
  service_line_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_line_id),
  FOREIGN KEY (tenant_id, invoice_id, item_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, service_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  CHECK (item_line_id <> service_line_id)
);

CREATE TABLE draft_discount_actions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  discount_scope VARCHAR(16) NOT NULL CHECK (discount_scope IN ('INVOICE', 'LINE')),
  calculation_kind VARCHAR(16) NOT NULL CHECK (calculation_kind IN ('FIXED_IRR', 'PERCENT_BPS')),
  requested_value BIGINT NOT NULL CHECK (requested_value > 0),
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  approver_user_id UUID NULL,
  policy_version VARCHAR(64) NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, approver_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK ((discount_scope = 'INVOICE' AND invoice_line_id IS NULL) OR (discount_scope = 'LINE' AND invoice_line_id IS NOT NULL)),
  CHECK (calculation_kind <> 'PERCENT_BPS' OR requested_value <= 10000)
);

CREATE TABLE document_number_counters (
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  document_type VARCHAR(32) NOT NULL CHECK (document_type IN ('INVOICE', 'RECEIPT', 'REFUND')),
  next_value BIGINT NOT NULL CHECK (next_value > 0),
  PRIMARY KEY (tenant_id, document_type)
);

CREATE TABLE service_record_charge_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_record_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, service_record_id, invoice_line_id),
  FOREIGN KEY (tenant_id, service_record_id) REFERENCES service_records(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE INDEX invoice_patient_date_idx ON invoice_documents(tenant_id, beneficiary_patient_id, posted_at_utc DESC, id);
CREATE INDEX invoice_appointment_idx ON invoice_lines(tenant_id, appointment_id);
