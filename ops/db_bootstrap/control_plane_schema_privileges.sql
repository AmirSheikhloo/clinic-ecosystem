-- Per-database Control Plane schema/object privilege bootstrap (Appendix E.1.4–E.1.5).
-- Run while connected to the Control Plane logical database (control_plane).
-- NO SECRETS.

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO cp_db_migrator;
GRANT USAGE ON SCHEMA public TO cp_db_app_runtime;

-- Private Alembic metadata schema (version tables created by Alembic lifecycle).
DO $$ BEGIN
  CREATE SCHEMA alembic_meta AUTHORIZATION cp_db_migrator;
EXCEPTION WHEN duplicate_schema THEN
  ALTER SCHEMA alembic_meta OWNER TO cp_db_migrator;
END $$;

REVOKE ALL ON SCHEMA alembic_meta FROM PUBLIC;
REVOKE ALL ON SCHEMA alembic_meta FROM cp_db_app_runtime;
DO $$ BEGIN
  REVOKE ALL ON SCHEMA alembic_meta FROM cp_app_login;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

-- Clear global defaults that would expose alembic_meta; preserve public DML below.
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator
  REVOKE ALL ON TABLES FROM cp_db_app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator
  REVOKE ALL ON SEQUENCES FROM cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON TABLES FROM cp_db_app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA alembic_meta
  REVOKE ALL ON SEQUENCES FROM cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
