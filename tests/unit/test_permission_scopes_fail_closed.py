"""Fail-closed scope semantics (no flat fallback when scopes table is active)."""

from __future__ import annotations

from uuid import uuid4

from clinic_ecosystem.infrastructure.persistence.permissions import (
    PermissionScope,
    SqlPermissionService,
)


def test_empty_scopes_deny_department() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    assert svc.allows_department([], uuid4()) is False
    assert svc.allows([], department_id=uuid4()) is False


def test_all_scope_allows_any_department_and_service() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    scopes = [
        PermissionScope("P", "ALL", None, None, None),
    ]
    assert svc.allows(scopes, department_id=uuid4(), service_id=uuid4()) is True
    assert svc.allows_practitioner(scopes, uuid4()) is True


def test_filter_within_row_and_across_row_or() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    dept_a, dept_b = uuid4(), uuid4()
    svc_a, svc_b = uuid4(), uuid4()
    scopes = [
        PermissionScope("P", "FILTER", dept_a, svc_a, None),
        PermissionScope("P", "FILTER", dept_b, None, None),
    ]
    assert svc.allows(scopes, department_id=dept_a, service_id=svc_a) is True
    # Within-row AND fails when service mismatches on first row; second row has no service filter.
    assert svc.allows(scopes, department_id=dept_b, service_id=svc_b) is True
    assert svc.allows(scopes, department_id=dept_a, service_id=svc_b) is False


def test_practitioner_unscoped_filter_covers_all_practitioners() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    scopes = [PermissionScope("P", "FILTER", uuid4(), None, None)]
    assert svc.allows_practitioner(scopes, uuid4()) is True
    scoped = [PermissionScope("P", "FILTER", None, None, uuid4())]
    other = uuid4()
    assert svc.allows_practitioner(scoped, scoped[0].provider_resource_id) is True
    assert svc.allows_practitioner(scoped, other) is False


def test_permission_scope_matches_and() -> None:
    dept, svc_id, pract = uuid4(), uuid4(), uuid4()
    row = PermissionScope("P", "FILTER", dept, svc_id, pract)
    assert row.matches(department_id=dept, service_id=svc_id, provider_resource_id=pract)
    assert not row.matches(department_id=dept, service_id=svc_id, provider_resource_id=uuid4())
