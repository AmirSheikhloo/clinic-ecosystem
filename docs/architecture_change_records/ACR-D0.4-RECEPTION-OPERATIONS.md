# ACR-D0.4 — Reception operations remaining contracts (PROPOSAL ONLY)

Status: **PROPOSED — not approved.** Task 26 / D0.4 on `development/clinic-operations`.
Tenant migration lineage remains `tp0001`–`tp0007`. No gate closure claimed.

## Implemented without new architecture

* Appointment lifecycle transitions on existing status CHECK values (CONFIRMED → CHECKED_IN → COMPLETED; NO_SHOW rules).
* List-first appointment management + management/upcoming read model.
* National ID syntactic validation (normalize + checksum) and Clause 755 exceptional reason (validated, **not** ciphertext-stored).
* Multi-service reception desk with non-posted tariff preview; each service retains independent appointment identity.
* Windows preview Docker readiness and gitignored runtime preview files.

## Remaining decisions (consolidated)

| # | Topic | Authoritative source | Incompatibility | Proposed resolution | Migration | Security / concurrency | Acceptance tests | PO approval needed |
|---|-------|---------------------|-----------------|---------------------|-----------|------------------------|------------------|--------------------|
| 1 | Official identifier ciphertext + blind-index lookup | Spec §52 / F.2 `person_identifiers` | App lacks KMS/DEK + HMAC lifecycle wiring | Implement sealed box + domain-separated HMAC; refuse plaintext; exact lookup API | None if F.2 sufficient; key versioning ops runbook | Never log plaintext; tenant isolation | Duplicate ID denied; exact lookup; rotate keys | Approve test-key policy for non-prod |
| 2 | Shared family phones | Spec person_phones | No panel phone write/search | Encrypt phones; search returns distinct persons; never unique-on-phone | None if F.2 sufficient | Blind index; no silent merge | Two patients same mobile selectable | Confirm UX |
| 3 | Section 50 ledger (invoice/receipt/discount/refund) | Spec Section 50 | No DDL in approved lineage | Approve ledger tables + IRR integer math + immutable posted facts | New TP migration after approval | Idempotent financial ops; refund caps | Discount/refund E2E matrix | Approve schema packet |
| 4 | Inventory optional module | Spec inventory | Entitlement + stock movement tables not in lineage | Optional module flag; FEFO movements immutable | New TP migration | No stock edit; no pharmacy | Future booking ≠ consumption | Approve entitlement |
| 5 | Scope table for scoped receptionist | ACR-BETA02-001 §3.1 | No scope rows | `role_permission_scopes` + server enforcement on all reads/writes | New TP migration | Fail-closed | Out-of-scope 403 on list/metrics/mutation | Approve scope kinds |
| 6 | Staff–service eligibility | Product multi-skill practitioner | No link table; resources used today | `staff_service_links` + filter eligible practitioners | New TP migration | Tenant RLS | Changing service clears incompatible staff | Approve link model |
| 7 | Historical late entry | Product §13 | Recording vs occurrence timestamps | Dedicated audited workflow; suppress reminders | Possibly audit-only | Immutable audit time | Past entry does not trigger reminders | Approve reason codes |
| 8 | Atomic grouped booking UoW | Product §10.4 | Handler commits per appointment | GroupScheduleHandler single UoW + group idempotency | None | All-or-nothing local group | 3-service atomicity / retry | Approve semantics vs sequential PARTIAL |

## Anti-patterns rejected

Fake finance screens, fabricated National IDs, client-only scope filters, editing stock balances, claiming gate closure.
