# ACR-D0.12 — Task 34 Integrated Four-Workspace Implementation Notes

**Status: PROPOSED IMPLEMENTATION INCREMENT (DISPOSABLE / SYNTHETIC).**  
Not approved for official Alembic landing, merge to production, live data, or live payments.

**Baseline tip:** `8309f2a044e944123ddb1f49a8bad1255e4ce2e0`  
**Architecture validation tip:** `8c2d3774b6c748ad69aea8fed0f3417e7baa785c` (ACR-D0.11)  
**Branch:** `cursor/d010-ops-contracts-validation-95a4` (PR #10 → `development/clinic-operations`)

## What this increment adds

1. Disposable ops schema applicator (`clinic_ecosystem.infrastructure.ops_schema`) applying ACR-D0.9/D0.11 SQL after tp0007 when `CLINIC_OPS_SCHEMA_MODE=disposable`.
2. Application APIs: `/api/v1/finance/*`, `/api/v1/waitlist/*`, `/api/v1/ops/*`.
3. Check-in writer adopts arrival facts when ops schema is present.
4. Demo seed expansion for invoices, waitlist, inventory, eligibility, departments (valid contracts only).
5. Frontend workspaces: finance, waitlist, ops config; dashboard wait/finance metrics.
6. Concurrent refund acceptance strengthened to require exactly one success + competing rejection.
7. Paired inventory write-off coverage added to deep suite.

## Preserved invariants

- TP0001–TP0007 history unchanged; no official tp0008+ landed.
- Canonical patient merge remains disabled (package 12 skipped).
- Live payment adapters, insurer settlement, revenue-share, KMS, SRC-10 remain blocked.
- Gates A–D and Package 1 / Package 4 boundaries remain distinct.

## Contract deltas vs ACR-D0.11

No DDL contract changes. Application adoption of existing proposed tables only. If official revision allocation remains unresolved, official migration landing stays blocked; disposable development continues.

## Remaining ratification decisions

See `docs/validation/d010/proposed/OFFICIAL_MIGRATION_GRAPH.md`.
