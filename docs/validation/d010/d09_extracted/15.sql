CREATE TABLE ledger_receipt_guards (
  receipt_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  lock_version BIGINT NOT NULL DEFAULT 1 CHECK (lock_version > 0),
  UNIQUE (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL
);

CREATE TABLE receipt_beneficiary_attributions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  beneficiary_patient_id UUID NOT NULL,
  operator_user_id UUID NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  correlation_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE FUNCTION public.ops_create_receipt_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  INSERT INTO public.ledger_receipt_guards(receipt_id, tenant_id)
  VALUES (NEW.id, NEW.tenant_id);
  RETURN NEW;
END $$;

CREATE TRIGGER payment_receipt_create_guard
  AFTER INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_create_receipt_guard();

CREATE FUNCTION public.ops_receipt_attribution_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_existing_beneficiary uuid;
BEGIN
  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  FOR UPDATE;

  SELECT credit_beneficiary_patient_id INTO v_existing_beneficiary
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.receipt_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'receipt not found for attribution' USING ERRCODE = '23503';
  END IF;
  IF v_existing_beneficiary IS NOT NULL THEN
    RAISE EXCEPTION 'receipt already has an immutable beneficiary' USING ERRCODE = '23514';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  ) THEN
    RAISE EXCEPTION 'cannot attribute receipt after allocations exist' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER receipt_beneficiary_attribution_guard
  BEFORE INSERT ON public.receipt_beneficiary_attributions
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_attribution_guard();

REVOKE ALL ON FUNCTION public.ops_create_receipt_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_attribution_guard() FROM PUBLIC;
