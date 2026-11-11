# M1-01 Open decisions / non-invention log

| ID | Topic | Resolution in this PR | Residual risk |
|---|---|---|---|
| OD-1 | RBAC table DDL (no Appendix F SQL) | Minimum tables in TP0003 sufficient for `ALLOW_MANUAL_OVERBOOKING` via role→permission→user assignment | Broader RBAC catalog sync/Cloud authority UI deferred |
| OD-2 | Appointment/allocation status CHECKs | F.4 leaves status unconstrained; application uses clause 781 enum values | Optional DB CHECK can be added in a later revision if PO freezes DDL |
| OD-3 | Idempotency/Outbox/Inbox/Audit DDL | Minimum columns implementing clauses 171–184 / 213–231 / 779 | Lease reclaim workers beyond HoldExpirationWorker / Outbox delivery TX2 network path deferred |
| OD-4 | RFC8785 JCS | **Resolved:** `rfc8785==0.1.4` canonicalization + SHA-256 fingerprint (`application/scheduling/fingerprint.py`); MANUAL ack IDs included and sorted | None for fingerprinting |
| OD-5 | HTTP FastAPI surface | Thin presentation adapter maps payloads and serializes clause 779 conflict responses; no parallel FastAPI app in M1-01 | Full Business API routes later |
| OD-6 | Branch name | `feature/m1-01-appointment-vertical-slice` per PO (not cloud `cursor/*-95a4` template) | No merge/PR without further authorization |
| OD-7 | Display-safe patient name source | Operational `tenant_persons.first_name`/`last_name` (clause 757) via `patient_profiles` join; disclosed only after `ALLOW_MANUAL_OVERBOOKING` | Not encrypted-identifier `masked_display`; clinic staff operational names |
