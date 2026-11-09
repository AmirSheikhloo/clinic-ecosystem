-- Per-database Tenant Plane schema/object privilege bootstrap (Appendix E.1.4–E.1.5).
-- Run while connected to the Tenant Plane logical database (tenant_app or local_hub).
-- NO SECRETS.

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO db_migrator;
GRANT USAGE ON SCHEMA public TO db_app_runtime;

-- Future objects owned by db_migrator receive least-privilege DML for runtime only.
-- Explicitly omit TRUNCATE, DDL, and grants to PUBLIC / other planes.
ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE db_migrator IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
