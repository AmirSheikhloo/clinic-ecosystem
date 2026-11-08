-- Local Hub PostgreSQL instance role structure (v3.0.1 Appendix E.1 / D.2).
-- Independent cluster: Tenant Plane group-role names may be reused.
-- NO PASSWORDS OR SECRETS. Tests set ephemeral passwords at runtime via ALTER ROLE.

DO $$ BEGIN
  CREATE ROLE db_migrator NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE db_app_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE local_migrator_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE ROLE local_app_login LOGIN NOSUPERUSER NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT db_app_runtime TO local_app_login;
GRANT db_migrator TO local_migrator_login;

-- Database name expected by tests: local_hub
REVOKE CONNECT, TEMPORARY ON DATABASE local_hub FROM PUBLIC;
GRANT CONNECT ON DATABASE local_hub TO local_migrator_login, local_app_login;
