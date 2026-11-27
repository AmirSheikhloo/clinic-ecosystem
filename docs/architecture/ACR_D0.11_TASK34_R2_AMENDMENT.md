# ACR amendment candidate — Task 34 R2 (PROPOSED, not ratified)

**Status:** PROPOSED for independent ChatGPT/Gemini review and owner ratification.  
**Scope:** Multi-patient temporary cart settlement attribution; treatment-course / rolling-recall disposable contracts; thermal print job identity.  
**Does not:** Land official Alembic TP0008+, weaken one-beneficiary invoice guards, activate live CARD_TO_CARD/ONLINE, or claim Gate B/C/D.

## 1. Multi-patient shared settlement (MULTI-02)

Inspected ACR-D0.11 enforces one beneficiary per invoice and matching receipt beneficiary on allocation. Cross-patient allocation is **not** authorized by the frozen contract.

### Proposed narrow contract (feature flag `CLINIC_MULTI_PATIENT_SETTLEMENT=off` by default)

1. Keep one immutable invoice per patient beneficiary.
2. Introduce `settlement_batches` (tenant-scoped) representing one verified external inflow exactly once (synthetic POS/CASH evidence).
3. Introduce `settlement_batch_attributions` mapping exact IRR sub-amounts to each beneficiary invoice/receipt without cross-credit.
4. Conservation: sum(attributions) == batch.amount_irr; reject unspecified beneficiary; reject over-allocation under concurrent locks.
5. Refunds remain per original receipt/line; sibling patients unchanged.

Until ratified and disposable PG15 races pass, UI may collect multi-patient drafts but must settle as **separate** invoices/receipts or unpaid — never weaken existing guards.

## 2. Treatment courses + rolling recall (COURSE / RECALL)

Disposable tables (ops schema only): `treatment_course_templates`, `treatment_courses`, `treatment_course_sessions`, `treatment_recall_schedules`, `notification_outbox_synthetic`.

- Clinical completion count from PERFORMED service records only.
- Rolling next suggested date from actual completion Tehran local date + versioned interval.
- Synthetic notification sink only; no real SMS/bot.

## 3. Print jobs (PRINT)

`print_jobs` separate from checkout idempotency. Statuses: QUEUED / SPOOLED / FAILED / UNKNOWN. Reprint never re-runs finance. Simulated adapter in preview; QZ signing private key server-side only when hardware path approved.

## Unresolved

- Owner ratification of settlement batch model.
- Clinical interval policy ownership.
- Legal/commercial prepaid forfeiture (PREPAY remain fail-closed).
- Physical printer evidence.
