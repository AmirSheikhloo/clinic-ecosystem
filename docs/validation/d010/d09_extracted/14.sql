CREATE FUNCTION public.ops_invoice_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'invoice documents cannot be deleted at runtime' USING ERRCODE = '23514';
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'DRAFT' THEN
      RAISE EXCEPTION 'invoice document must begin in DRAFT status' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
  END IF;
  IF OLD.status <> 'DRAFT' THEN
    RAISE EXCEPTION 'posted or voided invoice document is immutable' USING ERRCODE = '23514';
  END IF;
  IF NEW.id <> OLD.id OR NEW.tenant_id <> OLD.tenant_id
     OR NEW.beneficiary_patient_id <> OLD.beneficiary_patient_id
     OR NEW.created_at_utc <> OLD.created_at_utc THEN
    RAISE EXCEPTION 'invoice identity fields are immutable' USING ERRCODE = '23514';
  END IF;
  IF NEW.aggregate_version <> OLD.aggregate_version + 1 THEN
    RAISE EXCEPTION 'invoice aggregate_version must increment by 1' USING ERRCODE = '23514';
  END IF;
  IF NEW.status = 'POSTED' AND NOT EXISTS (
    SELECT 1 FROM public.invoice_lines l
    WHERE l.tenant_id = OLD.tenant_id AND l.invoice_id = OLD.id AND l.line_status = 'ACTIVE'
  ) THEN
    RAISE EXCEPTION 'cannot post an invoice with zero ACTIVE lines' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER invoice_documents_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_documents
  FOR EACH ROW EXECUTE FUNCTION public.ops_invoice_guard();

CREATE FUNCTION public.ops_draft_child_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_tenant_id uuid;
  v_invoice_id uuid;
  v_status text;
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF TG_TABLE_NAME = 'draft_discount_actions' THEN
      RAISE EXCEPTION 'draft_discount_actions are append-only and cannot be deleted' USING ERRCODE = '23514';
    END IF;
    v_tenant_id := OLD.tenant_id;
    v_invoice_id := OLD.invoice_id;
  ELSE
    v_tenant_id := NEW.tenant_id;
    v_invoice_id := NEW.invoice_id;
  END IF;

  IF TG_OP = 'UPDATE' AND (NEW.tenant_id <> OLD.tenant_id OR NEW.invoice_id <> OLD.invoice_id OR NEW.id <> OLD.id) THEN
    RAISE EXCEPTION 'invoice child identity cannot be reparented' USING ERRCODE = '23514';
  END IF;

  SELECT status INTO v_status
  FROM public.invoice_documents
  WHERE tenant_id = v_tenant_id AND id = v_invoice_id
  FOR UPDATE;

  IF NOT FOUND OR v_status IS DISTINCT FROM 'DRAFT' THEN
    RAISE EXCEPTION 'invoice children may mutate only while parent invoice is DRAFT' USING ERRCODE = '23514';
  END IF;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER invoice_lines_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_lines
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER invoice_item_service_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_item_service_links
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER insurer_expectation_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_insurer_expectations
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER revenue_share_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.revenue_share_allocations
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER discount_action_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.draft_discount_actions
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();

REVOKE ALL ON FUNCTION public.ops_invoice_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_draft_child_guard() FROM PUBLIC;
