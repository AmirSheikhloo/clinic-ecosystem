# ACR amendment candidate — Task 34 R2 (PROPOSED, not ratified)

**Status:** PROPOSED for independent ChatGPT/Gemini review and owner ratification.  
**Scope:** Multi-patient temporary cart settlement attribution; treatment-course / rolling-recall disposable contracts; thermal print job identity.  
**Does not:** Land official Alembic TP0008+, weaken one-beneficiary invoice guards, activate live CARD_TO_CARD/ONLINE, or claim Gate B/C/D.

## 1. Multi-patient shared settlement (MULTI-02)

Inspected ACR-D0.11 enforces one beneficiary per invoice and matching receipt beneficiary on allocation. Cross-patient allocation is **not** authorized by the frozen contract.

**Authoritative review candidate (unabridged):**  
`docs/architecture/ACR_D0.12_SETTLEMENT_BATCH_ATTRIBUTION_CANDIDATE.md`

That document covers conservation, unique external evidence, idempotency, beneficiary isolation, locks, partial failure, credit, refunds, privacy, audit, recovery, and duplicate receipt prevention. Shared settlement remains **DISABLED** (`CLINIC_MULTI_PATIENT_SETTLEMENT=off`) until ratified. Do **not** weaken one-beneficiary invoice/receipt guards.

### Interim product behavior (flag off)

1. Keep one immutable invoice per patient beneficiary.
2. UI may collect multi-patient drafts but must settle as **separate** invoices/receipts or unpaid.
3. Batch **printing** of independent receipts is allowed without shared settlement.
4. `settlement_batches` / attributions must not be written while the flag is off.

## 2. Treatment courses + rolling recall (COURSE / RECALL)

Disposable tables (ops schema only): `treatment_course_templates`, `treatment_courses`, `treatment_course_sessions`, `treatment_recall_schedules`, `notification_outbox_synthetic`.

- Clinical completion count from PERFORMED service records only.
- Rolling next suggested date from actual completion Tehran local date + versioned interval.
- Synthetic notification sink only; no real SMS/bot.

## 3. Print jobs (PRINT)

`thermal_print_jobs` separate from checkout idempotency. Statuses: QUEUED / SPOOLED / FAILED / UNKNOWN / CANCELLED. Reprint never re-runs finance. Simulated adapter in preview; QZ signing private key server-side only when hardware path approved. Proposed SQL: `docs/validation/d010/d09_extracted/proposed_print_jobs.sql`. Snapshot API: `GET /api/v1/finance/invoices/{id}/print-snapshot`.

## Unresolved

- Owner ratification of settlement batch model (see ACR-D0.12 candidate §21).
- Clinical interval policy ownership.
- Legal/commercial prepaid forfeiture (PREPAY remain fail-closed).
- Physical printer evidence.
