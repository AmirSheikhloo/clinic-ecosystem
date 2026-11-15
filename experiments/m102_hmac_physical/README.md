# M1-02 experimental HMAC physical probes (P1 vs P2)

**Classification:** `EXPERIMENTAL / NOT APPROVED / NOT Package-1 / NOT official TP0008+`

Disposable PostgreSQL 15 probes comparing:

- **P1** — staged gen2/gen3 columns on `person_identifiers`
- **P2** — generation-aware sidecar with parent identity binding + ACTIVE uniqueness

## Safety corrections (N01–N09)

This package includes fail-closed guards for:

- Active-generation index/value wipe refusal (N01)
- P2 ACTIVE partial unique index + person/type/authority parent consistency (N02/N03)
- Mandatory observed Lock/LWLock two-session barrier (N04)
- Evidence-bound phase transitions (N05)
- Exact index catalog assert + real-target invalid index recovery (N06)
- Atomic dual-write / resumable backfill / two complete rotations (N07)

Synthetic digests only (`synthetic_hmac.py`). No production keys, no patient data, no merge to `main`.
