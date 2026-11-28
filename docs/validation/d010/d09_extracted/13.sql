-- The migration sets this transaction-local selector to an explicit JSON array
-- of only the tables created in that revision, e.g. '["departments"]'.
-- No default and no silent skip; reject unknown, duplicate or empty selections.
DO $policies$
DECLARE
  rel text;
  selected text[];
  append_only text[] := ARRAY[
    'reception_groups', 'reception_group_appointments', 'visit_appointments',
    'appointment_arrival_facts', 'service_records', 'service_record_practitioners',
    'historical_appointment_entries', 'draft_discount_actions', 'service_record_charge_links',
    'payment_receipts', 'receipt_beneficiary_attributions', 'receipt_allocations',
    'financial_adjustments', 'clinic_payment_refunds', 'insurer_settlement_entries',
    'revenue_share_adjustments', 'stock_movements', 'inventory_lot_state_events',
    'patient_operational_notes', 'patient_note_actions', 'person_merge_events'
  ];
  mutable_metadata text[] := ARRAY[
    'staff_practitioner_resources', 'staff_service_links', 'departments',
    'department_service_links', 'department_practitioner_links', 'clinic_visits',
    'appointment_waitlist_entries', 'service_availability_guards', 'online_availability_closures',
    'billable_items', 'cashier_shifts', 'clinic_payment_instruments',
    'invoice_documents', 'invoice_lines', 'document_number_counters',
    'payment_attempts', 'unverified_payment_claims', 'ledger_receipt_guards',
    'clinic_insurers', 'clinic_service_referrers', 'inventory_items',
    'inventory_lots', 'service_item_suggestions', 'staff_tag_catalog',
    'patient_staff_tags', 'patient_identity_reviews'
  ];
  controlled_delete text[] := ARRAY[
    'role_permission_scopes', 'invoice_item_service_links',
    'invoice_insurer_expectations', 'revenue_share_allocations'
  ];
BEGIN
  SELECT array_agg(value) INTO selected FROM jsonb_array_elements_text(
    NULLIF(current_setting('app.ops_migration_tables', true), '')::jsonb);
  IF selected IS NULL OR cardinality(selected) = 0
     OR EXISTS (SELECT 1 FROM unnest(selected) t(x) WHERE NOT (x = ANY(append_only || mutable_metadata || controlled_delete)))
     OR cardinality(selected) <> (SELECT count(DISTINCT x) FROM unnest(selected) t(x)) THEN
    RAISE EXCEPTION 'explicit valid migration table subset required';
  END IF;
  FOREACH rel IN ARRAY selected LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO db_migrator', rel);
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', rel);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', rel);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, db_app_runtime', rel);

    EXECUTE format(
      'CREATE POLICY tenant_runtime_base ON public.%I AS PERMISSIVE FOR ALL TO db_app_runtime USING (true) WITH CHECK (true)',
      rel
    );
    EXECUTE format(
      'CREATE POLICY tenant_runtime_guard ON public.%I AS RESTRICTIVE FOR ALL TO db_app_runtime '
      'USING (tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid) '
      'WITH CHECK (tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid)',
      rel
    );
    EXECUTE format(
      'CREATE POLICY tenant_migrator_maintenance ON public.%I AS PERMISSIVE FOR ALL TO db_migrator USING (true) WITH CHECK (true)',
      rel
    );

    IF rel = ANY(append_only) THEN
      EXECUTE format('GRANT SELECT, INSERT ON TABLE public.%I TO db_app_runtime', rel);
    ELSIF rel = ANY(mutable_metadata) THEN
      EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.%I TO db_app_runtime', rel);
    ELSE
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO db_app_runtime', rel);
    END IF;
  END LOOP;
  IF 'ledger_receipt_guards' = ANY(selected) THEN
    REVOKE UPDATE ON TABLE public.ledger_receipt_guards FROM db_app_runtime;
    GRANT UPDATE (lock_version) ON TABLE public.ledger_receipt_guards TO db_app_runtime;
  END IF;
END $policies$;
