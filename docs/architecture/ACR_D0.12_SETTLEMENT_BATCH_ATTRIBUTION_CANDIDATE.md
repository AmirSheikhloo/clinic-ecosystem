# ACR-D0.12 Candidate — Settlement-Batch Attribution (Multi-Patient Shared Collection)

**Status:** PROPOSED architecture review candidate — **NOT RATIFIED**.  
**Feature flag (mandatory default):** `CLINIC_MULTI_PATIENT_SETTLEMENT=off`  
**Does not:** Land official Alembic TP0008+, weaken ACR-D0.11 one-beneficiary invoice/receipt guards, activate live CARD_TO_CARD/ONLINE, claim Gates A–D, or authorize production use.

**Supersedes for review purposes:** the short note in `docs/architecture/ACR_D0.11_TASK34_R2_AMENDMENT.md` §1 (that file remains a pointer only).  
**Preserves:** all valid ACR-D0.11 ledger tables, triggers, RLS posture, and disposable PG15 evidence obligations.

**Product context (R2 §21):** Operators may temporarily cart multiple independently identified patients without family accounts. Each patient still receives their own immutable accounting invoice. Target UX is one verified cash/POS collection with independent per-patient accounting outcomes — **only after** this candidate is independently reviewed, owner-ratified, and disposable race tests pass. Until then UI must settle as **separate** invoices/receipts or unpaid.

---

## 0. Non-negotiable preserved invariants

1. **One beneficiary per invoice.** `invoice_documents.beneficiary_patient_id` remains mandatory and immutable after post. No multi-beneficiary invoice row.
2. **Matching receipt ↔ invoice beneficiary on allocation.** ACR-D0.11 `ops_receipt_allocation_reconcile` continues to reject allocation when effective receipt beneficiary ≠ invoice beneficiary (`receipt beneficiary does not match invoice beneficiary`).
3. **Unresolved beneficiary blocks allocation/credit.** `credit_beneficiary_patient_id` or `receipt_beneficiary_attributions` still required before allocation.
4. **Tenant isolation / RLS.** All new tables tenant-scoped with MATCH FULL composite FKs where children share a parent.
5. **Synthetic payment evidence only** in disposable development. Live providers remain Gate B+.
6. **Shared settlement stays DISABLED** until ratification flips the feature flag under an approved rollout record.

This candidate adds a **layer above** per-patient receipts; it does not replace or dilute the above guards.

---

## 1. Problem statement

Reception often collects one physical cash tender or one POS authorization covering several patients in one visit group (e.g. parent + children). ACR-D0.11 correctly forbids putting multiple beneficiaries on one invoice or cross-allocating one receipt to another patient’s invoice.

Without a new contract, product choices are:

| Option | Accounting honesty | UX |
|---|---|---|
| A. Separate checkout per patient (current safe default) | Honest | Extra operator steps |
| B. Fake multiple receipts reusing one POS reference | Dishonest / uniqueness violation | Appears convenient |
| C. Weaken one-beneficiary guards | Forbidden | — |
| D. Settlement batch + per-beneficiary attributions (this candidate) | Honest if proven | One collection action |

Option B and C are rejected. Option D is proposed under feature flag.

---

## 2. Conceptual model

```
settlement_batches          1 verified external inflow (CASH drawer event or synthetic POS evidence)
        │
        ├── settlement_batch_attributions[]   exact IRR slices → beneficiary patient
        │         │
        │         └── payment_receipts (1:1 per attribution)  existing ACR-D0.11 row
        │                   └── receipt_allocations → that patient's invoice_lines only
        │
        └── optional settlement_batch_payer_ref   non-patient payer label (no clinical access grant)
```

Definitions:

- **Settlement batch:** tenant-scoped record representing exactly one verified external inflow, with a unique evidence key.
- **Attribution:** exact integer IRR amount assigned to exactly one beneficiary patient; creates exactly one `payment_receipts` row for that patient (or links an already-created receipt under strict rules below).
- **Invoice:** unchanged — one beneficiary, immutable posted snapshot.
- **Print:** independent per-patient thermal receipts (batch print = consecutive jobs); shared payment summary (if ever authorized) must omit clinical line detail.

---

## 3. Proposed DDL (disposable / review only — not official Alembic)

```sql
-- FEATURE FLAG GATE: application MUST refuse writes unless CLINIC_MULTI_PATIENT_SETTLEMENT=on
-- AND environment is disposable/synthetic. Default off.

CREATE TABLE settlement_batches (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  batch_number VARCHAR(64) NOT NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR' CHECK (currency_code = 'IRR'),
  payment_method VARCHAR(16) NOT NULL CHECK (payment_method IN ('CASH', 'POS')),
  -- Unique external evidence: synthetic POS reference or cashier-shift cash event id.
  evidence_kind VARCHAR(32) NOT NULL
    CHECK (evidence_kind IN ('SYNTHETIC_POS', 'CASH_SHIFT_EVENT')),
  evidence_reference VARCHAR(128) NOT NULL,
  evidence_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(24) NOT NULL DEFAULT 'OPEN'
    CHECK (status IN ('OPEN', 'ATTRIBUTING', 'COMMITTED', 'FAILED', 'CANCELLED')),
  cashier_shift_id UUID,
  department_id UUID,
  operator_user_id UUID NOT NULL,
  idempotency_key VARCHAR(64) NOT NULL,
  committed_at_utc TIMESTAMPTZ,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  aggregate_version INT NOT NULL DEFAULT 1 CHECK (aggregate_version >= 1),
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, batch_number),
  UNIQUE (tenant_id, idempotency_key),
  -- Unique external evidence per tenant+method+kind
  UNIQUE (tenant_id, payment_method, evidence_kind, evidence_reference),
  FOREIGN KEY (tenant_id, cashier_shift_id)
    REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id)
    REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (payment_method = 'POS' AND evidence_kind = 'SYNTHETIC_POS')
    OR (payment_method = 'CASH' AND evidence_kind = 'CASH_SHIFT_EVENT')
  ),
  CHECK (jsonb_typeof(evidence_payload) = 'object')
);

CREATE TABLE settlement_batch_attributions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  batch_id UUID NOT NULL,
  beneficiary_patient_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  receipt_id UUID, -- set when receipt row created/linked
  attribution_status VARCHAR(24) NOT NULL DEFAULT 'PENDING'
    CHECK (attribution_status IN ('PENDING', 'RECEIPTED', 'FAILED', 'REVERSED')),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, batch_id, beneficiary_patient_id),
  UNIQUE (tenant_id, batch_id, invoice_id),
  UNIQUE (tenant_id, id, batch_id, beneficiary_patient_id),
  FOREIGN KEY (tenant_id, batch_id)
    REFERENCES settlement_batches(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, beneficiary_patient_id)
    REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, beneficiary_patient_id)
    REFERENCES invoice_documents(tenant_id, id, beneficiary_patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, receipt_id)
    REFERENCES payment_receipts(tenant_id, id) MATCH SIMPLE
);

CREATE TABLE settlement_batch_events (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  batch_id UUID NOT NULL,
  event_kind VARCHAR(48) NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  actor_user_id UUID,
  created_at_utc TIMESTAMPTZ NOT NULL,
  FOREIGN KEY (tenant_id, batch_id)
    REFERENCES settlement_batches(tenant_id, id) MATCH FULL
);
```

Application-level constraint (enforced in UoW + deferred trigger):

\[
\sum_{\text{attributions in batch}} \text{amount\_irr} = \text{batch.amount\_irr}
\]

when `status = COMMITTED`. OPEN batches may be built incrementally but cannot commit under/over.

---

## 4. Conservation

1. On COMMIT: sum(attribution amounts) MUST equal `batch.amount_irr` exactly (integer IRR).
2. Each attribution amount MUST be ≤ that invoice’s outstanding patient obligation at lock time.
3. Reject zero, negative, or unspecified beneficiary attributions.
4. Reject leftover unattributed batch amount at commit (no silent “clinic suspense” without an explicit ratified suspense account — **out of scope**; fail closed).
5. Over-allocation under concurrency: use lock order in §7; loser receives deterministic conflict, not partial silent trim.

---

## 5. Unique external evidence

1. `(tenant_id, payment_method, evidence_kind, evidence_reference)` UNIQUE.
2. POS: evidence_reference is the synthetic terminal approval id from the isolated adapter; never client-invented free text alone.
3. CASH: evidence_reference binds to an open cashier shift cash-in event id.
4. Reuse of the same evidence on a second batch → conflict (`evidence_reuse`).
5. Screenshot / operator assertion without adapter verification → rejected.
6. Live CARD_TO_CARD / ONLINE evidence kinds are **not** defined in this candidate.

---

## 6. Idempotency

1. Batch create/commit uses `idempotency_key` unique per tenant (header or body).
2. Same key + same payload → return original batch result (`replayed=true`).
3. Same key + different payload → `409 idempotency_payload_mismatch`.
4. Attribution rows use deterministic keys `(batch_id, invoice_id)` so retries do not double-insert.
5. Receipt insertion inside attribution uses existing finance receipt idempotency / ledger guards.
6. Print jobs for the resulting receipts use **separate** print-job identity (R2 print contract); reprint never recreates the batch.

---

## 7. Beneficiary isolation

1. Each attribution names exactly one `beneficiary_patient_id` matching the target invoice’s beneficiary (composite FK).
2. Created `payment_receipts` row MUST set `credit_beneficiary_patient_id` to that patient (or insert matching `receipt_beneficiary_attributions`) **before** allocation.
3. Existing ACR-D0.11 trigger still verifies receipt beneficiary = invoice beneficiary — **do not disable**.
4. No automatic transfer of patient credit between siblings.
5. Payer person (optional future column) is **not** a clinical accessor and does not grant dossier rights.
6. Scope authorization: operator must be authorized for **every** patient/invoice/department/service in the batch; fail closed if any member is out of scope.

---

## 8. Lock order (concurrency)

Acquire locks in this global order to avoid deadlocks:

1. `settlement_batches` row (`FOR UPDATE`) by `id`
2. Each distinct `invoice_documents` row ascending by `invoice_id`
3. Each `ledger_receipt_guards` / receipt row as created
4. Related shift row if CASH

Competing commits on overlapping invoices: one succeeds; others fail with `invoice_lock_conflict` or outstanding-insufficient — no torn attribution.

Disposable PG15 races required before ratification:

- Two batches attributing the same invoice outstanding concurrently
- Duplicate evidence_reference inserts
- Commit vs refund on one member invoice
- Commit vs invoice void

---

## 9. Partial failure

| Phase | Failure | Recovery |
|---|---|---|
| OPEN build | Validation error on one patient | Batch remains OPEN; remove bad attribution; others untouched |
| ATTRIBUTING | Receipt insert fails mid-loop | Mark batch FAILED or roll back entire UoW; **no** committed half-batch; emit `settlement_batch_events` |
| After COMMIT | Print failure | Finance unchanged; print recovery only |
| After COMMIT | One patient refund | Refund that receipt/lines only; siblings unchanged; batch remains COMMITTED historical fact |

Never leave COMMITTED with sum(attributions) ≠ amount_irr. Prefer single UoW for ATTRIBUTING→COMMITTED.

---

## 10. Credit

1. If an attribution amount exceeds a single invoice’s outstanding **and** `accept_unapplied_credit` is true for that beneficiary, surplus becomes that patient’s credit only (existing receipt unapplied semantics).
2. Cross-patient credit application remains forbidden without a future, separately ratified relationship/credit-share contract (Jane-style related-client credit is **not** imported as Iran policy).
3. Unresolved beneficiary credit still blocked by ACR-D0.11.

---

## 11. Refunds

1. Refunds target `clinic_payment_refunds` against an **original receipt/allocation** of one beneficiary.
2. Batch id may be recorded in refund audit detail for traceability; refund does not reverse the whole batch.
3. Caps and reversal rules remain ACR-D0.11 (cumulative refund ≤ reversed ≤ original APPLY).
4. Sibling patients’ receipts/invoices unchanged.
5. Concurrent refund vs batch commit: lock order §8; deterministic conflict.

---

## 12. Privacy

1. Batch record stores payment totals and evidence references — **not** clinical notes, full national IDs, or unnecessary phones.
2. Per-patient thermal receipts remain independent; batch print concatenates separable receipts with cut marks.
3. Optional shared payment summary (if product later enables) may show batch number, method, total, and per-patient payable totals **without** service-line clinical detail.
4. Payer label (if present) does not expand medical access.
5. Audit/export of batches is permission-scoped (`FINANCE_*`); cross-tenant denied.

---

## 13. Audit

Emit (same UoW as state change) append-only audit + optional outbox candidates:

- `settlement_batch.created`
- `settlement_batch.attribution_added`
- `settlement_batch.committed`
- `settlement_batch.failed`
- `settlement_batch.cancelled`
- existing `receipt.recorded` / `allocation.applied` per beneficiary

Audit detail includes batch id, evidence reference (non-secret), amounts, invoice ids, actor, correlation/idempotency key. No signing private keys or raw card data.

---

## 14. Recovery

1. Client timeout after commit unknown: query by `idempotency_key` or `batch_id`; return COMMITTED result without re-charging evidence.
2. Client timeout during ATTRIBUTING: server finalizes to COMMITTED or FAILED atomically; client reconciles.
3. FAILED batch: evidence_reference remains consumed (unique) to prevent double capture; operator starts a **new** batch only with new evidence or explicit ratified void-evidence procedure (future). Until void-evidence exists, FAILED POS evidence is quarantined.
4. CANCELLED only from OPEN with zero RECEIPTED attributions.

---

## 15. Duplicate receipt prevention

1. Unique evidence prevents two batches from claiming one POS/cash event.
2. Unique `(batch_id, invoice_id)` prevents two attributions to the same invoice inside one batch.
3. Receipt idempotency + beneficiary guards prevent double allocation of the same money to one invoice beyond outstanding.
4. UI double-submit protected by idempotency key (§6).
5. Automatic print refresh dedupe is orthogonal (print auto-intent); must not create receipts.

---

## 16. Authorization

- Create/commit batch: `FINANCE_RECEIPT_RECORD` (+ shift rules for CASH) AND object-level scope for every invoice/patient/service/department in the set (within-row AND, across-row OR only across the operator’s grant rows — fail closed on missing dimensions).
- View batch: `FINANCE_INVOICE_VIEW` with same scope filtering; no leakage of out-of-scope sibling patients via batch totals (either filter members or deny whole batch if any member out of scope — **prefer deny whole batch** for v1).

---

## 17. Application algorithm (COMMIT)

```
assert feature_flag == on and disposable_env
begin UoW
  lock batch FOR UPDATE
  assert status == OPEN
  assert sum(attrs) == batch.amount_irr
  verify evidence still valid / unused
  lock invoices in id order FOR UPDATE
  for attr in attrs ordered by invoice_id:
      assert invoice POSTED and beneficiary matches
      assert operator scope
      assert attr.amount <= outstanding (+ credit policy)
      create payment_receipt with credit_beneficiary_patient_id = beneficiary
      allocate to that invoice's lines only (existing helpers)
      set attr.receipt_id, attribution_status=RECEIPTED
  set batch.status=COMMITTED, committed_at_utc=now()
  append audit + events
commit
```

On any exception → full rollback; status remains OPEN or transitions to FAILED only via controlled handler that records the event without partial receipts.

---

## 18. Feature flag & rollout

| Environment | Flag | Behavior |
|---|---|---|
| Production / persistent | forced off | API returns `settlement_disabled` |
| Disposable synthetic | default off | Multi-patient cart → separate checkouts + batch **print** only |
| Disposable synthetic | on after ratification | Enable commit path + race suite |

UI may collect multi-patient drafts while flag is off, but **must not** call settlement commit.

---

## 19. Disposable test matrix (required before ratification)

| ID | Scenario | Expect |
|---|---|---|
| SB-01 | Commit two patients, sums equal | COMMITTED; 2 receipts; 2 invoices allocated |
| SB-02 | Sum attributions ≠ batch amount | Reject |
| SB-03 | Duplicate evidence_reference | Reject second batch |
| SB-04 | Attribution to wrong beneficiary invoice | Reject (FK + trigger) |
| SB-05 | Concurrent over-allocate same invoice | Exactly one success |
| SB-06 | Idempotent replay | Same batch; no second receipt |
| SB-07 | Payload mismatch same key | 409 |
| SB-08 | Mid-commit failure injection | No partial receipts |
| SB-09 | Refund patient A after commit | A refunded; B unchanged |
| SB-10 | Out-of-scope patient in batch | Deny |
| SB-11 | Cross-tenant batch id | Not found / deny |
| SB-12 | Flag off | API disabled |
| SB-13 | Print batch after commit | Independent jobs; finance unchanged |
| SB-14 | Unresolved beneficiary attempt | Trigger reject |

---

## 20. Explicit non-goals

- Family accounts / automatic relationships
- Importing Jane/US insurance or fiscal reprint laws
- Live acquirer settlement or insurer settlement reuse
- Weakening `ops_receipt_allocation_reconcile`
- Official migration identifiers (TP0008+) without owner ratification
- Suspense / unattributed overnight holding accounts

---

## 21. Unresolved items for owner / independent review

1. Whether FAILED POS evidence may ever be voided/reused under a controlled procedure.
2. Whether a non-patient payer identity is stored, and under which privacy notice.
3. Whether deny-whole-batch (v1) vs filter-members is preferred for partial scope.
4. Clinical/legal policy for prepaid packages interacting with batch pay (PREPAY remains fail-closed separately).
5. Ratification of this candidate and disposable race evidence sign-off.

---

## 22. Relationship to print & courses

- Thermal print jobs remain independent (§R2 print). Settlement commit success may trigger enrolled auto-print of **each** patient receipt; print failure does not roll back settlement.
- Treatment-course session hints on receipts use clinical completion facts, not settlement batch ids.

---

## 23. Review checklist for ChatGPT/Gemini/owner

- [ ] Confirms one-beneficiary guards untouched
- [ ] Conservation + unique evidence + lock order adequate
- [ ] Partial failure / recovery / refund sibling isolation adequate
- [ ] Privacy & audit adequate for Iranian clinic ops without copying foreign fiscal law
- [ ] Flag-default-off acceptable interim
- [ ] Test matrix sufficient for disposable PG15 proof

**Until all boxes are checked and owner ratifies: shared settlement remains DISABLED.**
