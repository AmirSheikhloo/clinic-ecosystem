-- 1. Item-to-service link kind and ACTIVE status validation (deferred to commit)
CREATE FUNCTION public.ops_item_service_link_check() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_item_kind text;
  v_item_status text;
  v_srv_kind text;
  v_srv_status text;
BEGIN
  SELECT line_kind, line_status INTO v_item_kind, v_item_status
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.item_line_id;

  SELECT line_kind, line_status INTO v_srv_kind, v_srv_status
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.service_line_id;

  IF v_item_kind IS DISTINCT FROM 'ITEM' OR v_item_status IS DISTINCT FROM 'ACTIVE'
     OR v_srv_kind IS DISTINCT FROM 'SERVICE' OR v_srv_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'invoice_item_service_links requires an ACTIVE ITEM line and an ACTIVE SERVICE line'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER invoice_item_service_link_check
  AFTER INSERT OR UPDATE ON public.invoice_item_service_links
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_item_service_link_check();

-- 2. Service-record-to-charge-line patient/service/appointment consistency
CREATE FUNCTION public.ops_service_record_charge_link_check() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_sr record;
  v_line record;
BEGIN
  SELECT patient_id, service_id, appointment_id INTO v_sr
  FROM public.service_records
  WHERE tenant_id = NEW.tenant_id AND id = NEW.service_record_id;

  SELECT beneficiary_patient_id, service_id, appointment_id, line_kind, line_status INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_kind IS DISTINCT FROM 'SERVICE' OR v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'service_record_charge_links requires an ACTIVE SERVICE invoice line' USING ERRCODE = '23514';
  END IF;
  IF v_sr.patient_id <> v_line.beneficiary_patient_id OR v_sr.service_id <> v_line.service_id THEN
    RAISE EXCEPTION 'service_record and invoice_line patient/service mismatch' USING ERRCODE = '23514';
  END IF;
  IF v_sr.appointment_id IS NOT NULL AND v_line.appointment_id IS NOT NULL
     AND v_sr.appointment_id <> v_line.appointment_id THEN
    RAISE EXCEPTION 'service_record and invoice_line appointment mismatch' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER service_record_charge_link_check
  AFTER INSERT ON public.service_record_charge_links
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_service_record_charge_link_check();

-- 3. Receipt allocation, reversal, beneficiary, and invoice-line obligation check (deferred)
CREATE FUNCTION public.ops_receipt_allocation_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_receipt record;
  v_attr_patient uuid;
  v_effective_patient uuid;
  v_inv record;
  v_line record;
  v_orig record;
  v_net_receipt_alloc numeric;
  v_total_refunded numeric;
  v_reversed_on_orig numeric;
  v_adj_delta numeric;
  v_net_line_alloc numeric;
BEGIN
  SELECT status, beneficiary_patient_id INTO v_inv
  FROM public.invoice_documents
  WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id
  FOR UPDATE;

  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'receipt guard missing' USING ERRCODE = '23503'; END IF;

  SELECT id, amount_irr, credit_beneficiary_patient_id INTO v_receipt
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.receipt_id;

  SELECT beneficiary_patient_id INTO v_attr_patient
  FROM public.receipt_beneficiary_attributions
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id;

  v_effective_patient := COALESCE(v_receipt.credit_beneficiary_patient_id, v_attr_patient);
  IF v_effective_patient IS NULL THEN
    RAISE EXCEPTION 'cannot allocate receipt with unresolved beneficiary' USING ERRCODE = '23514';
  END IF;

  IF v_inv.status IS DISTINCT FROM 'POSTED' THEN
    RAISE EXCEPTION 'allocations require a POSTED invoice' USING ERRCODE = '23514';
  END IF;
  IF v_inv.beneficiary_patient_id <> v_effective_patient THEN
    RAISE EXCEPTION 'receipt beneficiary does not match invoice beneficiary' USING ERRCODE = '23514';
  END IF;

  SELECT line_status, patient_payable_amount INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'cannot allocate to a REMOVED invoice line' USING ERRCODE = '23514';
  END IF;

  IF NEW.allocation_kind = 'REVERSE' THEN
    SELECT allocation_kind, amount_irr INTO v_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND id = NEW.reverses_allocation_id;

    IF v_orig.allocation_kind IS DISTINCT FROM 'APPLY' THEN
      RAISE EXCEPTION 'reversal must target an APPLY allocation' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_reversed_on_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id
      AND allocation_kind = 'REVERSE'
      AND reverses_allocation_id = NEW.reverses_allocation_id;

    IF v_reversed_on_orig > v_orig.amount_irr THEN
      RAISE EXCEPTION 'cumulative reversals exceed original APPLY amount' USING ERRCODE = '23514';
    END IF;
  END IF;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_receipt_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id;

  SELECT COALESCE(SUM(amount_irr), 0) INTO v_total_refunded
  FROM public.clinic_payment_refunds
  WHERE tenant_id = NEW.tenant_id AND original_receipt_id = NEW.receipt_id;

  IF v_net_receipt_alloc < 0 OR (v_net_receipt_alloc + v_total_refunded) > v_receipt.amount_irr THEN
    RAISE EXCEPTION 'receipt net allocations plus refunds exceed verified receipt amount' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(patient_delta_irr), 0) INTO v_adj_delta
  FROM public.financial_adjustments
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_line_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF (v_line.patient_payable_amount::numeric + v_adj_delta) < 0
     OR v_net_line_alloc < 0
     OR v_net_line_alloc > (v_line.patient_payable_amount::numeric + v_adj_delta) THEN
    RAISE EXCEPTION 'invoice line patient obligation or allocation cap violated' USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER receipt_allocations_reconcile_trg
  AFTER INSERT ON public.receipt_allocations
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_allocation_reconcile();

-- 4. Financial adjustment post-state & obligation invariant check (deferred)
CREATE FUNCTION public.ops_financial_adjustment_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_inv_status text;
  v_line record;
  v_adj_patient numeric;
  v_adj_basic numeric;
  v_adj_supp numeric;
  v_net_line_alloc numeric;
BEGIN
  SELECT status INTO v_inv_status
  FROM public.invoice_documents
  WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id
  FOR UPDATE;

  IF v_inv_status IS DISTINCT FROM 'POSTED' THEN
    RAISE EXCEPTION 'financial adjustments require a POSTED invoice' USING ERRCODE = '23514';
  END IF;

  SELECT line_status, patient_payable_amount, basic_insurance_expected_share, supplementary_insurance_expected_share
  INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'cannot adjust a REMOVED invoice line' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(patient_delta_irr), 0),
         COALESCE(SUM(basic_insurer_delta_irr), 0),
         COALESCE(SUM(supplementary_insurer_delta_irr), 0)
  INTO v_adj_patient, v_adj_basic, v_adj_supp
  FROM public.financial_adjustments
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF (v_line.patient_payable_amount::numeric + v_adj_patient) < 0
     OR (v_line.basic_insurance_expected_share::numeric + v_adj_basic) < 0
     OR (v_line.supplementary_insurance_expected_share::numeric + v_adj_supp) < 0 THEN
    RAISE EXCEPTION 'financial adjustment drives line obligation below zero' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_line_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF v_net_line_alloc > (v_line.patient_payable_amount::numeric + v_adj_patient) THEN
    RAISE EXCEPTION 'post-adjustment net allocation exceeds reduced patient obligation; reverse excess in same UoW'
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER financial_adjustments_reconcile_trg
  AFTER INSERT ON public.financial_adjustments
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_financial_adjustment_reconcile();

-- 5. Clinic payment refund cap & linked-reversal check (deferred)
CREATE FUNCTION public.ops_clinic_refund_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_receipt_amt bigint;
  v_net_receipt_alloc numeric;
  v_total_refunded numeric;
  v_orig_kind text;
  v_reversed_on_orig numeric;
  v_refunded_on_orig numeric;
BEGIN
  IF NEW.invoice_id IS NOT NULL THEN
    PERFORM 1 FROM public.invoice_documents WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id AND status = 'POSTED' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'refund invoice must be posted' USING ERRCODE = '23514'; END IF;
  END IF;
  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.original_receipt_id
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'receipt guard missing' USING ERRCODE = '23503'; END IF;

  SELECT amount_irr INTO v_receipt_amt
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.original_receipt_id;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_receipt_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.original_receipt_id;

  SELECT COALESCE(SUM(amount_irr), 0) INTO v_total_refunded
  FROM public.clinic_payment_refunds
  WHERE tenant_id = NEW.tenant_id AND original_receipt_id = NEW.original_receipt_id;

  IF (v_net_receipt_alloc + v_total_refunded) > v_receipt_amt THEN
    RAISE EXCEPTION 'refund exceeds unapplied refundable balance on receipt' USING ERRCODE = '23514';
  END IF;

  IF NEW.original_allocation_id IS NOT NULL THEN
    SELECT allocation_kind INTO v_orig_kind
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND id = NEW.original_allocation_id;

    IF v_orig_kind IS DISTINCT FROM 'APPLY' THEN
      RAISE EXCEPTION 'refund original_allocation_id must reference an APPLY row' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_reversed_on_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id
      AND allocation_kind = 'REVERSE'
      AND reverses_allocation_id = NEW.original_allocation_id;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_refunded_on_orig
    FROM public.clinic_payment_refunds
    WHERE tenant_id = NEW.tenant_id AND original_allocation_id = NEW.original_allocation_id;

    IF v_refunded_on_orig > v_reversed_on_orig THEN
      RAISE EXCEPTION 'refunds attributed to allocation exceed reversed portion' USING ERRCODE = '23514';
    END IF;
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER clinic_payment_refunds_reconcile_trg
  AFTER INSERT ON public.clinic_payment_refunds
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_clinic_refund_reconcile();

-- 6. Inventory lot rules, non-negative balance, return cap, transfer zero-sum, and lot state sync
CREATE FUNCTION public.ops_inventory_lot_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF ROW(NEW.id, NEW.tenant_id, NEW.item_id, NEW.is_lot_tracked, NEW.requires_expiry,
           NEW.source_lot_id, NEW.expires_on, NEW.received_at_utc, NEW.created_at_utc)
       IS DISTINCT FROM ROW(OLD.id, OLD.tenant_id, OLD.item_id, OLD.is_lot_tracked, OLD.requires_expiry,
           OLD.source_lot_id, OLD.expires_on, OLD.received_at_utc, OLD.created_at_utc) THEN
      RAISE EXCEPTION 'lot identity, expiry and provenance immutable' USING ERRCODE = '23514';
    END IF;
  END IF;
  PERFORM 1 FROM public.inventory_items WHERE tenant_id = NEW.tenant_id AND id = NEW.item_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'inventory item missing' USING ERRCODE = '23503'; END IF;
  IF NEW.source_lot_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.inventory_lots l
    WHERE l.tenant_id = NEW.tenant_id AND l.item_id = NEW.item_id AND l.id = NEW.source_lot_id
      AND l.source_lot_id IS NULL AND l.expires_on IS NOT DISTINCT FROM NEW.expires_on
  ) THEN RAISE EXCEPTION 'invalid lot provenance' USING ERRCODE = '23514'; END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER inventory_lots_guard
  BEFORE INSERT OR UPDATE ON public.inventory_lots
  FOR EACH ROW EXECUTE FUNCTION public.ops_inventory_lot_guard();

CREATE FUNCTION public.ops_stock_movement_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_lot record;
  v_lot_balance numeric;
  v_orig record;
  v_returned_qty numeric;
  v_transfer_net numeric;
BEGIN
  PERFORM 1 FROM public.inventory_items
  WHERE tenant_id = NEW.tenant_id AND id = NEW.item_id
  FOR UPDATE;

  SELECT lot_status, source_lot_id, expires_on INTO v_lot
  FROM public.inventory_lots
  WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND id = NEW.lot_id
  FOR UPDATE;

  IF NEW.movement_kind IN ('SERVICE_CONSUMPTION', 'SALE') AND
     (v_lot.lot_status <> 'AVAILABLE' OR (v_lot.expires_on IS NOT NULL AND
      v_lot.expires_on < (transaction_timestamp() AT TIME ZONE 'Asia/Tehran')::date)) THEN
    RAISE EXCEPTION 'cannot consume or sell from a non-AVAILABLE lot' USING ERRCODE = '23514';
  END IF;

  IF NEW.movement_kind = 'RETURN' THEN
    SELECT movement_kind, lot_id, quantity_delta INTO v_orig
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND id = NEW.original_movement_id;

    IF v_orig.movement_kind NOT IN ('SERVICE_CONSUMPTION', 'SALE') THEN
      RAISE EXCEPTION 'stock return must reference SERVICE_CONSUMPTION or SALE' USING ERRCODE = '23514';
    END IF;

    IF NEW.return_disposition = 'REUSABLE' AND (NEW.lot_id <> v_orig.lot_id OR v_lot.lot_status <> 'AVAILABLE' OR
        (v_lot.expires_on IS NOT NULL AND v_lot.expires_on < (transaction_timestamp() AT TIME ZONE 'Asia/Tehran')::date)) THEN
      RAISE EXCEPTION 'REUSABLE return must restore the original AVAILABLE lot' USING ERRCODE = '23514';
    END IF;

    IF NEW.return_disposition = 'QUARANTINE' AND (v_lot.lot_status <> 'QUARANTINE' OR v_lot.source_lot_id IS DISTINCT FROM v_orig.lot_id) THEN
      RAISE EXCEPTION 'QUARANTINE return must target a QUARANTINE lot linked to original lot' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(quantity_delta), 0) INTO v_returned_qty
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id
      AND item_id = NEW.item_id
      AND movement_kind = 'RETURN'
      AND original_movement_id = NEW.original_movement_id;

    IF v_returned_qty > ABS(v_orig.quantity_delta) THEN
      RAISE EXCEPTION 'cumulative returned stock exceeds original issued quantity' USING ERRCODE = '23514';
    END IF;
  END IF;

  IF NEW.movement_kind IN ('TRANSFER_OUT', 'TRANSFER_IN') THEN
    SELECT COALESCE(SUM(quantity_delta), 0) INTO v_transfer_net
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id
      AND item_id = NEW.item_id
      AND transfer_operation_id = NEW.transfer_operation_id;

    IF v_transfer_net <> 0 OR NOT EXISTS (
      SELECT 1 FROM public.stock_movements m
      WHERE m.tenant_id = NEW.tenant_id AND m.item_id = NEW.item_id
        AND m.transfer_operation_id = NEW.transfer_operation_id
      GROUP BY m.transfer_operation_id HAVING count(*) = 2 AND count(DISTINCT m.lot_id) = 2
    ) THEN
      RAISE EXCEPTION 'stock transfer pair must net to zero within the transaction' USING ERRCODE = '23514';
    END IF;
  END IF;

  SELECT COALESCE(SUM(quantity_delta), 0) INTO v_lot_balance
  FROM public.stock_movements
  WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND lot_id = NEW.lot_id;

  IF v_lot_balance < 0 THEN
    RAISE EXCEPTION 'stock lot balance cannot become negative' USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER stock_movements_reconcile_trg
  AFTER INSERT ON public.stock_movements
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_stock_movement_reconcile();

-- 7. Canonical practitioner resource-type & immutability guard
CREATE FUNCTION public.ops_practitioner_mapping_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_res_type text;
BEGIN
  IF TG_OP = 'UPDATE' AND (NEW.staff_profile_id <> OLD.staff_profile_id OR NEW.bookable_resource_id <> OLD.bookable_resource_id) THEN
    RAISE EXCEPTION 'practitioner staff_profile_id and bookable_resource_id are immutable' USING ERRCODE = '23514';
  END IF;
  SELECT resource_type INTO v_res_type
  FROM public.bookable_resources
  WHERE tenant_id = NEW.tenant_id AND id = NEW.bookable_resource_id;

  IF v_res_type IS DISTINCT FROM 'PRACTITIONER' THEN
    RAISE EXCEPTION 'staff_practitioner_resources requires resource_type = PRACTITIONER' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER staff_practitioner_resources_guard
  BEFORE INSERT OR UPDATE ON public.staff_practitioner_resources
  FOR EACH ROW EXECUTE FUNCTION public.ops_practitioner_mapping_guard();

-- 8. Typed role_permission_scopes ALL vs. FILTER mutual exclusivity guard
CREATE FUNCTION public.ops_role_permission_scope_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  PERFORM 1 FROM public.role_permission_assignments
  WHERE tenant_id = NEW.tenant_id AND id = NEW.role_permission_assignment_id
  FOR UPDATE;

  IF EXISTS (
    SELECT 1 FROM public.role_permission_scopes
    WHERE tenant_id = NEW.tenant_id
      AND role_permission_assignment_id = NEW.role_permission_assignment_id
      AND scope_mode <> NEW.scope_mode
      AND id <> NEW.id
  ) THEN
    RAISE EXCEPTION 'ALL and FILTER scope modes cannot coexist on the same permission grant' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER role_permission_scopes_guard
  BEFORE INSERT OR UPDATE ON public.role_permission_scopes
  FOR EACH ROW EXECUTE FUNCTION public.ops_role_permission_scope_guard();

-- 9. Terminal-state immutability guards (waitlist, online closure, note retraction, identity review)
CREATE FUNCTION public.ops_terminal_state_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
     OR NEW.created_at_utc IS DISTINCT FROM OLD.created_at_utc THEN
    RAISE EXCEPTION 'immutable identity' USING ERRCODE = '23514';
  END IF;
  IF NEW.aggregate_version <> OLD.aggregate_version + 1 THEN
    RAISE EXCEPTION 'aggregate version must advance by one' USING ERRCODE = '23514';
  END IF;
  -- Branch before accessing relation-specific record fields.
  CASE TG_TABLE_NAME
    WHEN 'appointment_waitlist_entries' THEN
      IF OLD.status IN ('CONVERTED','CANCELLED','EXPIRED') OR NEW.patient_id <> OLD.patient_id
         OR NEW.service_id <> OLD.service_id OR NEW.created_by_user_id <> OLD.created_by_user_id THEN
        RAISE EXCEPTION 'terminal waitlist or identity mutation' USING ERRCODE = '23514';
      END IF;
    WHEN 'online_availability_closures' THEN
      IF OLD.reopened_at_utc IS NOT NULL OR NEW.reopened_at_utc IS NULL
         OR ROW(NEW.service_id,NEW.resource_id,NEW.closure_date,NEW.starts_at_utc,NEW.ends_at_utc,NEW.reason,NEW.created_by_user_id)
         IS DISTINCT FROM ROW(OLD.service_id,OLD.resource_id,OLD.closure_date,OLD.starts_at_utc,OLD.ends_at_utc,OLD.reason,OLD.created_by_user_id) THEN
        RAISE EXCEPTION 'closure may only be reopened once' USING ERRCODE = '23514';
      END IF;
    WHEN 'patient_identity_reviews' THEN
      IF OLD.review_state <> 'NEEDS_COMPLETION' OR NEW.review_state NOT IN ('RESOLVED','CANCELLED')
         OR ROW(NEW.patient_id,NEW.reason,NEW.opened_by_user_id,NEW.opened_at_utc)
         IS DISTINCT FROM ROW(OLD.patient_id,OLD.reason,OLD.opened_by_user_id,OLD.opened_at_utc) THEN
        RAISE EXCEPTION 'invalid identity review transition' USING ERRCODE = '23514';
      END IF;
    ELSE RAISE EXCEPTION 'unexpected trigger relation' USING ERRCODE = '23514';
  END CASE;
  RETURN NEW;
END $$;

CREATE TRIGGER waitlist_terminal_guard
  BEFORE UPDATE ON public.appointment_waitlist_entries
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();
CREATE TRIGGER closure_terminal_guard
  BEFORE UPDATE ON public.online_availability_closures
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();
CREATE TRIGGER identity_review_terminal_guard
  BEFORE UPDATE ON public.patient_identity_reviews
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();

CREATE FUNCTION public.ops_note_action_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  PERFORM 1 FROM public.patient_operational_notes
  WHERE tenant_id = NEW.tenant_id AND id = NEW.note_id
  FOR UPDATE;

  IF EXISTS (
    SELECT 1 FROM public.patient_note_actions
    WHERE tenant_id = NEW.tenant_id AND note_id = NEW.note_id AND action_kind = 'RETRACT'
  ) THEN
    RAISE EXCEPTION 'retracted operational note cannot receive further actions' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER patient_note_actions_guard
  BEFORE INSERT ON public.patient_note_actions
  FOR EACH ROW EXECUTE FUNCTION public.ops_note_action_guard();

-- 10. Appointment lifecycle fact enforcement on new transitions (grandfathers legacy rows)
CREATE FUNCTION public.ops_appointment_lifecycle_facts_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.status = 'CHECKED_IN' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'CHECKED_IN') THEN
    IF NOT EXISTS (
      SELECT 1
      FROM public.appointment_arrival_facts aaf
      JOIN public.clinic_visits cv
        ON cv.tenant_id = aaf.tenant_id AND cv.id = aaf.visit_id
      WHERE aaf.tenant_id = NEW.tenant_id
        AND aaf.appointment_id = NEW.id
        AND cv.arrived_at_utc IS NOT NULL
    ) THEN
      RAISE EXCEPTION 'new CHECKED_IN transition requires verified arrival fact and arrived_at_utc'
        USING ERRCODE = '23514';
    END IF;
  END IF;

  IF NEW.status = 'COMPLETED' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'COMPLETED') THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.service_records sr
      WHERE sr.tenant_id = NEW.tenant_id
        AND sr.appointment_id = NEW.id
        AND sr.record_kind = 'PERFORMED'
    ) THEN
      RAISE EXCEPTION 'new COMPLETED transition requires a PERFORMED service_records entry'
        USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER appointments_lifecycle_facts_trg
  AFTER INSERT OR UPDATE OF status ON public.appointments
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_appointment_lifecycle_facts_guard();

REVOKE ALL ON FUNCTION public.ops_item_service_link_check() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_service_record_charge_link_check() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_allocation_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_financial_adjustment_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_clinic_refund_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_inventory_lot_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_stock_movement_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_practitioner_mapping_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_role_permission_scope_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_terminal_state_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_note_action_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_appointment_lifecycle_facts_guard() FROM PUBLIC;
