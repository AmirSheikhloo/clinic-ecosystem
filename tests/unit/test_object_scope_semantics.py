"""Object-level ALL/FILTER semantics — within-row AND, across-row OR, fail-closed."""

from __future__ import annotations

from uuid import uuid4

from clinic_ecosystem.infrastructure.persistence.permissions import (
    PermissionScope,
    SqlPermissionService,
)


def _filter(*, dept=None, service=None, provider=None) -> PermissionScope:
    return PermissionScope(
        permission_code="appointments.list",
        scope_mode="FILTER",
        department_id=dept,
        service_id=service,
        provider_resource_id=provider,
    )


def test_all_grants_unrestricted() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    scopes = [
        PermissionScope("appointments.list", "ALL", None, None, None),
        _filter(service=uuid4()),
    ]
    assert svc.allows(scopes, service_id=uuid4()) is True


def test_within_row_and_across_row_or() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    d1, d2 = uuid4(), uuid4()
    s1, s2 = uuid4(), uuid4()
    scopes = [_filter(dept=d1, service=s1), _filter(dept=d2, service=s2)]
    assert svc.allows(scopes, department_id=d1, service_id=s1) is True
    assert svc.allows(scopes, department_id=d2, service_id=s2) is True
    # Within-row AND fails when only one dimension matches a row.
    assert svc.allows(scopes, department_id=d1, service_id=s2) is False
    assert svc.allows(scopes, department_id=d1, service_id=None) is False


def test_missing_object_dimension_fail_closed() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    s1 = uuid4()
    scopes = [_filter(service=s1)]
    assert svc.allows(scopes, service_id=None) is False
    assert svc.allows(scopes, service_id=s1) is True


def test_allows_practitioner_does_not_widen_unconstrained_filter() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    dept = uuid4()
    scopes = [_filter(dept=dept)]  # no provider constraint
    # Omitting department while FILTER constrains it must fail closed.
    assert svc.allows_practitioner(scopes, uuid4()) is False
    assert svc.allows(scopes, department_id=dept, provider_resource_id=uuid4()) is True


def test_empty_scopes_deny() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    assert svc.allows([], service_id=uuid4()) is False
