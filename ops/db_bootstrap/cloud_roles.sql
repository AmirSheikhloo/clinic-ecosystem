-- Cloud shared-cluster role and privilege structure (v3.0.1 Appendix E.1 / D.2 / clause 744).
-- NO PASSWORDS OR SECRETS. Tests set ephemeral passwords at runtime via ALTER ROLE.

-- Tenant Plane group roles
DO $$ BEGIN
  CREATE ROLE db_migrator NOLOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE db_app_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Control Plane group roles (distinct names; roles are cluster-wide)
DO $$ BEGIN
  CREATE ROLE cp_db_migrator NOLOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE cp_db_app_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Recommended login principals (password set by test harness only)
DO $$ BEGIN
  CREATE ROLE tp_migrator_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE tp_app_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE cp_migrator_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE cp_app_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Membership: runtime inherits only its plane runtime role; never migrator or other plane
GRANT db_app_runtime TO tp_app_login;
GRANT db_migrator TO tp_migrator_login;
GRANT cp_db_app_runtime TO cp_app_login;
GRANT cp_db_migrator TO cp_migrator_login;

-- Migration jobs assume only their plane migrator group role (E.1.4).
ALTER ROLE tp_migrator_login SET ROLE db_migrator;
ALTER ROLE cp_migrator_login SET ROLE cp_db_migrator;

-- Per-database CONNECT / TEMPORARY (run after both logical DBs exist)
-- Database names expected by tests: control_plane, tenant_app

REVOKE CONNECT, TEMPORARY ON DATABASE control_plane FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE tenant_app FROM PUBLIC;

GRANT CONNECT ON DATABASE control_plane TO cp_migrator_login, cp_app_login;
GRANT CONNECT ON DATABASE tenant_app TO tp_migrator_login, tp_app_login;

-- Explicitly no cross-plane CONNECT
REVOKE CONNECT ON DATABASE control_plane FROM tp_migrator_login, tp_app_login;
REVOKE CONNECT ON DATABASE tenant_app FROM cp_migrator_login, cp_app_login;

-- Minimum DB CREATE for trusted extensions (btree_gist) without SUPERUSER (E.1.8).
GRANT CREATE ON DATABASE tenant_app TO db_migrator;
GRANT CREATE ON DATABASE control_plane TO cp_db_migrator;
