# M1-01 Open decisions / non-invention log

| ID | Topic | Resolution in this PR | Residual risk |
|---|---|---|---|
| OD-1 | RBAC table DDL (no Appendix F SQL) | Minimum tables in TP0003 sufficient for `ALLOW_MANUAL_OVERBOOKING` via role→permission→user assignment | Broader RBAC catalog sync/Cloud authority UI deferred |
| OD-2 | Appointment/allocation status CHECKs | F.4 leaves status unconstrained; application uses clause 781 enum values | Optional DB CHECK can be added in a later revision if PO freezes DDL |
| OD-3 | Idempotency/Outbox/Inbox/Audit DDL | Minimum columns implementing clauses 171–184 / 213–231 / 779 | Lease reclaim workers beyond HoldExpirationWorker / Outbox delivery TX2 network path deferred |
| OD-4 | RFC8785 JCS | Presentation uses sorted-JSON SHA-256 fingerprint helper; contract remains fingerprint string on command | Swap to full JCS library without handler changes |
| OD-5 | HTTP FastAPI surface | Thin command adapter only; no public HTTP routes in M1-01 | Gate A presentation endpoints later |
| OD-6 | Branch name | `feature/m1-01-appointment-vertical-slice` per PO (not cloud `cursor/*-95a4` template) | No merge/PR without further authorization |
