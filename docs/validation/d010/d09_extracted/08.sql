ALTER TABLE appointments ADD CONSTRAINT appointments_patient_service_uq
  UNIQUE (tenant_id, id, beneficiary_patient_id, service_id);
ALTER TABLE appointments ADD CONSTRAINT appointments_patient_uq
  UNIQUE (tenant_id, id, beneficiary_patient_id);

CREATE TABLE reception_groups (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  created_by_user_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE reception_group_appointments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  group_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  line_key VARCHAR(128) NOT NULL,
  line_no INT NOT NULL CHECK (line_no > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  UNIQUE (tenant_id, group_id, line_key),
  UNIQUE (tenant_id, group_id, line_no),
  FOREIGN KEY (tenant_id, group_id, patient_id) REFERENCES reception_groups(tenant_id, id, patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id) MATCH FULL
);

CREATE TABLE clinic_visits (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  admission_at_utc TIMESTAMPTZ NOT NULL,
  arrived_at_utc TIMESTAMPTZ NULL,
  departed_at_utc TIMESTAMPTZ NULL,
  registered_by_user_id UUID NOT NULL,
  departed_by_user_id UUID NULL,
  historical_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, registered_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, departed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (departed_at_utc IS NULL AND departed_by_user_id IS NULL)
    OR (departed_at_utc IS NOT NULL AND arrived_at_utc IS NOT NULL AND departed_at_utc >= arrived_at_utc AND departed_by_user_id IS NOT NULL)
  )
);

CREATE TABLE visit_appointments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  visit_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  UNIQUE (tenant_id, visit_id, appointment_id),
  FOREIGN KEY (tenant_id, visit_id, patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id) MATCH FULL
);

CREATE TABLE appointment_arrival_facts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  visit_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  checked_in_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  FOREIGN KEY (tenant_id, visit_id, appointment_id) REFERENCES visit_appointments(tenant_id, visit_id, appointment_id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE service_records (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  appointment_id UUID NULL,
  visit_id UUID NULL,
  department_id UUID NULL,
  record_kind VARCHAR(24) NOT NULL CHECK (record_kind IN ('PERFORMED', 'OPERATIONAL_RECORD')),
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  reason_code VARCHAR(64) NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id, service_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id, service_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, visit_id, patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (record_kind = 'PERFORMED' OR reason_code IS NOT NULL)
);

CREATE UNIQUE INDEX performed_record_per_appointment_uq ON service_records(tenant_id, appointment_id)
  WHERE appointment_id IS NOT NULL AND record_kind = 'PERFORMED';

CREATE TABLE service_record_practitioners (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_record_id UUID NOT NULL,
  practitioner_mapping_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, service_record_id, practitioner_mapping_id),
  FOREIGN KEY (tenant_id, service_record_id) REFERENCES service_records(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL
);

CREATE TABLE historical_appointment_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  appointment_id UUID NOT NULL,
  late_entry_reason VARCHAR(200) NOT NULL CHECK (length(btrim(late_entry_reason)) > 0),
  reported_occurrence_at_utc TIMESTAMPTZ NULL,
  suppress_past_reminders BOOLEAN NOT NULL DEFAULT TRUE CHECK (suppress_past_reminders),
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  FOREIGN KEY (tenant_id, appointment_id) REFERENCES appointments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE INDEX clinic_visits_patient_time_idx ON clinic_visits(tenant_id, patient_id, admission_at_utc DESC, id);
CREATE INDEX clinic_visits_present_idx ON clinic_visits(tenant_id, arrived_at_utc, id) WHERE departed_at_utc IS NULL;
CREATE INDEX service_records_patient_time_idx ON service_records(tenant_id, patient_id, occurred_at_utc DESC, id);
