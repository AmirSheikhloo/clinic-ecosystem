"""BETA-02 Workstreams E and F: catalog administration, dashboard, global search."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.integration


def _svc(ops, headers, key=None, **overrides):
    body = {"service_name": "Cupping", "service_code": f"C-{uuid.uuid4().hex[:6]}",
            "default_duration_minutes": 40, "default_price_irr": 250000} | overrides
    return ops.client.post("/api/v1/catalog/admin/services",
                           headers={**headers, "Idempotency-Key": key or str(uuid.uuid4())}, json=body)


def test_catalog_admin_is_manager_only(ops) -> None:
    for headers in (ops.receptionist(), ops.unauthorized(), ops.deputy()):
        assert ops.client.get("/api/v1/catalog/admin/services", headers=headers).status_code == 403
        assert _svc(ops, headers).status_code == 403
        assert ops.client.get("/api/v1/catalog/admin/resources", headers=headers).status_code == 403
        assert ops.client.post("/api/v1/catalog/admin/resources", headers={**headers, "Idempotency-Key": "k"},
                               json={"resource_type": "ROOM", "resource_name": "x"}).status_code == 403


def test_service_create_update_activate_with_versions(ops) -> None:
    mgr = ops.manager()
    key = str(uuid.uuid4())
    code = f"IDEM-{uuid.uuid4().hex[:5]}"
    created = _svc(ops, mgr, key=key, service_code=code)
    assert created.status_code == 201, created.text
    sid = created.json()["service_id"]
    replay = _svc(ops, mgr, key=key, service_code=code)
    assert replay.status_code == 200 and replay.json()["service_id"] == sid
    assert _svc(ops, mgr, key=key, service_code=code, default_price_irr=1).status_code == 409

    url = f"/api/v1/catalog/admin/services/{sid}"
    detail = ops.client.get(url, headers=mgr)
    assert detail.status_code == 200 and detail.headers["ETag"] == '"1"'
    assert ops.client.patch(url, headers=mgr, json={"default_price_irr": 1}).status_code == 428
    upd = ops.client.patch(url, headers={**mgr, "If-Match": '"1"'},
                           json={"default_price_irr": 300000, "service_name": "Cupping+"})
    assert upd.status_code == 200 and upd.json()["aggregate_version"] == 2
    assert ops.client.patch(url, headers={**mgr, "If-Match": '"1"'}, json={"default_price_irr": 5}).status_code == 412
    off = ops.client.patch(url, headers={**mgr, "If-Match": '"2"'}, json={"is_active": False})
    assert off.status_code == 200
    # inactive services vanish from the receptionist catalog but stay in the admin directory
    active = ops.client.get("/api/v1/catalog/services", headers=ops.receptionist()).json()["items"]
    assert sid not in [i["id"] for i in active]
    admin_inactive = ops.client.get("/api/v1/catalog/admin/services", headers=mgr,
                                    params={"status": "inactive", "q": "Cupping"}).json()
    assert sid in [i["service_id"] for i in admin_inactive["items"]]
    # the inactive service cannot be booked
    seed = ops.seed.base
    start = datetime(2032, 1, 1, 6, 0, tzinfo=timezone.utc)
    booked = ops.client.post("/api/v1/appointments", headers={**ops.receptionist(), "Idempotency-Key": str(uuid.uuid4())},
                             json={"beneficiary_patient_id": str(seed.patient_a_id), "service_id": sid,
                                   "resource_ids": [str(seed.resource_a_id)],
                                   "start_at_utc": start.isoformat(),
                                   "end_at_utc": (start + timedelta(minutes=30)).isoformat()})
    assert booked.status_code == 400 and booked.json()["detail"]["error"] == "service_inactive"


def test_service_validation_and_duplicate_codes(ops) -> None:
    mgr = ops.manager()
    assert _svc(ops, mgr, default_duration_minutes=0).status_code == 400
    assert _svc(ops, mgr, default_price_irr=-1).status_code == 400
    assert _svc(ops, mgr, service_name="  ").status_code == 400
    assert _svc(ops, mgr, default_duration_minutes=100000).status_code == 400
    code = f"DUP-{uuid.uuid4().hex[:5]}"
    assert _svc(ops, mgr, service_code=code).status_code == 201
    dup = _svc(ops, mgr, service_code=code.lower())
    assert dup.status_code == 409 and dup.json()["error"] == "service_code_taken"


def test_requirements_replace_validates_resources_and_versions(ops) -> None:
    mgr = ops.manager()
    seed = ops.seed.base
    sid = _svc(ops, mgr).json()["service_id"]
    url = f"/api/v1/catalog/admin/services/{sid}/requirements"
    items = [{"requirement_group": "room", "required_resource_type": "ROOM", "quantity_required": 1},
             {"requirement_group": "doctor", "required_resource_type": "PRACTITIONER",
              "specific_resource_id": str(seed.resource_a2_id), "quantity_required": 1}]
    assert ops.client.put(url, headers=mgr, json={"items": items}).status_code == 428
    ok = ops.client.put(url, headers={**mgr, "If-Match": '"1"'}, json={"items": items})
    assert ok.status_code == 200 and ok.json()["aggregate_version"] == 2
    detail = ops.client.get(f"/api/v1/catalog/admin/services/{sid}", headers=mgr).json()
    assert {r["requirement_group"] for r in detail["requirements"]} == {"room", "doctor"}
    assert ops.client.put(url, headers={**mgr, "If-Match": '"1"'}, json={"items": items}).status_code == 412

    mismatch = [{"requirement_group": "x", "required_resource_type": "ROOM",
                 "specific_resource_id": str(seed.resource_a2_id), "quantity_required": 1}]
    assert ops.client.put(url, headers={**mgr, "If-Match": '"2"'}, json={"items": mismatch}).status_code == 400
    foreign = [{"requirement_group": "x", "required_resource_type": "ROOM",
                "specific_resource_id": str(seed.resource_b_id), "quantity_required": 1}]
    assert ops.client.put(url, headers={**mgr, "If-Match": '"2"'}, json={"items": foreign}).status_code == 400
    bad_type = [{"requirement_group": "x", "required_resource_type": "DEFAULT_ONLINE_SLOT_STREAM"}]
    assert ops.client.put(url, headers={**mgr, "If-Match": '"2"'}, json={"items": bad_type}).status_code == 400
    assert ops.client.put(url, headers={**mgr, "If-Match": '"2"'}, json={"items": [
        {"requirement_group": "x", "required_resource_type": "ROOM", "quantity_required": 0}]}).status_code == 400

    # the new requirements drive scheduling validation: a room alone no longer satisfies it
    start = datetime(2032, 2, 1, 6, 0, tzinfo=timezone.utc)
    body = {"beneficiary_patient_id": str(seed.patient_a_id), "service_id": sid,
            "resource_ids": [str(seed.resource_a_id)], "start_at_utc": start.isoformat(),
            "end_at_utc": (start + timedelta(minutes=30)).isoformat()}
    res = ops.client.post("/api/v1/appointments", headers={**ops.receptionist(), "Idempotency-Key": str(uuid.uuid4())}, json=body)
    assert res.status_code == 400, res.text
    body["resource_ids"] = [str(seed.resource_a_id), str(seed.resource_a2_id)]
    res = ops.client.post("/api/v1/appointments", headers={**ops.receptionist(), "Idempotency-Key": str(uuid.uuid4())}, json=body)
    assert res.status_code == 200, res.text


def test_resource_create_update_and_cross_tenant(ops) -> None:
    mgr = ops.manager()
    key = str(uuid.uuid4())
    res = ops.client.post("/api/v1/catalog/admin/resources", headers={**mgr, "Idempotency-Key": key},
                          json={"resource_type": "DEVICE", "resource_name": "Laser A"})
    assert res.status_code == 201, res.text
    rid = res.json()["resource_id"]
    replay = ops.client.post("/api/v1/catalog/admin/resources", headers={**mgr, "Idempotency-Key": key},
                             json={"resource_type": "DEVICE", "resource_name": "Laser A"})
    assert replay.status_code == 200 and replay.json()["resource_id"] == rid
    bad = ops.client.post("/api/v1/catalog/admin/resources", headers={**mgr, "Idempotency-Key": str(uuid.uuid4())},
                          json={"resource_type": "DEFAULT_ONLINE_SLOT_STREAM", "resource_name": "x"})
    assert bad.status_code == 400
    patch = ops.client.patch(f"/api/v1/catalog/admin/resources/{rid}", headers=mgr,
                             json={"resource_name": "Laser B", "is_active": False})
    assert patch.status_code == 200
    listing = ops.client.get("/api/v1/catalog/admin/resources", headers=mgr,
                             params={"status": "inactive", "resource_type": "DEVICE"}).json()
    assert [i["resource_name"] for i in listing["items"]] == ["Laser B"]
    assert ops.client.patch(f"/api/v1/catalog/admin/resources/{ops.seed.base.resource_b_id}", headers=mgr,
                            json={"is_active": False}).status_code == 404
    audit = ops.admin_query("SELECT operation FROM audit_entries WHERE target_id = $1 ORDER BY created_at_utc",
                            uuid.UUID(rid))
    assert [r["operation"] for r in audit] == ["resource.created", "resource.updated"]


def test_dashboard_sections_follow_permissions(ops) -> None:
    now = datetime.now(timezone.utc)
    params = {"start_at_utc": (now - timedelta(days=1)).isoformat(), "end_at_utc": (now + timedelta(days=1)).isoformat()}
    full = ops.client.get("/api/v1/dashboard/summary", headers=ops.manager(), params=params).json()
    assert full["patients_active"] >= 1 and full["staff_active"] is not None
    assert full["appointments"] is not None and full["services_active"] >= 1
    assert full["tomorrow_appointments"] is not None and "total" in full["tomorrow_appointments"]
    rec = ops.client.get("/api/v1/dashboard/summary", headers=ops.receptionist(), params=params).json()
    assert rec["staff_active"] is None and rec["patients_active"] >= 1
    assert rec["tomorrow_appointments"] is not None
    none = ops.client.get("/api/v1/dashboard/summary", headers=ops.unauthorized(), params=params).json()
    assert set(none.values()) == {None}
    assert ops.client.get("/api/v1/dashboard/summary", headers=ops.manager(), params={
        "start_at_utc": params["end_at_utc"], "end_at_utc": params["start_at_utc"]}).status_code == 400
    assert ops.client.get("/api/v1/dashboard/summary", params=params).status_code == 401


def test_global_search_only_returns_authorized_kinds(ops) -> None:
    mgr = ops.manager()
    ops.client.post("/api/v1/staff", headers={**mgr, "Idempotency-Key": str(uuid.uuid4())}, json={
        "first_name": "Zeynab", "last_name": "Searchable", "staff_kind": "DOCTOR"})
    full = ops.client.get("/api/v1/search", headers=mgr, params={"q": "Searchable"}).json()["items"]
    assert [i["kind"] for i in full] == ["staff"]
    patients = ops.client.get("/api/v1/search", headers=mgr, params={"q": "Alpha"}).json()["items"]
    assert "patient" in {i["kind"] for i in patients}
    rec = ops.client.get("/api/v1/search", headers=ops.receptionist(), params={"q": "Searchable"}).json()
    assert rec["items"] == []
    secret = ops.client.get("/api/v1/search", headers=mgr, params={"q": "Secret"}).json()
    assert secret["items"] == []
    assert ops.client.get("/api/v1/search", headers=mgr, params={"q": "a"}).status_code == 422
    assert ops.client.get("/api/v1/search", headers=ops.unauthorized(), params={"q": "Alpha"}).json()["items"] == []
    wildcard = ops.client.get("/api/v1/search", headers=mgr, params={"q": "%%"}).json()["items"]
    assert wildcard == []
