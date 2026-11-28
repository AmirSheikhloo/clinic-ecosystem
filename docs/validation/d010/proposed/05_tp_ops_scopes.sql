CREATE TABLE role_permission_scopes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  role_id UUID NOT NULL,
  permission_code VARCHAR(64) NOT NULL,
  scope_kind VARCHAR(32) NOT NULL, -- DEPARTMENT | SERVICE | PROVIDER_RESOURCE | ALL
  scope_ref UUID NULL, -- NULL only when scope_kind='ALL'
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT role_permission_scopes_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT role_permission_scopes_role_fk
    FOREIGN KEY (tenant_id, role_id) REFERENCES tenant_roles (tenant_id, id) MATCH FULL,
  CONSTRAINT role_permission_scopes_kind_chk CHECK (scope_kind IN ('DEPARTMENT','SERVICE','PROVIDER_RESOURCE','ALL')),
  CONSTRAINT role_permission_scopes_ref_chk CHECK (
    (scope_kind = 'ALL' AND scope_ref IS NULL) OR (scope_kind <> 'ALL' AND scope_ref IS NOT NULL)
  )
);
CREATE INDEX role_permission_scopes_lookup_idx
  ON role_permission_scopes (tenant_id, role_id, permission_code);
