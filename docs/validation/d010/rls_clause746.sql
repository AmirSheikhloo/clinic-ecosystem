-- Clause 746 / Appendix F.6 three-policy pattern for TP-OPS tables.
-- Applied only in disposable validation; not an Alembic revision.
-- Policy names MUST match tp0007: tenant_runtime_base, tenant_runtime_guard, tenant_migrator_maintenance.

DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'invoice_documents',
    'invoice_lines',
    'payment_receipts',
    'receipt_allocations',
    'patient_credits',
    'financial_adjustments',
    'clinic_payment_refunds',
    'document_number_counters',
    'inventory_items',
    'inventory_lots',
    'stock_movements',
    'service_item_suggestions',
    'appointment_waitlist_entries',
    'staff_service_links',
    'role_permission_scopes',
    'online_availability_closures',
    'patient_operational_notes',
    'patient_staff_tags',
    'person_merge_events',
    'departments'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF to_regclass('public.' || t) IS NULL THEN
      CONTINUE;
    END IF;
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY tenant_runtime_base ON %I AS PERMISSIVE FOR ALL TO db_app_runtime USING (true) WITH CHECK (true)',
      t
    );
    EXECUTE format(
      $p$CREATE POLICY tenant_runtime_guard ON %I AS RESTRICTIVE FOR ALL TO db_app_runtime
         USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
         WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)$p$,
      t
    );
    EXECUTE format(
      'CREATE POLICY tenant_migrator_maintenance ON %I AS PERMISSIVE FOR ALL TO db_migrator USING (true) WITH CHECK (true)',
      t
    );
  END LOOP;
END $$;

-- Runtime DML grants (immutable finance tables: INSERT+SELECT only)
GRANT SELECT, INSERT, UPDATE ON invoice_documents TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON invoice_lines TO db_app_runtime;
-- Keep UPDATE privilege so SELECT … FOR UPDATE works for concurrency; enforce
-- append-only with reject triggers (REVOKE UPDATE would block row locks).
GRANT SELECT, INSERT, UPDATE ON payment_receipts TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON receipt_allocations TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_credits TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON financial_adjustments TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON clinic_payment_refunds TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON document_number_counters TO db_app_runtime;

GRANT SELECT, INSERT, UPDATE ON inventory_items TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON inventory_lots TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON stock_movements TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON service_item_suggestions TO db_app_runtime;

GRANT SELECT, INSERT, UPDATE ON appointment_waitlist_entries TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON staff_service_links TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON role_permission_scopes TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON online_availability_closures TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_operational_notes TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_staff_tags TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON person_merge_events TO db_app_runtime;

REVOKE DELETE ON payment_receipts FROM db_app_runtime;
REVOKE DELETE ON receipt_allocations FROM db_app_runtime;
REVOKE DELETE ON financial_adjustments FROM db_app_runtime;
REVOKE DELETE ON clinic_payment_refunds FROM db_app_runtime;
REVOKE DELETE ON stock_movements FROM db_app_runtime;
REVOKE DELETE ON person_merge_events FROM db_app_runtime;

CREATE OR REPLACE FUNCTION reject_mutation_append_only()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'append-only table % rejects %', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'payment_receipts',
    'receipt_allocations',
    'financial_adjustments',
    'clinic_payment_refunds',
    'stock_movements',
    'person_merge_events'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER %I_reject_update BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation_append_only()',
      t, t
    );
    EXECUTE format(
      'CREATE TRIGGER %I_reject_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation_append_only()',
      t, t
    );
  END LOOP;
END $$;

DO $$
BEGIN
  IF to_regclass('public.departments') IS NOT NULL THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON departments TO db_app_runtime';
  END IF;
END $$;
