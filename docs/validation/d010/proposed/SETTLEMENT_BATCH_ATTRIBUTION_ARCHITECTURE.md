# Settlement-batch attribution — complete architecture review candidate (Task 34 R2 §8)

**Status:** PROPOSED — NOT ratified. Shared multi-patient settlement remains **DISABLED**.
**Preserves:** one-beneficiary invoice and receipt guards in the current disposable ops contracts.
**Does not:** authorize production activation, Alembic migration, or live payment providers.

## 1. Purpose

Define an unabridged contract for attributing a single external payment inflow to multiple
authorized beneficiaries **without** weakening the existing invariant that each invoice and
each receipt allocation tree currently has exactly one beneficiary patient.

This document is a review candidate only. Implementation of shared settlement must wait for
independent ACR ratification.

## 2. Non-goals (current tip)

- Do not replace per-patient desk checkout.
- Do not allow one receipt to allocate across patients in the live synthetic stack.
- Do not invent family accounts or persistent family relationships as a prerequisite.
- Do not enable CARD_TO_CARD / ONLINE live verification.

## 3. Current frozen guards (must remain until ratification)

1. Invoice `beneficiary_patient_id` is singular and immutable after draft creation.
2. Receipt allocations reference one invoice's lines; cross-patient allocation is rejected.
3. Desk checkout creates one invoice per patient checkout intent.
4. Multi-patient cart UI settles each slot independently (`FEATURE_FLAGS.multiPatientSharedSettlement = false`).

## 4. Proposed settlement-batch aggregate (future)

### 4.1 Identity

- `settlement_batch_id` (UUIDv7), tenant-scoped
- `created_by_user_id`, `department_id`, `created_at_utc`
- `status`: `OPEN | LOCKED | POSTED | PARTIALLY_FAILED | VOIDED`
- `external_evidence_kind` + `external_evidence_ref` (unique per tenant when present)
- `idempotency_key` (principal-scoped, durable)

### 4.2 Members

Each member is an independently valid invoice intent:

- `beneficiary_patient_id`
- `invoice_id` (nullable until created)
- `expected_patient_payable_irr`
- `allocated_irr`
- `member_status`: `PENDING | INVOICED | ALLOCATED | FAILED | SKIPPED`

Conservation: `sum(member.allocated_irr) + unapplied_batch_credit_irr + unresolved_irr = received_irr`.

### 4.3 Unique external evidence

- When a POS/card slip / bank reference is attached, `(tenant_id, external_evidence_kind, external_evidence_ref)` is UNIQUE.
- Duplicate evidence on a second batch is rejected (`duplicate_external_evidence`).
- Reprinting a receipt does not create new external evidence.

## 5. Idempotency and concurrency

- Batch creation and posting use durable idempotency keys (UUID, not truncated composites).
- Same key + same payload → replay original result.
- Same key + different payload → `idempotency_conflict`.
- Concurrent posts take a row lock on `settlement_batches` (`SELECT … FOR UPDATE`).
- Member invoice creation is ordered by `beneficiary_patient_id` to avoid deadlock.

## 6. Beneficiary isolation and privacy

- Operators see only patients/invoices within their object scopes (ALL/FILTER).
- Batch listing never leaks out-of-scope member rows (filter before pagination).
- Print exports emit independent patient receipts; shared batch metadata is staff-only.
- Error messages do not disclose other beneficiaries' identifiers across scope boundaries.

## 7. Partial failure

- If member N fails after members 1…N-1 succeeded:
  - Batch status → `PARTIALLY_FAILED`
  - Successful member invoices remain posted (no silent rollback of money facts)
  - Recovery UI lists failed members with retry-safe intents
- Voiding a batch never deletes verified receipts; it appends compensating adjustments under authority.

## 8. Credit, refunds, and adjustments

- Unapplied overpayment becomes `patient_credit` attributed to an explicit beneficiary
  (or `batch_unapplied_credit` holding account requiring manager resolution) — policy choice
  must be ratified; default proposal: require explicit beneficiary for any credit.
- Refunds target original receipt allocations; cross-beneficiary refund from shared inflow
  requires documented allocation lineage.
- Historical verified receipt amounts are never mutated; corrections are append-only.

## 9. Audit and recovery

- Append audit events: `settlement_batch.created|locked|posted|member_failed|voided|reprinted`.
- Recovery query by `idempotency_key` or `external_evidence_ref` returns authoritative batch state.
- Timeout/unknown-result clients must reconcile via GET before creating a new batch.

## 10. Duplicate receipt prevention

- Print jobs reference immutable invoice snapshots; reprint does not re-run checkout.
- Batch print creates one print job per beneficiary receipt + optional staff batch summary.
- Failed/unknown print jobs are recoverable without financial mutation.

## 11. Activation gate

Shared settlement may be enabled only after:

1. Owner/independent review of this candidate (complete, unabridged).
2. Disposable PG15 implementation + adversarial multi-user tests.
3. Explicit ACR ratification amending ACR-D0.11.
4. Feature flag flip under synthetic preview only.

Until then: `multiPatientSharedSettlement = false`.

## 12. Unresolved items

- Attribution of batch-level unapplied credit when operator cannot choose a beneficiary.
- Interaction with prepaid course entitlements (also ratification-gated).
- Live provider evidence schemas for CARD_TO_CARD / ONLINE.
