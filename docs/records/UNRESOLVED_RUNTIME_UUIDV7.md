# Unresolved — Python runtime / UUIDv7 provider

**Specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` (clauses 45–46; Appendix E.2)  
**Milestone:** M0 (Gate A)

## Agent environment measurement

- **Agent Python version (recorded at execution):** 3.12.3  
  (`3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`)
- Do not assume a developer-machine Python version applies to the Agent.

## Specification facts

- Application-level UUIDv7 is required.
- Database UUID generation must not substitute for the application UUIDv7 policy.
- Python standard-library `uuid.uuid7()` is available starting with Python 3.14, not 3.12/3.13.
- The specification does not mandate Python 3.14 and does not select a third-party provider.

## M0 decision

- **No UUIDv7 library or provider is selected in M0.**
- TP0001 schema acceptance remains separate: `tenant_registry.tenant_id` has no UUID-generating default.
- Application UUIDv7 generation/insertion tests are deferred until a provider and runtime pin are approved.

## Status

**UNRESOLVED** — Product/engineering must pin the supported Python runtime and select a UUIDv7 provider before application code relies on ID generation.
