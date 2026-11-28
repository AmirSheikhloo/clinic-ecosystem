# Proposed official Tenant Plane migration graph (Task 34)

**Governance:** PROPOSED ONLY. Do not land until Product Owner allocates official revision IDs and ratifies ACR-D0.11/D0.12.  
**Current official head on disk:** `tp0007`  
**Protected:** `TP0011` reserved; F2 topology constraints preserved; TP0001–TP0007 history immutable.

## Linear sequence (proposed labels → pending official IDs)

| Order | Proposed package id | SQL sources (ACR-D0.9 extract) | Depends on | Notes |
|------:|---------------------|--------------------------------|------------|-------|
| 1 | TP-OPS-ELIGIBILITY | `05.sql` | tp0007 | staff_practitioner_resources, staff_service_links |
| 2 | TP-OPS-DEPARTMENTS | `06.sql` | TP-OPS-ELIGIBILITY | departments + appointment.department_id |
| 3 | TP-OPS-SCOPES | `07.sql` | tp0007 | role_permission_scopes |
| 4 | TP-OPS-NOTES | `10.sql` | tp0007 | patient operational notes/tags |
| 5 | TP-OPS-IDENTITY-REVIEWS | `11.sql` | tp0007 | identity review queue |
| 6 | TP-OPS-ARRIVAL | `08.sql` | TP-OPS-DEPARTMENTS | reception_groups, visits, arrival_facts, service_records |
| 7 | TP-OPS-WAITLIST | `04.sql` | TP-OPS-ARRIVAL | waitlist; needs appointment patient/service UQs from arrival |
| 8 | TP-OPS-ONLINE-CLOSE | `09.sql` | TP-OPS-ELIGIBILITY | online_availability_closures |
| 9 | TP-OPS-LEDGER | `00.sql`, `01.sql`, `02.sql` | TP-OPS-ARRIVAL, TP-OPS-DEPARTMENTS | invoice/receipt/refund core |
| 10 | TP-OPS-RECEIPT-GUARDS | `15.sql` | TP-OPS-LEDGER | ledger_receipt_guards |
| 11 | TP-OPS-INVOICE-GUARDS | `14.sql` | TP-OPS-LEDGER | invoice posting guards |
| 12 | TP-OPS-INVENTORY | `03.sql` | TP-OPS-LEDGER, TP-OPS-ARRIVAL | inventory + FEFO movements |
| 13 | TP-OPS-CROSSROW | `16.sql` | TP-OPS-INVENTORY, TP-OPS-RECEIPT-GUARDS | Appendix B.3 triggers |
| 14 | TP-OPS-MISC-GUARDS | `17.sql` | TP-OPS-CROSSROW | Appendix B.4 |
| 15 | TP-OPS-RLS | `13.sql` | all above | Appendix A; requires `app.ops_migration_tables` |
| — | TP-OPS-PERSON-MERGE | `12.sql` | SOURCE_REQUIRED | **BLOCKED** — canonical merge stays disabled |

## Exact dependency edges

```
tp0007
  ├─ TP-OPS-ELIGIBILITY ─┬─ TP-OPS-DEPARTMENTS ─┬─ TP-OPS-ARRIVAL ─┬─ TP-OPS-WAITLIST
  │                      │                     │                 └─ TP-OPS-LEDGER ─┬─ TP-OPS-RECEIPT-GUARDS ─┐
  │                      │                     │                                  ├─ TP-OPS-INVOICE-GUARDS ─┤
  │                      │                     └──────────────────────────────────┴─ TP-OPS-INVENTORY ──────┼─ TP-OPS-CROSSROW ─ TP-OPS-MISC-GUARDS ─ TP-OPS-RLS
  │                      └─ TP-OPS-ONLINE-CLOSE
  ├─ TP-OPS-SCOPES
  ├─ TP-OPS-NOTES
  └─ TP-OPS-IDENTITY-REVIEWS
```

## Remaining ratification decisions (blockers for official landing)

1. Allocate official Alembic revision IDs without colliding with `TP0011` or reserved F2 slots.
2. Confirm whether scopes/notes/identity packages share a single revision or stay atomic packages.
3. Confirm inventory FEFO + write-off pairing acceptance as Package 4 vs Gate C evidence.
4. Explicit PO decision that disposable Testcontainers evidence is sufficient to open official migration PR (separate from this PR).
5. Confirm head-receptionist permission code naming for production catalog (currently `BETA02_HEAD_RECEPTIONIST` provisional).

## Disposable preview (this PR)

- Harness: `CLINIC_OPS_SCHEMA_MODE=disposable` via `tests/e2e/beta01b/stack.py` / `scripts/start_preview.ps1`.
- Does **not** mutate any baseline/preview database outside the disposable container.
- Windows: `powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1` (add `-NoBrowser` for CI).
