# M1-01 Implementation status

## Delivered

- UUIDv7 provider (`uuid6==2024.7.10`, locked, stdlib `uuid.UUID`)
- TP0002–TP0007 Tenant Plane migrations
- Domain `Appointment.schedule` + allocation set
- `ScheduleAppointmentHandler` with UoW, idempotency, outbox, MANUAL overlap ack + audit, ONLINE EXCLUDE translation
- Clause 779 display-safe conflict projection (authorized staff only) via presentation serializer
- Pre-insert MANUAL audit conflict snapshot (no self-inclusion; no display names in audit)
- Clause 783 MANUAL Resource→Appointment→Allocation lock order under one UoW
- RFC 8785 (`rfc8785==0.1.4`) idempotency fingerprints including MANUAL ack IDs
- HoldExpirationWorker (queue claim then Resource→Appointment→Allocation)
- RLS fail-closed and MANUAL denial integration tests
- VERIFY-01: Runtime (`tp_app_login` / `db_app_runtime`) effective privilege + real UPDATE/DELETE denial on `audit_entries` under matching Tenant GUC (append/INSERT retained)
- VERIFY-02: MANUAL overbooking audit asserts actor_type, actor_id, created_at_utc, target appointment id, conflict snapshot IDs, and no patient display names in persisted details
- Unit + integration tests; M1 GitHub Actions workflow

## Explicitly not claimed

- Full FastAPI Business/Sync HTTP route surface (adapter + serializer only; OD-5 presentation adapter without HTTP Business API routes)
- Outbox network delivery worker
- Cross-hub sync protocol / full Cloud→Local ONLINE projection delivery (Local MANUAL conflict inspection depends on future Integration Event/Sync)
- Nobat.ir ACL
- Production key management / AES field crypto beyond schema columns
