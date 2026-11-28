-- Prevent a resource type change from invalidating a canonical practitioner mapping.
CREATE FUNCTION public.ops_bookable_resource_type_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.resource_type IS DISTINCT FROM OLD.resource_type AND EXISTS (
    SELECT 1 FROM public.staff_practitioner_resources m
    WHERE m.tenant_id = OLD.tenant_id AND m.bookable_resource_id = OLD.id
  ) THEN
    RAISE EXCEPTION 'mapped practitioner resource type cannot change' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER bookable_resources_practitioner_type_guard
  BEFORE UPDATE OF resource_type ON public.bookable_resources
  FOR EACH ROW EXECUTE FUNCTION public.ops_bookable_resource_type_guard();

-- Match instrument kind and active shift against receipt/refund facts.
-- Application must prelock shift before invoice/receipt guards. This check is not external verification.
CREATE FUNCTION public.ops_receipt_instrument_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_method text;
  v_instrument record;
  v_shift record;
  v_expected_kind text;
BEGIN
  CASE TG_TABLE_NAME
    WHEN 'payment_receipts' THEN v_method := NEW.payment_method;
    WHEN 'clinic_payment_refunds' THEN v_method := NEW.refund_method;
    ELSE RAISE EXCEPTION 'unexpected relation';
  END CASE;
  IF NEW.shift_id IS NOT NULL THEN
    SELECT * INTO v_shift FROM public.cashier_shifts
      WHERE tenant_id = NEW.tenant_id AND id = NEW.shift_id FOR UPDATE;
    IF NOT FOUND OR v_shift.closed_at_utc IS NOT NULL
      OR NEW.occurred_at_utc < v_shift.opened_at_utc
      OR NEW.department_id IS DISTINCT FROM v_shift.department_id THEN
      RAISE EXCEPTION 'invalid cashier shift or department' USING ERRCODE = '23514';
    END IF;
  END IF;
  v_expected_kind := CASE v_method WHEN 'POS' THEN 'POS_TERMINAL'
    WHEN 'CARD_TO_CARD' THEN 'BANK_DESTINATION' WHEN 'ONLINE' THEN 'GATEWAY_MERCHANT'
    WHEN 'CASH' THEN 'CASH_REGISTER' END;
  IF NEW.instrument_id IS NOT NULL THEN
    SELECT * INTO v_instrument FROM public.clinic_payment_instruments
      WHERE tenant_id = NEW.tenant_id AND id = NEW.instrument_id FOR SHARE;
    IF NOT FOUND OR NOT v_instrument.is_active
      OR v_instrument.instrument_kind IS DISTINCT FROM v_expected_kind
      OR (v_instrument.department_id IS NOT NULL AND
          NEW.department_id IS DISTINCT FROM v_instrument.department_id) THEN
      RAISE EXCEPTION 'wrong or inactive payment instrument' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER payment_receipt_instrument_guard BEFORE INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_instrument_guard();
CREATE TRIGGER clinic_refund_instrument_guard BEFORE INSERT ON public.clinic_payment_refunds
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_instrument_guard();

-- This trigger verifies linkage and state, NOT trustworthiness of a bank/provider response.
-- Until a verified source/actor contract exists, runtime live ONLINE/CARD_TO_CARD posting is disabled.
CREATE FUNCTION public.ops_receipt_evidence_link_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  a record;
  c record;
BEGIN
  IF NEW.payment_method = 'ONLINE' THEN
    SELECT * INTO a FROM public.payment_attempts
      WHERE tenant_id = NEW.tenant_id AND id = NEW.payment_attempt_id;
    IF NOT FOUND OR a.state IS DISTINCT FROM 'VERIFIED'
      OR a.expected_amount_irr IS DISTINCT FROM NEW.amount_irr
      OR a.currency_code IS DISTINCT FROM NEW.currency_code
      OR a.merchant_instrument_id IS DISTINCT FROM NEW.instrument_id
      OR a.beneficiary_patient_id IS DISTINCT FROM NEW.credit_beneficiary_patient_id
      OR NULLIF(btrim(NEW.provider_reference),'') IS NULL
      OR NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
      RAISE EXCEPTION 'receipt does not match verified attempt' USING ERRCODE = '23514';
    END IF;
  ELSIF NEW.payment_method = 'CARD_TO_CARD' THEN
    SELECT * INTO c FROM public.unverified_payment_claims
      WHERE tenant_id = NEW.tenant_id AND id = NEW.verified_claim_id;
    IF NOT FOUND OR c.state IS DISTINCT FROM 'VERIFIED'
      OR c.claimed_amount_irr IS DISTINCT FROM NEW.amount_irr
      OR c.currency_code IS DISTINCT FROM NEW.currency_code
      OR c.destination_instrument_id IS DISTINCT FROM NEW.instrument_id
      OR c.beneficiary_patient_id IS DISTINCT FROM NEW.credit_beneficiary_patient_id
      OR NULLIF(btrim(NEW.provider_reference),'') IS NULL
      OR NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
      RAISE EXCEPTION 'receipt does not match independently reviewed claim' USING ERRCODE = '23514';
    END IF;
  ELSIF NEW.payment_method = 'POS' AND NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
    RAISE EXCEPTION 'POS evidence missing' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER payment_receipt_evidence_link_guard BEFORE INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_evidence_link_guard();

-- Recheck linked line kinds and status when posting, even if a draft link was
-- created in a prior transaction and its lines subsequently changed.
CREATE FUNCTION public.ops_invoice_post_link_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.status = 'DRAFT' AND NEW.status = 'POSTED' THEN
    IF EXISTS (
      SELECT 1 FROM public.invoice_item_service_links x
      JOIN public.invoice_lines i ON (i.tenant_id,i.invoice_id,i.id) = (x.tenant_id,x.invoice_id,x.item_line_id)
      JOIN public.invoice_lines l ON (l.tenant_id,l.invoice_id,l.id) = (x.tenant_id,x.invoice_id,x.service_line_id)
      WHERE x.tenant_id = NEW.tenant_id AND x.invoice_id = NEW.id
        AND (i.line_kind <> 'ITEM' OR i.line_status <> 'ACTIVE' OR l.line_kind <> 'SERVICE' OR l.line_status <> 'ACTIVE')
    ) THEN RAISE EXCEPTION 'invalid invoice item/service association' USING ERRCODE = '23514'; END IF;
    IF EXISTS (
      SELECT 1 FROM public.invoice_lines l
      WHERE l.tenant_id = NEW.tenant_id AND l.invoice_id = NEW.id AND l.line_status = 'ACTIVE'
       AND (l.basic_insurance_expected_share::numeric <> COALESCE((SELECT sum(e.expected_amount_irr)
          FROM public.invoice_insurer_expectations e WHERE e.tenant_id=l.tenant_id AND e.invoice_line_id=l.id AND e.coverage_kind='BASIC'),0)
        OR l.supplementary_insurance_expected_share::numeric <> COALESCE((SELECT sum(e.expected_amount_irr)
          FROM public.invoice_insurer_expectations e WHERE e.tenant_id=l.tenant_id AND e.invoice_line_id=l.id AND e.coverage_kind='SUPPLEMENTARY'),0))
    ) THEN RAISE EXCEPTION 'insurer expectation snapshot mismatch' USING ERRCODE = '23514'; END IF;
    IF EXISTS (SELECT 1 FROM public.invoice_insurer_expectations e JOIN public.invoice_lines l
      ON (l.tenant_id,l.invoice_id,l.id)=(e.tenant_id,e.invoice_id,e.invoice_line_id)
      WHERE e.tenant_id=NEW.tenant_id AND e.invoice_id=NEW.id AND l.line_status <> 'ACTIVE') THEN
      RAISE EXCEPTION 'expectation on removed invoice line' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER invoice_post_link_guard BEFORE UPDATE OF status ON public.invoice_documents
  FOR EACH ROW EXECUTE FUNCTION public.ops_invoice_post_link_guard();

-- Terminal tag removal cannot be undone or alter the original assignment.
CREATE FUNCTION public.ops_patient_tag_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.removed_at_utc IS NOT NULL OR NEW.removed_at_utc IS NULL OR
    ROW(NEW.id,NEW.tenant_id,NEW.patient_id,NEW.tag_id,NEW.department_id,NEW.service_id,NEW.created_by_user_id,NEW.created_at_utc)
    IS DISTINCT FROM ROW(OLD.id,OLD.tenant_id,OLD.patient_id,OLD.tag_id,OLD.department_id,OLD.service_id,OLD.created_by_user_id,OLD.created_at_utc) THEN
    RAISE EXCEPTION 'tag assignment may only be removed once' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER patient_staff_tag_guard BEFORE UPDATE ON public.patient_staff_tags
  FOR EACH ROW EXECUTE FUNCTION public.ops_patient_tag_guard();

REVOKE ALL ON FUNCTION public.ops_bookable_resource_type_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_instrument_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_evidence_link_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_invoice_post_link_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_patient_tag_guard() FROM PUBLIC;
