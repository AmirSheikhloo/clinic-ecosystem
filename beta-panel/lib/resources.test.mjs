import assert from "node:assert/strict";
import test from "node:test";

function validate(requirements, selectedIds, resourcesById) {
  const unique = Array.from(new Set(selectedIds));
  if (unique.length !== selectedIds.length) {
    return { ok: false, code: "extra" };
  }
  if (!requirements.length) {
    return unique.length ? { ok: true } : { ok: false, code: "empty_required" };
  }
  const remaining = [...unique];
  for (const req of requirements) {
    const matched = [];
    for (const id of [...remaining]) {
      const resource = resourcesById.get(id);
      if (!resource || !resource.is_active) continue;
      if (req.specific_resource_id && id !== req.specific_resource_id) continue;
      if (resource.resource_type !== req.required_resource_type) continue;
      matched.push(id);
      remaining.splice(remaining.indexOf(id), 1);
      if (matched.length === req.quantity_required) break;
    }
    if (matched.length < req.quantity_required) {
      return { ok: false, code: "insufficient" };
    }
  }
  if (remaining.length) return { ok: false, code: "extra" };
  return { ok: true };
}

const room = { id: "r1", resource_type: "ROOM", resource_name: "A", is_active: true };
const doc = { id: "d1", resource_type: "PRACTITIONER", resource_name: "Dr", is_active: true };
const byId = new Map([
  ["r1", room],
  ["d1", doc],
]);

test("single resource requirement satisfied", () => {
  const reqs = [
    {
      id: "q1",
      requirement_group: "primary",
      required_resource_type: "ROOM",
      specific_resource_id: null,
      quantity_required: 1,
    },
  ];
  assert.equal(validate(reqs, ["r1"], byId).ok, true);
});

test("multi resource and specific resource", () => {
  const reqs = [
    {
      id: "q1",
      requirement_group: "room",
      required_resource_type: "ROOM",
      specific_resource_id: null,
      quantity_required: 1,
    },
    {
      id: "q2",
      requirement_group: "doctor",
      required_resource_type: "PRACTITIONER",
      specific_resource_id: "d1",
      quantity_required: 1,
    },
  ];
  assert.equal(validate(reqs, ["r1", "d1"], byId).ok, true);
  assert.equal(validate(reqs, ["r1"], byId).code, "insufficient");
});

test("extra resource rejected", () => {
  const reqs = [
    {
      id: "q1",
      requirement_group: "primary",
      required_resource_type: "ROOM",
      specific_resource_id: null,
      quantity_required: 1,
    },
  ];
  assert.equal(validate(reqs, ["r1", "d1"], byId).code, "extra");
});

test("empty requirements still need at least one resource", () => {
  assert.equal(validate([], [], byId).code, "empty_required");
  assert.equal(validate([], ["r1"], byId).ok, true);
});
