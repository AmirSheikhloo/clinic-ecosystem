/**
 * Lightweight frontend helper checks (Node, no browser E2E).
 */
import assert from "node:assert/strict";
import test from "node:test";

function tehranLocalToUtcIso(localValue) {
  const [datePart, timePart] = localValue.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = timePart.split(":").map(Number);
  const guess = new Date(Date.UTC(y, m - 1, d, hh, mm, 0));
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(
    formatter.formatToParts(guess).map((p) => [p.type, p.value]),
  );
  const asTehran = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second),
  );
  const offsetMs = asTehran - guess.getTime();
  return new Date(guess.getTime() - offsetMs).toISOString();
}

function formatApiError(data, fallback) {
  if (data.message) return data.message;
  if (data.error) return data.error;
  return fallback;
}

function bookingFingerprint(payload) {
  const normalized = [
    payload.patientId,
    payload.serviceId,
    [...payload.resourceIds].sort().join(","),
    payload.startLocal,
    String(payload.durationMinutes),
  ].join("|");
  let hash = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = (hash * 31 + normalized.charCodeAt(i)) >>> 0;
  }
  return `desk-${hash.toString(16)}-${normalized.length}`;
}

function extractOverlapConflicts(data) {
  const detail = data.detail;
  if (!detail || typeof detail !== "object") return null;
  const d = detail;
  if (d.error === "manual_overlap_acknowledgement_required") {
    return Array.isArray(d.conflicts) ? d.conflicts : [];
  }
  return null;
}

test("tehran local converts to timezone-aware UTC ISO", () => {
  const iso = tehranLocalToUtcIso("2026-11-20T12:00");
  assert.match(iso, /Z$/);
  const roundTrip = new Date(iso);
  const fa = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tehran",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(roundTrip);
  assert.ok(fa.includes("12:00"));
});

test("formatApiError prefers message then error", () => {
  assert.equal(formatApiError({ message: "m", error: "e" }, "f"), "m");
  assert.equal(formatApiError({ error: "e" }, "f"), "e");
  assert.equal(formatApiError({}, "f"), "f");
});

test("UTC instant is preserved across Tehran display formatting", () => {
  const utc = "2026-11-20T08:30:00.000Z";
  const dt = new Date(utc);
  const local = new Intl.DateTimeFormat("fa-IR", {
    timeZone: "Asia/Tehran",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(dt);
  assert.ok(local.length > 0);
  assert.equal(dt.toISOString(), utc);
});

test("idempotency fingerprint stable for same payload, changes when resources change", () => {
  const base = {
    patientId: "p1",
    serviceId: "s1",
    resourceIds: ["r2", "r1"],
    startLocal: "2026-11-20T10:00",
    durationMinutes: 30,
  };
  const a = bookingFingerprint(base);
  const b = bookingFingerprint({ ...base, resourceIds: ["r1", "r2"] });
  const c = bookingFingerprint({ ...base, resourceIds: ["r1"] });
  assert.equal(a, b);
  assert.notEqual(a, c);
});

test("overlap conflicts extracted only for acknowledgement responses", () => {
  assert.equal(extractOverlapConflicts({ error: "capacity_conflict" }), null);
  const conflicts = extractOverlapConflicts({
    detail: {
      error: "manual_overlap_acknowledgement_required",
      conflicts: [{ appointment_id: "a1" }],
    },
  });
  assert.equal(conflicts.length, 1);
  assert.equal(conflicts[0].appointment_id, "a1");
});
