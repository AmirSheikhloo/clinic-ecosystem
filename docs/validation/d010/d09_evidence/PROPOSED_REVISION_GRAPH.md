# Proposed Tenant Plane revision dependency graph (LOGICAL — for PO approval)

**Status:** PROPOSED ONLY. No official Alembic files. Do not invent landed `tp0008+` numbers.

## Protected facts

| Item | Rule |
|------|------|
| Existing head | `tp0001 → … → tp0007` (frozen; do not modify) |
| TP0011 | **PROTECT** — HMAC Phase-6 / atomic-resource lane only; zero ops tables |
| TP0020–TP0021 | Preserve CMS/Portal/CSAT |
| F2-B | Experimental / TERMINAL FAILED E0.7 — not authorized |
| Official IDs | Assigned by PO after approved roadmap reconciliation |

## Logical package graph (edges = schema dependencies)

```
tp0007 (existing head)
  └─ L1 Identity/KMS/versioned permissions          [reconcile TP0008–TP0010; SOURCE]
  └─ L2 TP0011 atomic/HMAC lane                     [PROTECTED — parallel, not ops parent]
  └─ OPS-A  staff_practitioner_resources + staff_service_links + departments (+ links)
       ├─ OPS-B  role_permission_scopes + notes/tags + identity_reviews
       ├─ OPS-C  reception/visits/arrival/service_records/historical + waitlist + online_close
       │    └─ OPS-D  billable_items + cashier + instruments + invoices/receipts/refunds
       │         (+ Appendix B guards/triggers) + insurer/revenue-share tables (fail-closed advanced)
       │         └─ OPS-E  optional MOD_INVENTORY FEFO ledger
       └─ OPS-F  person_merge_events                 [BLOCKED until v1.3]
  └─ SYNC envelope reconciliation                   [reconcile TP0014; Gate A multi-node]
  └─ Notifications / reminder suppression           [reconcile TP0018]
```

## Candidate roadmap alignment (R4.16 — unapproved)

| Logical | Candidate slots (not assigned) |
|---------|--------------------------------|
| OPS-A / OPS-B | After Package-1; do not use TP0011 |
| OPS-C (arrival/waitlist/closure) | ~TP0012–TP0013 family |
| OPS-D finance | ~TP0015–TP0017 family |
| OPS-E inventory | ~TP0019 |
| Merge | Requires v1.3 + approved lineage — never TP0020–21 |

## Approval ask

PO assigns concrete revision IDs and `down_revision` parents matching an **approved** successor roadmap, preserving TP0011 and TP0020–21, then checks ACR-D0.9 §13 boxes per package.
