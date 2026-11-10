# Gate A M0 Bootstrap — Consolidated Report

**Authoritative specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`  
**Pull Request:** https://github.com/AmirSheikhloo/clinic-ecosystem/pull/1 (do not merge)

## Milestone results

| Milestone | Result | Notes |
|---|---|---|
| **M0-A** | **COMPLETE** | Legacy inventory NOT ACCESSIBLE; authorization recorded. |
| **M0-B** | **PENDING CI REVIEW** | Final security remediation applied; await green expanded suite. |
| **M0-C** | **PENDING CI REVIEW** | `alembic_meta` isolation + migrator path; await green CI. |

Do **not** treat M0-B/C as ACCEPTED until the post-remediation GitHub Actions evidence is reviewed.

## Final security remediation (this change set)

- Alembic version tables in private schema `alembic_meta` (online + offline `version_table_schema`)
- Fixed plane migrator `SET ROLE` (no env override)
- Removed Control Plane `CREATE ON DATABASE`; retained Tenant/Local Hub CREATE for `btree_gist`
- Alembic test runner no longer mutates `os.environ`
- Expanded role-attribute / privilege / metadata-isolation tests across all three DBs
- CI collect step uses Bash `pipefail`; evidence guard fails on any JUnit failure/error

## Unresolved / deferred

1. UUIDv7 provider
2. Legacy source access
3. Backup/restore identities (**E.1.7** — explicitly deferred; not implemented)
4. Agent Docker unavailable (CI is evidence path)

## Exact next step

Review GitHub Actions for this remediation commit. Accept M0-B/C only after green evidence. Do not merge without separate approval.
