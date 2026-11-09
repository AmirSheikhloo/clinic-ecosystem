-- Per-database Control Plane schema/object privilege bootstrap (Appendix E.1.4–E.1.5).
-- Run while connected to the Control Plane logical database (control_plane).
-- NO SECRETS.

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO cp_db_migrator;
GRANT USAGE ON SCHEMA public TO cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO cp_db_app_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE cp_db_migrator IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC;
