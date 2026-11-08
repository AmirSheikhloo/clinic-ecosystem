# Agent runtime evidence — Gate A M0

**Specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`  
**PO scope name:** `gate-a/m0-bootstrap`

## Python (Agent execution environment)

- **Version:** 3.12.3  
- **Full:** `3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`  
- Measured in the Agent environment; not assumed from a developer machine.

## Docker (Agent execution environment)

- **Availability:** **NOT AVAILABLE** (`docker: command not found`)
- Measured in the Agent environment at execution time.
- PostgreSQL 15 Testcontainers therefore cannot start.

## Required PostgreSQL integration tests

| Suite | Result | Notes |
|---|---|---|
| `tests/integration/test_plane_isolation.py` | **NOT RUN** | Skipped: Docker unavailable |
| `tests/integration/test_tp0001_migration.py` | **NOT RUN** | Skipped: Docker unavailable |
| `tests/unit/test_tp0001_verbatim_sql.py` | Runnable without Docker | Static verbatim F.2 check only; does not accept M0-B/C |

## Milestone acceptance implication

- **M0-B:** implementation files present; status **NOT ACCEPTED** (required isolation tests NOT RUN).
- **M0-C:** migration files present; status **NOT ACCEPTED** (required migration tests NOT RUN).

## Exact blocker

Docker CLI/daemon is not available in the Agent execution environment, so real PostgreSQL 15 Testcontainers cannot run.
