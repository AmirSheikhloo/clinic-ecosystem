# M1-02 P1/P2 HMAC physical experiment (NONPRODUCTION)

**Status:** `EXPERIMENTAL / PROPOSED / NOT APPROVED / NOT Package-1`

This package applies **scratch DDL at runtime** inside disposable PostgreSQL 15
Testcontainers. It does **not** add official `TP0008+` Alembic revisions and must
not be merged as production migration code.

## Models under test

- **P1** — additive staged generation columns on `person_identifiers`
  (`exp_lookup_hmac_gen2` / `gen3`) with nonredundant concurrent unique indexes.
- **P2** — generation-aware sidecar table `person_identifier_hmac_generations_exp`
  with status-scoped unique indexes and FORCE RLS.

## Explicitly out of scope

- Production auth/API/key-management services
- Official ACR/ADR approval
- Gate A/B/C/D acceptance
- Real patient data / production keys / persistent target DBs
- Modification of frozen `FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` or R4.12
