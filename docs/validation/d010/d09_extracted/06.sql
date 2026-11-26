CREATE TABLE departments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_code VARCHAR(64) NOT NULL,
  department_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_code)
);

CREATE TABLE department_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NOT NULL,
  service_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_id, service_id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE TABLE department_practitioner_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NOT NULL,
  practitioner_mapping_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_id, practitioner_mapping_id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL
);

ALTER TABLE appointments ADD COLUMN department_id UUID NULL;
ALTER TABLE appointments ADD CONSTRAINT appointments_department_fk
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE;
