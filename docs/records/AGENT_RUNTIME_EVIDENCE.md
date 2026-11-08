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
- PostgreSQL 15 Testcontainers therefore cannot start **in the Agent**.

## CI evidence path (accepting)

- Workflow: `.github/workflows/m0-postgres-integration.yml`
- Runner: GitHub-hosted `ubuntu-24.04`
- Accepting push run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/42536959128
- Commit: `2f5831c4ff33abca7247088604c230514ecd05f3`
- CI Python: 3.12.16
- Result: **12 passed, 0 skipped, 0 failed**

## Required PostgreSQL integration tests

| Suite | Agent | CI (accepting run) |
|---|---|---|
| `tests/integration/test_plane_isolation.py` | NOT RUN (no Docker) | **PASS** (6) |
| `tests/integration/test_tp0001_migration.py` | NOT RUN (no Docker) | **PASS** (4) |
| `tests/unit/test_tp0001_verbatim_sql.py` | **PASS** (2) | **PASS** (2) |

## Milestone acceptance implication

- **M0-B:** **ACCEPTED** on CI evidence (plane isolation PASS; 0 skips).
- **M0-C:** **ACCEPTED** on CI evidence (TP0001 migration PASS; 0 skips).
