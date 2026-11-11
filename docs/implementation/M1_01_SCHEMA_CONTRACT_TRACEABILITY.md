# M1-01 Schema contract traceability

Authority: `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`.

| Revision | Spec source | Objects | Notes |
|---|---|---|---|
| TP0001 | Appendix F.2 (partial) | `btree_gist`, `tenant_registry` | Delivered in M0; unchanged |
| TP0002 | Appendix F.2 (remainder) | `tenant_persons`, `person_identifiers`, `person_phones`, `patient_profiles`, `staff_profiles`, `user_accounts` | Verbatim F.2 SQL |
| TP0003 | Clauses 78–88, 199, 779; §51 FK rules | `permission_catalog_snapshots`, `tenant_roles`, `role_permission_assignments`, `user_role_assignments`, `tenant_governance_assignments` | No Appendix F DDL; minimum derived for `ALLOW_MANUAL_OVERBOOKING` |
| TP0004 | Appendix F.3 | `services`, `bookable_resources`, `service_resource_requirements` | Verbatim F.3 |
| TP0005 | Appendix F.4 + F.5 | `appointments`, `appointment_resource_allocations`, `hold_expiry_work_items` | Verbatim; ONLINE-only GiST EXCLUDE |
| TP0006 | Clauses 161–184, 213–231, 779 | `idempotency_records`, `outbox_messages`, `inbox_messages`, `sync_stream_counters`, `audit_entries` | Minimum persistence; no F DDL |
| TP0007 | Appendix F.6 / clauses 745–747 | RLS ENABLE+FORCE + 3 policies on all TP0001–TP0006 tenant tables; audit append-only revoke | Policy names: `tenant_runtime_base`, `tenant_runtime_guard`, `tenant_migrator_maintenance` |

## Application ID rule

All application-generated primary keys use `clinic_ecosystem.shared_kernel.uuid7.new_uuid7()` (`uuid6==2024.7.10`). Migrations do not add UUID-generating defaults.
