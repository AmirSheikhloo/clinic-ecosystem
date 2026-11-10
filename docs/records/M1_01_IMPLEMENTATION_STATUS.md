# M1-01 Implementation status

## Delivered

- UUIDv7 provider (`uuid6==2024.7.10`, locked, stdlib `uuid.UUID`)
- TP0002–TP0007 Tenant Plane migrations
- Domain `Appointment.schedule` + allocation set
- `ScheduleAppointmentHandler` with UoW, idempotency, outbox, MANUAL overlap ack + audit, ONLINE EXCLUDE translation
- HoldExpirationWorker (queue claim then Resource→Appointment→Allocation)
- Unit + integration tests; M1 GitHub Actions workflow

## Explicitly not claimed

- Full FastAPI Business/Sync API
- Outbox network delivery worker
- Cross-hub sync protocol
- Nobat.ir ACL
- Production key management / AES field crypto beyond schema columns
