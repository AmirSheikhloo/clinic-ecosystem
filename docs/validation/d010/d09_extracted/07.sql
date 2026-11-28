CREATE TABLE role_permission_scopes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  role_permission_assignment_id UUID NOT NULL,
  scope_mode VARCHAR(16) NOT NULL CHECK (scope_mode IN ('ALL', 'FILTER')),
  department_id UUID NULL,
  service_id UUID NULL,
  provider_resource_id UUID NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE NULLS NOT DISTINCT (tenant_id, role_permission_assignment_id, scope_mode, department_id, service_id, provider_resource_id),
  FOREIGN KEY (tenant_id, role_permission_assignment_id) REFERENCES role_permission_assignments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, provider_resource_id) REFERENCES bookable_resources(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, provider_resource_id) REFERENCES staff_practitioner_resources(tenant_id, bookable_resource_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (
    (scope_mode = 'ALL' AND department_id IS NULL AND service_id IS NULL AND provider_resource_id IS NULL)
    OR (scope_mode = 'FILTER' AND (department_id IS NOT NULL OR service_id IS NOT NULL OR provider_resource_id IS NOT NULL))
  )
);

CREATE INDEX role_permission_scopes_grant_idx ON role_permission_scopes(tenant_id, role_permission_assignment_id);
