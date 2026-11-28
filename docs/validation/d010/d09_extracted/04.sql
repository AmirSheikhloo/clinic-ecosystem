CREATE TABLE appointment_waitlist_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  department_id UUID NULL,
  preferred_resource_id UUID NULL,
  preferred_start_utc TIMESTAMPTZ NULL,
  preferred_end_utc TIMESTAMPTZ NULL,
  priority INT NOT NULL DEFAULT 100 CHECK (priority BETWEEN 1 AND 1000),
  status VARCHAR(24) NOT NULL CHECK (status IN ('OPEN', 'CONTACTED', 'CONVERTED', 'CANCELLED', 'EXPIRED')),
  contact_state VARCHAR(24) NOT NULL CHECK (contact_state IN ('NONE', 'PENDING', 'CONTACTED', 'UNREACHABLE', 'DECLINED')),
  converted_appointment_id UUID NULL,
  notes VARCHAR(500) NULL,
  created_by_user_id UUID NOT NULL,
  updated_by_user_id UUID NOT NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, converted_appointment_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, preferred_resource_id) REFERENCES staff_practitioner_resources(tenant_id, bookable_resource_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, converted_appointment_id, patient_id, service_id)
    REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, updated_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (preferred_start_utc IS NULL OR preferred_end_utc IS NULL OR preferred_start_utc < preferred_end_utc),
  CHECK ((status = 'CONVERTED') = (converted_appointment_id IS NOT NULL))
);

CREATE INDEX waitlist_open_idx ON appointment_waitlist_entries(tenant_id, service_id, priority, created_at_utc, id)
  WHERE status IN ('OPEN', 'CONTACTED');
