# Gate A M0 Bootstrap — Consolidated Report

**Authoritative specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`  
**PO scope name:** `gate-a/m0-bootstrap`  
**Pull Request:** https://github.com/AmirSheikhloo/clinic-ecosystem/pull/1 (target `main`; do not merge)

## Milestone results

| Milestone | Result | Notes |
|---|---|---|
| **M0-A** | **COMPLETE** | Legacy inventory **NOT ACCESSIBLE**; authorization recorded. |
| **M0-B** | **PENDING CI RE-ACCEPTANCE** | Appendix E privilege/membership/CONNECT remediations landed; prior CI green is superseded until new suite passes. |
| **M0-C** | **PENDING CI RE-ACCEPTANCE** | Migrator-login TP0001 path + E.3/E.4 remediations landed; await green CI. |

> Status above is updated to ACCEPTED only after the post-remediation GitHub Actions suite passes with 0 skips. See AGENT_RUNTIME_EVIDENCE.md for the accepting run once available.

## Remediation vs prior suite

### Previously passing (retained; still required)

- Unit F.2 verbatim checks (2)
- Plane CONNECT denials for runtime logins (2)
- Same-plane CONNECT allowed (1)
- PUBLIC CONNECT/TEMPORARY revoked (1)
- Local Hub role-name reuse (1)
- TP0001 applies to Cloud Tenant + Local Hub (1)
- Invalid status CHECK (1)
- TP0001 does not mutate CP DB (1)
- Separate Alembic version tables (1)

### Newly added security / ownership / policy tests

- Migrator cross-plane CONNECT denials + assigned-DB CONNECT matrix + Local Hub login CONNECT
- `pg_has_role` direct/transitive membership (Cloud + Local Hub)
- Runtime cannot `SET ROLE` to migrator or other-plane runtime; migrators assume only own migrator; Local Hub SET ROLE boundaries
- Runtime lacks SUPERUSER/BYPASSRLS; schema USAGE without CREATE; DML without TRUNCATE; no DDL; default privileges exclude PUBLIC/other plane
- TP0001 / Alembic version-table ownership by `db_migrator`
- Unit: TP0001 downgrade irreversible (E.4); CP0000 revision file absent (E.3 `ensure_version`)

## Agent environment

- **Python:** 3.12.3
- **Docker:** NOT AVAILABLE in Cursor Cloud Agent (CI is evidence path)

## Unresolved decisions

1. UUIDv7 provider (Python 3.12.3; stdlib uuid7 needs 3.14+)
2. Legacy source access (blocks business module rewrites only)
3. Backup/restore identities (E.1.7) — out of M0 executable scope; not claimed

## Exact next step

Wait for GitHub Actions on this remediation commit; accept M0-B/M0-C only on green evidence with 0 required skips. Do not merge PR #1 without separate approval.
