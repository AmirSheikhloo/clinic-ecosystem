# Gate A M0 Bootstrap — Consolidated Report

**Authoritative specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`  
**PO scope name:** `gate-a/m0-bootstrap`  
**Pull Request:** https://github.com/AmirSheikhloo/clinic-ecosystem/pull/1 (target `main`; do not merge)

## Milestone results

| Milestone | Result | Notes |
|---|---|---|
| **M0-A** | **COMPLETE** | Legacy inventory recorded as **NOT ACCESSIBLE**; authorization file committed. |
| **M0-B** | **ACCEPTED** | Required plane-isolation tests **PASS** on GitHub Actions (`ubuntu-24.04`) with real PostgreSQL 15 Testcontainers (two containers / three logical DBs). |
| **M0-C** | **ACCEPTED** | Required TP0001 migration tests **PASS** on the same CI evidence (Cloud Tenant + Local Hub independently; CP baseline separate). |

## Agent environment

- **Python:** 3.12.3 (`3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`)
- **Docker:** **NOT AVAILABLE** in the Cursor Cloud Agent (`docker: command not found`)
- Evidence path for M0-B/C: GitHub Actions workflow `.github/workflows/m0-postgres-integration.yml`

## CI evidence (accepting run)

- **Workflow run (push):** https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/42536959128
- **PR run:** https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/42536963085
- **Commit:** `2f5831c4ff33abca7247088604c230514ecd05f3`
- **CI Python:** 3.12.16
- **Docker:** verified via `docker version` / `docker info` on the runner
- **Pytest:** **12 passed**, **0 skipped**, **0 failed**
  - unit: 2 PASS
  - plane isolation: 6 PASS
  - TP0001 migration: 4 PASS
- Skip guard: `assert_m0_pytest_evidence.py` reported OK (12 required tests; 0 required skips)

## Delivered artifacts

- `docs/records/GATE_A_AUTHORIZATION_M0.md`
- `docs/inventory/M0A_LEGACY_INVENTORY.md`
- `docs/records/UNRESOLVED_RUNTIME_UUIDV7.md`
- `docs/records/AGENT_RUNTIME_EVIDENCE.md`
- `.github/workflows/m0-postgres-integration.yml`
- `pyproject.toml` (pytest, testcontainers, alembic, asyncpg, httpx, sqlalchemy for Alembic)
- `ops/db_bootstrap/cloud_roles.sql` / `local_hub_roles.sql` (no secrets)
- `migrations/tenant_plane/` including **TP0001** verbatim F.2 `tenant_registry` + `btree_gist`
- `migrations/control_plane/` baseline `cp0000` (no CP0001 business DDL); version table `alembic_version_cp`
- `tests/integration/` two-container topology + isolation + migration tests

## Deviations

- TP0001 executes the two verbatim F.2 statements via separate `op.execute` calls (asyncpg cannot prepare multi-command statements). SQL text remains identical to Appendix F.2.

## Unresolved decisions

1. UUIDv7 provider (Agent Python 3.12.3; stdlib uuid7 needs 3.14+)
2. Legacy source access (blocks business module rewrites only)
3. Agent Docker remains unavailable (CI is the evidence path; not a remaining M0-B/C blocker)

## Exact next step

Review PR #1. **Do not merge** until Product Owner/reviewer approval. No further M0-B/C test evidence is required for acceptance.
