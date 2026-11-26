-- D010: departments catalog required before DEPARTMENT scope_kind is usable
CREATE TABLE departments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_code VARCHAR(64) NOT NULL,
  department_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT departments_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT departments_code_uq UNIQUE (tenant_id, department_code)
);

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


-- Fail-closed: DEPARTMENT scopes must reference existing departments
CREATE OR REPLACE FUNCTION role_permission_scopes_ref_integrity()
RETURNS trigger AS $$
BEGIN
  IF NEW.scope_kind = 'DEPARTMENT' THEN
    IF NOT EXISTS (
      SELECT 1 FROM departments d
      WHERE d.tenant_id = NEW.tenant_id AND d.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'DEPARTMENT scope_ref must reference departments.id';
    END IF;
  ELSIF NEW.scope_kind = 'SERVICE' THEN
    IF NOT EXISTS (
      SELECT 1 FROM services s
      WHERE s.tenant_id = NEW.tenant_id AND s.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'SERVICE scope_ref must reference services.id';
    END IF;
  ELSIF NEW.scope_kind = 'PROVIDER_RESOURCE' THEN
    IF NOT EXISTS (
      SELECT 1 FROM bookable_resources r
      WHERE r.tenant_id = NEW.tenant_id AND r.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'PROVIDER_RESOURCE scope_ref must reference bookable_resources.id';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER role_permission_scopes_ref_trg
  BEFORE INSERT OR UPDATE ON role_permission_scopes
  FOR EACH ROW EXECUTE FUNCTION role_permission_scopes_ref_integrity();
