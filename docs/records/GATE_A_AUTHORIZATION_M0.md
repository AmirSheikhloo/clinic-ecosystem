# Gate A Authorization — M0 Bootstrap

**Status:** AUTHORIZED (Product Owner written initiation recorded)  
**Date recorded:** 2026-11-08  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`  
**Product Owner authorized scope name:** `gate-a/m0-bootstrap`

## Authoritative specification

- `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`
- Historical baseline retained: `docs/FINAL_MASTER_SPECIFICATION_v3.0_FINAL.txt`

## Authorized milestones

- **M0-A** — Legacy source inventory
- **M0-B** — Development infrastructure and PostgreSQL bootstrap
- **M0-C** — TP0001 Tenant Root migration

## Explicitly prohibited

- Production deployment
- Real patient data processing
- Live payments
- Customer-facing activation
- Production databases or migrations
- Business module implementation outside M0
- Invented CP0001 business DDL
- Premature RLS / TP0002+
- Gate B, C, or D activities
- Merging the feature branch into `main` without separate review/approval beyond this M0 delivery PR

## Agent environment (measured at execution)

- **Python version:** 3.12.3 (CPython; `3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`)
- **Docker availability:** **NOT AVAILABLE** (`docker: command not found` in the Agent execution environment)

## Unresolved items

1. **UUIDv7 provider** — application-level UUIDv7 is required by the specification; Python stdlib `uuid.uuid7()` requires Python 3.14+. Agent Python is 3.12.3. No provider selected in M0.
2. **Docker availability in the Agent** — required PostgreSQL Testcontainers evidence depends on Docker in this environment.
3. **Legacy source access** — NOT ACCESSIBLE in this repository; see `docs/inventory/M0A_LEGACY_INVENTORY.md`.

## Notes

This document records Product Owner Gate A initiation limited to M0-A / M0-B / M0-C. It is not Production authorization and does not close any of the 14 Open Items in clause 833.
