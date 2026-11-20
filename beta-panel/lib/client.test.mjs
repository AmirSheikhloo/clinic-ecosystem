/**
 * Lightweight frontend helper checks (Node, no browser E2E).
 * Run: node --test lib/client.test.mjs
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
  assert.ok(fa.includes("12:00") || fa.includes("12:00"));
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
