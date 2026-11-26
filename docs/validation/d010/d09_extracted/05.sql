CREATE TABLE staff_practitioner_resources (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  staff_profile_id UUID NOT NULL,
  bookable_resource_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, staff_profile_id),
  UNIQUE (tenant_id, bookable_resource_id),
  FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, bookable_resource_id) REFERENCES bookable_resources(tenant_id, id) MATCH FULL
);

CREATE TABLE staff_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  practitioner_mapping_id UUID NOT NULL,
  service_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, practitioner_mapping_id, service_id),
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE INDEX staff_service_eligible_idx ON staff_service_links(tenant_id, service_id, practitioner_mapping_id)
  WHERE is_active;
