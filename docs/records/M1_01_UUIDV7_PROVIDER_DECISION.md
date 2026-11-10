# M1-01 — UUIDv7 provider decision (PO resolution 14.1 / 14.4A)

## Decision

- Library: `uuid6==2024.7.10` (exact pin).
- Public API: `clinic_ecosystem.shared_kernel.uuid7.new_uuid7() -> uuid.UUID`.
- Normalization: convert `uuid6.UUID` to stdlib `uuid.UUID(int=...)` before return.
- Concurrency: module-private `threading.Lock` serializes every `uuid6.uuid7()` call
  because the library generator is not thread-safe.
- Domain/application/infrastructure generate IDs only through this provider.
- PostgreSQL must not invent row IDs via `gen_random_uuid()` / `uuid_generate_v4()`
  defaults on application tables (clause 46).

## Non-goals

- No custom UUIDv7 bit-packing implementation.
- No distributed clock/sequence authority beyond what UUIDv7 temporal locality provides.
