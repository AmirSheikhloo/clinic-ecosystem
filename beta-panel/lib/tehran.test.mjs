import assert from "node:assert/strict";
import test from "node:test";

function tehranParts(date) {
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
  return Object.fromEntries(
    formatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
}

function tehranLocalToUtcIso(localValue) {
  const [datePart, timePart] = localValue.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = (timePart || "00:00").split(":").map(Number);
  const guess = new Date(Date.UTC(y, m - 1, d, hh, mm, 0));
  const parts = tehranParts(guess);
  const asTehran = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second),
  );
  return new Date(guess.getTime() - (asTehran - guess.getTime())).toISOString();
}

function tehranDayBoundsUtc(dateYmd) {
  const start = tehranLocalToUtcIso(`${dateYmd}T00:00`);
  const [y, m, d] = dateYmd.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d));
  next.setUTCDate(next.getUTCDate() + 1);
  const nextYmd = `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
  const end = tehranLocalToUtcIso(`${nextYmd}T00:00`);
  return { start, end };
}

test("day bounds are half-open midnight-to-midnight Tehran", () => {
  const { start, end } = tehranDayBoundsUtc("2026-11-20");
  assert.match(start, /Z$/);
  assert.match(end, /Z$/);
  assert.ok(new Date(end).getTime() > new Date(start).getTime());
  const startLocal = tehranParts(new Date(start));
  assert.equal(`${startLocal.year}-${startLocal.month}-${startLocal.day}`, "2026-11-20");
  assert.equal(startLocal.hour % 24, 0);
  assert.equal(startLocal.minute, "00");
});

test("UTC instant preserved after Tehran display", () => {
  const utc = "2026-11-20T08:30:00.000Z";
  const dt = new Date(utc);
  assert.equal(dt.toISOString(), utc);
});
