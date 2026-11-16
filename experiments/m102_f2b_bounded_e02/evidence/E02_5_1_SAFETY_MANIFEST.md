# E0.2 §5.1 safety manifest (pre-execution)

**Contract SHA-256:** `03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31`  
**Base:** `fdae362e1a889831975060808ac612369d3b0d0a`  
**Branch:** `experiment/m102-f2b-e02-20261116-fdae362`

| ID | Status | Notes |
|---|---|---|
| E02-5.1-A | PASS | PO approval + digest match |
| E02-5.1-B | PASS | Frozen spec clauses 771–772; R4.15 §§11.8–11.9 REVIEW CANDIDATE (upload) |
| E02-5.1-C | PASS | Clean tree; origin/main=`fdae362…`; TP0001–TP0007 only |
| E02-5.1-D | PASS | Write paths limited to `experiments/m102_f2b_bounded_e02/**` + conditional workflow |
| E02-5.1-E | PASS* | Clock OK; local Docker ABSENT; CI disposable `postgres:15` service used instead |

\* Local daemon unavailable; isolation via GitHub Actions service container only.

## §5.2 path map

| Test ID | Write paths | PG boundary |
|---|---|---|
| E02-F2B-01..14 | `experiments/m102_f2b_bounded_e02/tests/**`, `evidence/**` | disposable PG15; roles `exp_f2b_migrator` / `exp_f2b_app` |
