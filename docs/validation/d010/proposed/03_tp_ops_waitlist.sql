CREATE TABLE appointment_waitlist_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  preferred_resource_id UUID NULL,
  preferred_start_utc TIMESTAMPTZ NULL,
  preferred_end_utc TIMESTAMPTZ NULL,
  priority INT NOT NULL DEFAULT 100,
  status VARCHAR(24) NOT NULL DEFAULT 'OPEN',
  -- OPEN | CONTACTED | CONVERTED | CANCELLED | EXPIRED
  contact_state VARCHAR(24) NOT NULL DEFAULT 'NONE',
  converted_appointment_id UUID NULL,
  notes VARCHAR(500) NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT appointment_waitlist_entries_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT appointment_waitlist_entries_status_chk CHECK (status IN ('OPEN','CONTACTED','CONVERTED','CANCELLED','EXPIRED')),
  CONSTRAINT appointment_waitlist_entries_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT appointment_waitlist_entries_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH FULL,
  CONSTRAINT appointment_waitlist_entries_resource_fk
    FOREIGN KEY (tenant_id, preferred_resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT appointment_waitlist_entries_converted_fk
    FOREIGN KEY (tenant_id, converted_appointment_id) REFERENCES appointments (tenant_id, id) MATCH SIMPLE
);
