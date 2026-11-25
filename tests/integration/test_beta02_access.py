"""BETA-02 Workstream C: roles, permissions, account status, governance."""

from __future__ import annotations

import uuid

import pytest

from tests.integration.beta02_seed import TARGET_PASSWORD

pytestmark = pytest.mark.integration


def _role(ops, headers, perms, code=None):
    code = code or f"ROLE_{uuid.uuid4().hex[:8].upper()}"
    res = ops.client.post("/api/v1/access/roles", headers=headers,
                          json={"role_code": code, "role_name": "Test role", "permissions": perms})
    return res, code


def test_access_endpoints_require_permissions(ops) -> None:
    for headers in (ops.unauthorized(), ops.receptionist()):
        for path in ("/api/v1/access/roles", "/api/v1/access/accounts",
                     "/api/v1/access/governance", "/api/v1/access/permissions"):
            assert ops.client.get(path, headers=headers).status_code == 403, path
    assert ops.client.get("/api/v1/access/roles").status_code == 401


def test_me_exposes_effective_permissions_and_governance(ops) -> None:
    me = ops.client.get("/api/v1/auth/me", headers=ops.manager()).json()
    assert "BETA02_ROLES_MANAGE" in me["permissions"]
    assert me["governance_roles"] == ["CLINIC_MANAGER"]
    assert "BETA02_GOVERNANCE_MANAGE" not in me["permissions"]
    assert ops.client.get("/api/v1/auth/me", headers=ops.unauthorized()).json()["permissions"] == []


def test_role_lifecycle_and_permission_catalog_validation(ops) -> None:
    mgr = ops.manager()
    res, code = _role(ops, mgr, ["BETA01B_PATIENTS_SEARCH", "BETA02_STAFF_VIEW"])
    assert res.status_code == 201, res.text
    role_id = res.json()["role_id"]
    dup, _ = _role(ops, mgr, [], code=code)
    assert dup.status_code == 409
    for bad in ("super_admin", "SUPER_ADMIN", "CLINIC_OWNER", "x"):
        assert _role(ops, mgr, [], code=bad)[0].status_code == 400
    unknown = _role(ops, mgr, ["NOT_A_PERMISSION"])[0]
    assert unknown.status_code == 400 and unknown.json()["error"] == "permission_unknown"

    put = ops.client.put(f"/api/v1/access/roles/{role_id}/permissions", headers=mgr,
                         json={"permissions": ["BETA02_STAFF_VIEW", "BETA01B_APPOINTMENTS_LIST"]})
    assert put.status_code == 200
    roles = ops.client.get("/api/v1/access/roles", headers=mgr).json()["items"]
    mine = next(r for r in roles if r["role_id"] == role_id)
    assert mine["permissions"] == ["BETA01B_APPOINTMENTS_LIST", "BETA02_STAFF_VIEW"]
    assert ops.client.delete(f"/api/v1/access/roles/{role_id}", headers=mgr).status_code == 204
    assert ops.client.delete(f"/api/v1/access/roles/{role_id}", headers=mgr).status_code == 404


def test_system_roles_are_immutable(ops) -> None:
    mgr = ops.manager()
    rid = str(ops.seed.role_manager_id)
    put = ops.client.put(f"/api/v1/access/roles/{rid}/permissions", headers=mgr, json={"permissions": []})
    assert put.status_code == 403 and put.json()["error"] == "system_role_immutable"
    assert ops.client.delete(f"/api/v1/access/roles/{rid}", headers=mgr).status_code == 403


def test_privilege_escalation_is_denied_on_role_permissions(ops) -> None:
    deputy = ops.deputy()  # holds ROLES_MANAGE but not STAFF_MANAGE / CATALOG_*
    res, _ = _role(ops, deputy, ["BETA02_STAFF_MANAGE"])
    assert res.status_code == 403
    assert res.json()["error"] == "privilege_escalation_denied"
    assert res.json()["permissions"] == ["BETA02_STAFF_MANAGE"]
    ok, _ = _role(ops, deputy, ["BETA02_STAFF_VIEW"])
    assert ok.status_code == 201
    role_id = ok.json()["role_id"]
    grow = ops.client.put(f"/api/v1/access/roles/{role_id}/permissions", headers=deputy,
                          json={"permissions": ["BETA02_STAFF_VIEW", "BETA02_GOVERNANCE_MANAGE"]})
    assert grow.status_code == 403


def test_assign_roles_enforces_escalation_self_and_owner_rules(ops) -> None:
    seed = ops.seed
    deputy, mgr, owner = ops.deputy(), ops.manager(), ops.owner()
    target = str(seed.target_account_id)
    url = f"/api/v1/access/accounts/{target}/roles"

    # deputy cannot hand out the manager role (permissions it does not hold)
    esc = ops.client.put(url, headers=deputy, json={"role_ids": [str(seed.role_manager_id)]})
    assert esc.status_code == 403 and esc.json()["error"] == "privilege_escalation_denied"
    # deputy can assign a role limited to permissions it holds
    ok = ops.client.put(url, headers=deputy, json={"role_ids": [str(seed.role_custom_id)]})
    assert ok.status_code == 200, ok.text
    eff = ops.client.get(f"/api/v1/access/accounts/{target}/effective-permissions", headers=mgr).json()
    assert [i["permission_code"] for i in eff["items"]] == ["BETA01B_PATIENTS_SEARCH"]
    assert eff["items"][0]["via_roles"] == ["CUSTOM_FRONTDESK"]

    # effect is immediate on the target's next request
    session = ops.login(seed.target_login, TARGET_PASSWORD)
    assert ops.client.get("/api/v1/patients/directory", headers=session).status_code == 200

    # removing a role the actor does not fully hold is denied; owners are protected
    assert ops.client.put(f"/api/v1/access/accounts/{seed.manager_account_id}/roles", headers=deputy,
                          json={"role_ids": []}).status_code == 403
    prot = ops.client.put(f"/api/v1/access/accounts/{seed.owner_account_id}/roles", headers=mgr,
                          json={"role_ids": []})
    assert prot.status_code == 403
    # nobody changes their own roles
    selfie = ops.client.put(f"/api/v1/access/accounts/{seed.manager_account_id}/roles", headers=mgr,
                            json={"role_ids": [str(seed.role_manager_id), str(seed.role_custom_id)]})
    assert selfie.status_code == 403 and selfie.json()["error"] == "self_change_denied"
    # owner may strip and restore
    assert ops.client.put(url, headers=owner, json={"role_ids": []}).status_code == 200
    unknown = ops.client.put(url, headers=owner, json={"role_ids": [str(uuid.uuid4())]})
    assert unknown.status_code == 400
    assert ops.client.get("/api/v1/patients/directory", headers=session).status_code == 403


def test_cross_tenant_ids_are_not_found(ops) -> None:
    owner = ops.owner()
    seed = ops.seed
    assert ops.client.put(f"/api/v1/access/accounts/{seed.tenant_b_account_id}/roles", headers=owner,
                          json={"role_ids": []}).status_code == 404
    assert ops.client.put(f"/api/v1/access/accounts/{seed.tenant_b_account_id}/status",
                          headers={**owner, "If-Match": '"1"'}, json={"is_active": False}).status_code == 404
    assert ops.client.put(f"/api/v1/access/roles/{seed.tenant_b_role_id}/permissions", headers=owner,
                          json={"permissions": []}).status_code == 404
    assert ops.client.put(f"/api/v1/access/governance/{uuid.uuid4()}", headers=owner,
                          json={"roles": ["RECEPTIONIST"]}).status_code == 404
    rows = ops.client.get("/api/v1/access/accounts", headers=owner, params={"limit": 100}).json()
    assert str(seed.tenant_b_account_id) not in str(rows)


def test_suspend_reactivate_account_is_immediate_and_versioned(ops) -> None:
    seed = ops.seed
    mgr = ops.manager()
    # manager holds ACCOUNTS_SET_ACTIVE; use a freshly provisioned account with no roles
    login = f"susp-{uuid.uuid4().hex[:6]}@beta02.test"
    created = ops.client.post("/api/v1/staff", headers={**mgr, "Idempotency-Key": str(uuid.uuid4())}, json={
        "first_name": "Su", "last_name": "Spend", "staff_kind": "OTHER", "create_login_account": True,
        "login": {"login_identifier": login, "password": "Suspendable-pass-123"}}).json()
    account = created["account_id"]
    session = ops.login(login, "Suspendable-pass-123")
    url = f"/api/v1/access/accounts/{account}/status"
    assert ops.client.put(url, headers=mgr, json={"is_active": False}).status_code == 428
    off = ops.client.put(url, headers={**mgr, "If-Match": '"1"'}, json={"is_active": False})
    assert off.status_code == 200 and off.json()["aggregate_version"] == 2
    assert ops.client.get("/api/v1/auth/me", headers=session).status_code == 401
    assert ops.client.post("/api/v1/auth/login", json={
        "login_identifier": login, "password": "Suspendable-pass-123"}).status_code == 401
    stale = ops.client.put(url, headers={**mgr, "If-Match": '"1"'}, json={"is_active": True})
    assert stale.status_code == 412
    on = ops.client.put(url, headers={**mgr, "If-Match": '"2"'}, json={"is_active": True})
    assert on.status_code == 200
    ops.login(login, "Suspendable-pass-123")
    # no self-suspension, owners protected from managers
    assert ops.client.put(f"/api/v1/access/accounts/{seed.manager_account_id}/status",
                          headers={**mgr, "If-Match": '"1"'}, json={"is_active": False}).status_code == 403
    assert ops.client.put(f"/api/v1/access/accounts/{seed.owner_account_id}/status",
                          headers={**mgr, "If-Match": '"1"'}, json={"is_active": False}).status_code == 403
    audit = ops.admin_query(
        "SELECT operation FROM audit_entries WHERE target_id = $1 ORDER BY created_at_utc",
        uuid.UUID(account))
    assert [r["operation"] for r in audit] == ["account.provisioned", "account.suspended", "account.reactivated"]


def test_governance_authority_rules(ops) -> None:
    seed = ops.seed
    owner, mgr, deputy = ops.owner(), ops.manager(), ops.deputy()
    listing = ops.client.get("/api/v1/access/governance", headers=mgr).json()["items"]
    assert {tuple(i["roles"]) for i in listing} >= {("CLINIC_OWNER",), ("CLINIC_MANAGER",)}
    # deputy lacks the governance permission entirely
    assert ops.client.put(f"/api/v1/access/governance/{seed.target_person_id}", headers=deputy,
                          json={"roles": ["RECEPTIONIST"]}).status_code == 403
    # manager role has no GOVERNANCE_MANAGE in the fixture
    assert ops.client.put(f"/api/v1/access/governance/{seed.target_person_id}", headers=mgr,
                          json={"roles": ["RECEPTIONIST"]}).status_code == 403
    url = f"/api/v1/access/governance/{seed.target_person_id}"
    assert ops.client.put(url, headers=owner, json={"roles": ["DEPUTY_ADMIN"]}).status_code == 200
    assert ops.client.put(url, headers=owner, json={"roles": ["WIZARD"]}).status_code == 400
    # self change and last-owner protection
    assert ops.client.put(f"/api/v1/access/governance/{seed.owner_person_id}", headers=owner,
                          json={"roles": []}).status_code == 403
    assert ops.client.put(url, headers=owner, json={"roles": ["CLINIC_OWNER"]}).status_code == 200
    removed = ops.client.put(f"/api/v1/access/governance/{seed.owner_person_id}",
                             headers=ops.login(seed.target_login, TARGET_PASSWORD), json={"roles": []})
    assert removed.status_code == 403  # target holds no governance permission
    assert ops.client.put(url, headers=owner, json={"roles": []}).status_code == 200


def test_every_denied_escalation_is_not_audited_and_success_is(ops) -> None:
    deputy = ops.deputy()
    res, code = _role(ops, deputy, ["BETA02_STAFF_MANAGE"])
    assert res.status_code == 403
    rows = ops.admin_query(
        "SELECT 1 FROM audit_entries WHERE operation = 'role.created' AND details_json->>'role_code' = $1",
        code)
    assert rows == []
    ok, code2 = _role(ops, deputy, ["BETA02_STAFF_VIEW"])
    rows = ops.admin_query(
        "SELECT actor_id FROM audit_entries WHERE operation = 'role.created' AND details_json->>'role_code' = $1",
        code2)
    assert len(rows) == 1 and rows[0]["actor_id"] == ops.seed.deputy_account_id
