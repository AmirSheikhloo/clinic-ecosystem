-- PROPOSED disposable ops tables for treatment courses / rolling recall (Task 34 R2).
-- Not an official Alembic revision. Apply only under CLINIC_OPS_SCHEMA_MODE=disposable.

CREATE TABLE IF NOT EXISTS treatment_course_templates (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  template_name VARCHAR(120) NOT NULL,
  planned_sessions INT NOT NULL CHECK (planned_sessions > 0 AND planned_sessions <= 100),
  interval_kind VARCHAR(24) NOT NULL CHECK (interval_kind IN ('CALENDAR_MONTH','FIXED_DAYS')),
  interval_value INT NOT NULL CHECK (interval_value > 0 AND interval_value <= 366),
  reminder_lead_days INT NOT NULL DEFAULT 2 CHECK (reminder_lead_days >= 0 AND reminder_lead_days <= 30),
  billing_mode VARCHAR(24) NOT NULL DEFAULT 'PAY_PER_SESSION'
    CHECK (billing_mode IN ('PAY_PER_SESSION','PREPAID_DISABLED')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS treatment_courses (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  template_id UUID,
  planned_sessions INT NOT NULL CHECK (planned_sessions > 0),
  completed_sessions INT NOT NULL DEFAULT 0 CHECK (completed_sessions >= 0),
  status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('ACTIVE','PAUSED','REASSESSMENT_REQUIRED','COMPLETED','ENDED')),
  interval_kind VARCHAR(24) NOT NULL,
  interval_value INT NOT NULL,
  next_suggested_date_tehran DATE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS treatment_recall_schedules (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  course_id UUID NOT NULL,
  cycle_no INT NOT NULL,
  suggested_date_tehran DATE NOT NULL,
  reminder_kind VARCHAR(24) NOT NULL,
  scheduled_at_utc TIMESTAMPTZ NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'SCHEDULED'
    CHECK (status IN ('SCHEDULED','SUPPRESSED','ATTEMPTED','ACCEPTED','FAILED')),
  logical_key VARCHAR(200) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, logical_key)
);
