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
- Unit + integration tests; M1 GitHub Actions workflow

## Explicitly not claimed

- Full FastAPI Business/Sync HTTP route surface (adapter + serializer only)
- Outbox network delivery worker
- Cross-hub sync protocol
- Nobat.ir ACL
- Production key management / AES field crypto beyond schema columns
