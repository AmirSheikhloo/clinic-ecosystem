"""Unit coverage for audit permission + list DTO shaping (no DB)."""

from clinic_ecosystem.domain.access import permissions as perm


def test_audit_view_in_catalog() -> None:
    assert perm.AUDIT_VIEW in perm.PERMISSION_CATALOG
    definition = perm.PERMISSION_CATALOG[perm.AUDIT_VIEW]
    assert definition.category == "governance"
    assert "audit" in definition.description.lower()


def test_manager_bundle_includes_audit_excludes_governance_manage() -> None:
    from tests.integration.beta02_seed import ALL_PERMISSIONS, MANAGER_PERMISSIONS

    assert perm.AUDIT_VIEW in ALL_PERMISSIONS
    assert perm.AUDIT_VIEW in MANAGER_PERMISSIONS
    assert perm.GOVERNANCE_MANAGE not in MANAGER_PERMISSIONS
