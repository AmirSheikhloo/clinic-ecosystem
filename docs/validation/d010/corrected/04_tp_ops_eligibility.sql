CREATE TABLE staff_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  staff_profile_id UUID NOT NULL,
  service_id UUID NOT NULL,
  bookable_resource_id UUID NOT NULL, -- practitioner resource representing this staff for scheduling
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT staff_service_links_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT staff_service_links_uq UNIQUE (tenant_id, staff_profile_id, service_id, bookable_resource_id),
  CONSTRAINT staff_service_links_staff_fk
    FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT staff_service_links_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH FULL,
  CONSTRAINT staff_service_links_resource_fk
    FOREIGN KEY (tenant_id, bookable_resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH FULL
);
