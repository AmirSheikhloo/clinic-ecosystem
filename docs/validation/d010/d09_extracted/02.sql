CREATE TABLE clinic_insurers (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  insurer_code VARCHAR(64) NOT NULL,
  insurer_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, insurer_code)
);

CREATE TABLE invoice_insurer_expectations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  insurer_id UUID NOT NULL,
  coverage_kind VARCHAR(24) NOT NULL CHECK (coverage_kind IN ('BASIC', 'SUPPLEMENTARY')),
  expected_amount_irr BIGINT NOT NULL CHECK (expected_amount_irr > 0),
  policy_version VARCHAR(64) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_line_id, coverage_kind),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, insurer_id) REFERENCES clinic_insurers(tenant_id, id) MATCH FULL
);

CREATE TABLE insurer_settlement_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  expectation_id UUID NOT NULL,
  entry_kind VARCHAR(16) NOT NULL CHECK (entry_kind IN ('REMITTANCE', 'REVERSAL')),
  reverses_entry_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  verified_reference VARCHAR(128) NOT NULL,
  evidence_reference VARCHAR(256) NOT NULL,
  operator_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type IN ('STAFF_USER', 'SYSTEM_CALLBACK')),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, expectation_id, id),
  UNIQUE (tenant_id, expectation_id, verified_reference, entry_kind),
  FOREIGN KEY (tenant_id, expectation_id) REFERENCES invoice_insurer_expectations(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, expectation_id, reverses_entry_id) REFERENCES insurer_settlement_entries(tenant_id, expectation_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK ((actor_type = 'STAFF_USER' AND operator_user_id IS NOT NULL AND actor_id = operator_user_id)
      OR (actor_type = 'SYSTEM_CALLBACK' AND operator_user_id IS NULL)),
  CHECK ((entry_kind = 'REMITTANCE' AND reverses_entry_id IS NULL)
      OR (entry_kind = 'REVERSAL' AND reverses_entry_id IS NOT NULL AND reverses_entry_id <> id)),
  CHECK (reverses_entry_id IS NULL OR reverses_entry_id <> id)
);

CREATE TABLE clinic_service_referrers (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  person_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, person_id),
  FOREIGN KEY (tenant_id, person_id) REFERENCES tenant_persons(tenant_id, id) MATCH FULL
);

CREATE TABLE revenue_share_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  beneficiary_kind VARCHAR(16) NOT NULL CHECK (beneficiary_kind IN ('CLINIC', 'DOCTOR', 'SPECIALIST', 'REFERRER')),
  staff_profile_id UUID NULL,
  referrer_id UUID NULL,
  basis_irr BIGINT NOT NULL CHECK (basis_irr >= 0),
  rule_kind VARCHAR(16) NOT NULL CHECK (rule_kind IN ('FIXED_IRR', 'PERCENT_BPS')),
  rule_value BIGINT NOT NULL CHECK (rule_value >= 0),
  amount_irr BIGINT NOT NULL CHECK (amount_irr >= 0),
  policy_version VARCHAR(64) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, referrer_id) REFERENCES clinic_service_referrers(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (beneficiary_kind = 'CLINIC' AND staff_profile_id IS NULL AND referrer_id IS NULL)
    OR (beneficiary_kind IN ('DOCTOR', 'SPECIALIST') AND staff_profile_id IS NOT NULL AND referrer_id IS NULL)
    OR (beneficiary_kind = 'REFERRER' AND referrer_id IS NOT NULL AND staff_profile_id IS NULL)
  ),
  CHECK (rule_kind <> 'PERCENT_BPS' OR rule_value <= 10000)
);

CREATE TABLE revenue_share_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  original_share_id UUID NOT NULL,
  financial_adjustment_id UUID NULL,
  refund_id UUID NULL,
  delta_irr BIGINT NOT NULL CHECK (delta_irr <> 0),
  reason_code VARCHAR(64) NOT NULL,
  operator_user_id UUID NOT NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, original_share_id) REFERENCES revenue_share_allocations(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, financial_adjustment_id) REFERENCES financial_adjustments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, refund_id) REFERENCES clinic_payment_refunds(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK ((financial_adjustment_id IS NULL) <> (refund_id IS NULL))
);
