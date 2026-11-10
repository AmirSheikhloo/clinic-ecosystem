-- Per-database Tenant Plane schema/object privilege bootstrap (Appendix E.1.4–E.1.5).
-- Run while connected to the Tenant Plane logical database (tenant_app or local_hub).
-- NO SECRETS.

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO db_migrator;
GRANT USAGE ON SCHEMA public TO db_app_runtime;

-- Private Alembic metadata schema (version tables created by Alembic lifecycle).
DO $$ BEGIN
  CREATE SCHEMA alembic_meta AUTHORIZATION db_migrator;
EXCEPTION WHEN duplicate_schema THEN
  ALTER SCHEMA alembic_meta OWNER TO db_migrator;
END $$;

REVOKE ALL ON SCHEMA alembic_meta FROM PUBLIC;
REVOKE ALL ON SCHEMA alembic_meta FROM db_app_runtime;
DO $$ BEGIN
  REVOKE ALL ON SCHEMA alembic_meta FROM tp_app_login;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;
DO $$ BEGIN
  REVOKE ALL ON SCHEMA alembic_meta FROM local_app_login;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

-- Clear any global default grants that would expose objects outside public
-- (including alembic_meta). Schema-specific public DML defaults are re-applied below.
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator
  REVOKE ALL ON TABLES FROM db_app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator
  REVOKE ALL ON SEQUENCES FROM db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON TABLES FROM db_app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON SEQUENCES FROM db_app_runtime;

-- Future application objects in public: least-privilege DML for runtime only.
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
