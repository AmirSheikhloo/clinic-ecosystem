# ACR-D0.5 — Implementation-ready decision packet (Category C)

Status: **PROPOSAL ONLY — not approved. Do not execute migrations.**  
Branch: `development/clinic-operations`. Lineage remains `tp0001`–`tp0007`.

## Classification

| Capability | Class | Evidence |
|------------|-------|----------|
| Encrypted National ID / phone persist+lookup | **A** — existing F.2 tables | `person_identifiers`, `person_phones` in TP0002 |
| Atomic group booking | **A** — application UoW | appointments + allocations exist |
| Waiting room as CHECKED_IN read model | **A** | status already in appointments CHECK |
| Section 50 invoices/receipts/refunds | **C** — no DDL in lineage or Appendix F.2 CREATE TABLE | Spec clauses 692–739 conceptual; no approved TP migration |
| Inventory / stock movements | **C** | No tables in tp0001–tp0007 |
| Future-slot waitlist entity | **C** | No waitlist table |
| Staff↔service eligibility links | **C** | No link table; resources≠practitioners |
| Scoped receptionist scope rows | **C** | ACR-BETA02-001 §3.1 |

## Proposed next migrations (DO NOT LAND without PO approval)

Suggested allocation after explicit Product Owner ratification (names illustrative only — **not invented as official numbers until approved**):

1. **Ledger foundations** — draft/posted invoices, lines with tariff snapshots, receipts, allocations, adjustments, refunds; integer IRR; RLS; permissions.  
2. **Inventory optional module** — items, lots, immutable movements, FEFO; entitlement flag.  
3. **Waitlist** — future-slot requests distinct from CHECKED_IN waiting.  
4. **staff_service_links** — multi-skill practitioner eligibility.  
5. **role_permission_scopes** — scoped receptionist enforcement.

Exact DDL, dependency order, RLS policies, permission codes, concurrency tests and acceptance scenarios must be ratified in a follow-up ACR before any Alembic revision is added to the repository.

## PO approval required

Approve or reject each Category C item above; assign official TP revision IDs; confirm non-production PII key policy for demo/test (`CLINIC_PII_*`).
