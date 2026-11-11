"""TP0007 — RLS and role policy for all M1-01 tenant-owned tables.

Applies the Appendix F.6 three-policy pattern (runtime base + restrictive
tenant guard + migrator maintenance) to every tenant-owned table introduced
by TP0001–TP0006. Audit entries remain append-only for runtime (no UPDATE/DELETE).

Revision ID: tp0007
Revises: tp0006
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0007"
down_revision: Union[str, None] = "tp0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENTS = [
"""ALTER TABLE tenant_registry ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE tenant_registry FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON tenant_registry
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON tenant_registry
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON tenant_registry
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE tenant_persons ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE tenant_persons FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON tenant_persons
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON tenant_persons
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON tenant_persons
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE person_identifiers ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE person_identifiers FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON person_identifiers
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON person_identifiers
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON person_identifiers
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE person_phones ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE person_phones FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON person_phones
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON person_phones
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON person_phones
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE patient_profiles ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE patient_profiles FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON patient_profiles
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON patient_profiles
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON patient_profiles
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE staff_profiles ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE staff_profiles FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON staff_profiles
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON staff_profiles
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON staff_profiles
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE user_accounts FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON user_accounts
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON user_accounts
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON user_accounts
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE permission_catalog_snapshots ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE permission_catalog_snapshots FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON permission_catalog_snapshots
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON permission_catalog_snapshots
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON permission_catalog_snapshots
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE tenant_roles ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE tenant_roles FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON tenant_roles
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON tenant_roles
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON tenant_roles
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE role_permission_assignments ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE role_permission_assignments FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON role_permission_assignments
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON role_permission_assignments
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON role_permission_assignments
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE user_role_assignments FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON user_role_assignments
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON user_role_assignments
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON user_role_assignments
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE tenant_governance_assignments ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE tenant_governance_assignments FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON tenant_governance_assignments
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON tenant_governance_assignments
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON tenant_governance_assignments
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE services ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE services FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON services
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON services
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON services
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE bookable_resources ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE bookable_resources FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON bookable_resources
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON bookable_resources
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON bookable_resources
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE service_resource_requirements ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE service_resource_requirements FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON service_resource_requirements
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON service_resource_requirements
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON service_resource_requirements
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE appointments ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE appointments FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON appointments
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON appointments
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON appointments
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE appointment_resource_allocations ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE appointment_resource_allocations FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON appointment_resource_allocations
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON appointment_resource_allocations
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON appointment_resource_allocations
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE hold_expiry_work_items ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE hold_expiry_work_items FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON hold_expiry_work_items
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON hold_expiry_work_items
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON hold_expiry_work_items
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE idempotency_records ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE idempotency_records FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON idempotency_records
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON idempotency_records
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON idempotency_records
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE outbox_messages ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE outbox_messages FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON outbox_messages
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON outbox_messages
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON outbox_messages
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE inbox_messages ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE inbox_messages FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON inbox_messages
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON inbox_messages
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON inbox_messages
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE sync_stream_counters ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE sync_stream_counters FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON sync_stream_counters
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON sync_stream_counters
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON sync_stream_counters
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""ALTER TABLE audit_entries ENABLE ROW LEVEL SECURITY""",
"""ALTER TABLE audit_entries FORCE ROW LEVEL SECURITY""",
"""CREATE POLICY tenant_runtime_base ON audit_entries
AS PERMISSIVE FOR ALL TO db_app_runtime
USING (true) WITH CHECK (true)""",
"""CREATE POLICY tenant_runtime_guard ON audit_entries
AS RESTRICTIVE FOR ALL TO db_app_runtime
USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)""",
"""CREATE POLICY tenant_migrator_maintenance ON audit_entries
AS PERMISSIVE FOR ALL TO db_migrator
USING (true) WITH CHECK (true)""",
"""REVOKE UPDATE, DELETE ON TABLE audit_entries FROM db_app_runtime""",
"""REVOKE UPDATE, DELETE ON TABLE audit_entries FROM PUBLIC""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0007 downgrade is intentionally irreversible under Appendix E.4."
    )
