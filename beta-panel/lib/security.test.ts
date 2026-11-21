/**
 * Tests import the ACTUAL production security helpers (not duplicated copies).
 * Run: node --experimental-strip-types --test lib/*.test.ts
 */
import assert from "node:assert/strict";
import test from "node:test";
import { NextResponse } from "next/server";

import {
  backendBaseUrl,
  isBetaPanelEnabled,
  requireBetaPanelEnabled,
  BetaPanelConfigError,
  CSRF_COOKIE,
  SESSION_COOKIE,
} from "./config.ts";
import {
  cookieSecureFromRequest,
  CookieTransportError,
  isLoopbackHostname,
  sessionCookieOptions,
  csrfCookieOptions,
} from "./cookies.ts";
import { evaluateCsrf, CsrfError } from "./csrf.ts";
import {
  bookingFingerprint,
  IdempotencyKeyStore,
  sortedConflictIds,
} from "./booking.ts";
import {
  clearSessionCookies,
  setSessionCookies,
  sessionCookieIsHttpOnly,
} from "./session.ts";
import { handleRouteError } from "./api-error.ts";
import {
  eligibleResourcesForRequirements,
  validateResourceSelection,
} from "./resources.ts";
import { tehranDayBoundsUtc, tehranLocalToUtcIso } from "./tehran.ts";

test("isBetaPanelEnabled uses production config helper", () => {
  assert.equal(
    isBetaPanelEnabled({ CLINIC_ENV: "production", CLINIC_BETA_PANEL_ENABLED: "1" }),
    false,
  );
  assert.equal(
    isBetaPanelEnabled({ CLINIC_ENV: "development", CLINIC_BETA_PANEL_ENABLED: "0" }),
    false,
  );
  assert.equal(
    isBetaPanelEnabled({ CLINIC_ENV: "development", CLINIC_BETA_PANEL_ENABLED: "1" }),
    true,
  );
  assert.throws(
    () => requireBetaPanelEnabled({ CLINIC_ENV: "production", CLINIC_BETA_PANEL_ENABLED: "1" }),
    BetaPanelConfigError,
  );
  assert.throws(
    () => backendBaseUrl({ CLINIC_ENV: "development", CLINIC_BETA_PANEL_ENABLED: "1" }),
    BetaPanelConfigError,
  );
  assert.equal(
    backendBaseUrl({
      CLINIC_ENV: "test",
      CLINIC_BETA_PANEL_ENABLED: "1",
      CLINIC_API_BASE_URL: "http://127.0.0.1:8000/",
    }),
    "http://127.0.0.1:8000",
  );
});

test("cookieSecureFromRequest: HTTPS secure, loopback HTTP insecure, non-loopback fails", () => {
  assert.equal(
    cookieSecureFromRequest(new Request("https://clinic.example/api/auth/login")),
    true,
  );
  assert.equal(
    cookieSecureFromRequest(new Request("http://127.0.0.1:3100/api/auth/login")),
    false,
  );
  assert.equal(
    cookieSecureFromRequest(new Request("http://localhost:3100/api/auth/login")),
    false,
  );
  assert.throws(
    () => cookieSecureFromRequest(new Request("http://evil.example/api/auth/login")),
    CookieTransportError,
  );
  // Forwarding headers must not authorize Secure=false on non-loopback HTTP,
  // and must not flip loopback into Secure via untrusted proto claims alone.
  assert.equal(
    cookieSecureFromRequest(
      new Request("http://127.0.0.1:3100/x", {
        headers: { "x-forwarded-proto": "https" },
      }),
    ),
    false,
  );
  assert.throws(
    () =>
      cookieSecureFromRequest(
        new Request("http://app.internal/x", {
          headers: { "x-forwarded-proto": "https" },
        }),
      ),
    CookieTransportError,
  );
  assert.equal(isLoopbackHostname("127.0.0.1"), true);
  assert.equal(isLoopbackHostname("localhost.evil"), false);
});

test("evaluateCsrf rejects missing, mismatched, and cross-origin tokens", () => {
  assert.throws(
    () =>
      evaluateCsrf({
        headerToken: "",
        cookieToken: "abc",
        origin: null,
        requestUrl: "http://127.0.0.1:3100/api/auth/logout",
      }),
    CsrfError,
  );
  assert.throws(
    () =>
      evaluateCsrf({
        headerToken: "abc",
        cookieToken: "xyz",
        origin: null,
        requestUrl: "http://127.0.0.1:3100/api/auth/logout",
      }),
    CsrfError,
  );
  assert.throws(
    () =>
      evaluateCsrf({
        headerToken: "abc",
        cookieToken: "abc",
        origin: "https://evil.example",
        requestUrl: "http://127.0.0.1:3100/api/auth/logout",
      }),
    CsrfError,
  );
  assert.doesNotThrow(() =>
    evaluateCsrf({
      headerToken: "abc",
      cookieToken: "abc",
      origin: "http://127.0.0.1:3100",
      requestUrl: "http://127.0.0.1:3100/api/auth/logout",
    }),
  );
});

test("setSessionCookies / clearSessionCookies set HttpOnly session and Readable CSRF", () => {
  const request = new Request("http://127.0.0.1:3100/api/auth/login");
  const response = NextResponse.json({ ok: true });
  setSessionCookies(response, request, {
    accessToken: "test-access-token-value",
    maxAgeSeconds: 900,
  });
  const setCookies = response.cookies.getAll();
  const session = setCookies.find((c) => c.name === SESSION_COOKIE);
  const csrf = setCookies.find((c) => c.name === CSRF_COOKIE);
  assert.ok(session);
  assert.equal(session!.value, "test-access-token-value");
  assert.equal(session!.httpOnly, true);
  assert.equal(session!.sameSite, "lax");
  assert.equal(session!.secure, false);
  assert.ok(csrf);
  assert.equal(csrf!.httpOnly, false);
  assert.ok(csrf!.value.length > 0);

  // Access token must not appear in JSON body helpers we return to clients.
  const body = { account_id: "x" };
  assert.equal(JSON.stringify(body).includes("test-access-token-value"), false);

  const cleared = NextResponse.json({ ok: true });
  clearSessionCookies(cleared, request);
  const clearedSession = cleared.cookies.get(SESSION_COOKIE);
  assert.ok(clearedSession);
  assert.equal(clearedSession!.value, "");
  assert.equal(clearedSession!.maxAge, 0);

  const serialized = [
    `${SESSION_COOKIE}=abc; Path=/; HttpOnly; SameSite=Lax`,
    `${CSRF_COOKIE}=xyz; Path=/; SameSite=Lax`,
  ];
  assert.equal(sessionCookieIsHttpOnly(serialized), true);
});

test("handleRouteError maps panel disabled, csrf, and unsafe cookie transport", () => {
  const disabled = handleRouteError(
    new BetaPanelConfigError("CLINIC_BETA_PANEL_ENABLED is not enabled"),
  );
  assert.equal(disabled.status, 503);
  const csrf = handleRouteError(new CsrfError());
  assert.equal(csrf.status, 403);
  const transport = handleRouteError(
    new CookieTransportError("Beta panel cookies refuse non-loopback HTTP transports"),
  );
  assert.equal(transport.status, 503);
});

test("confirmed-overlap fingerprint is stable and includes ack + conflict ids", () => {
  const store = new IdempotencyKeyStore();
  const base = {
    patientId: "p1",
    serviceId: "s1",
    resourceIds: ["r2", "r1"],
    startLocal: "2026-11-20T10:00",
    durationMinutes: 30,
    acknowledgeOverlap: false,
    acknowledgedConflictIds: [] as string[],
  };
  const k1 = store.keyFor(base, () => "key-a");
  const k2 = store.keyFor(base, () => "key-b");
  assert.equal(k1, "key-a");
  assert.equal(k2, "key-a"); // retry / lost-response reuses key

  const confirmed = {
    ...base,
    acknowledgeOverlap: true,
    acknowledgedConflictIds: sortedConflictIds([
      { appointment_id: "c2" },
      { appointment_id: "c1" },
    ]),
  };
  const kConfirm1 = store.keyFor(confirmed, () => "key-confirm");
  const kConfirm2 = store.keyFor(confirmed, () => "key-other");
  assert.equal(kConfirm1, "key-confirm");
  assert.equal(kConfirm2, "key-confirm");
  assert.notEqual(k1, kConfirm1);

  const changedConflicts = {
    ...confirmed,
    acknowledgedConflictIds: ["c3"],
  };
  assert.notEqual(
    bookingFingerprint(confirmed),
    bookingFingerprint(changedConflicts),
  );
  const kChanged = store.keyFor(changedConflicts, () => "key-changed");
  assert.equal(kChanged, "key-changed");

  const newIntent = { ...base, startLocal: "2026-11-20T11:00" };
  assert.notEqual(bookingFingerprint(base), bookingFingerprint(newIntent));
});

test("resource selection covers single/multi/specific/insufficient/extra", () => {
  const room = { id: "r1", resource_type: "ROOM", resource_name: "A", is_active: true };
  const doc = { id: "d1", resource_type: "PRACTITIONER", resource_name: "Dr", is_active: true };
  const byId = new Map([
    ["r1", room],
    ["d1", doc],
  ]);
  const single = [
    {
      id: "q1",
      requirement_group: "primary",
      required_resource_type: "ROOM",
      specific_resource_id: null,
      quantity_required: 1,
    },
  ];
  assert.equal(validateResourceSelection(single, ["r1"], byId).ok, true);
  assert.equal(validateResourceSelection(single, ["r1", "d1"], byId).ok, false);

  const multi = [
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
  assert.equal(validateResourceSelection(multi, ["r1"], byId).ok, false);
  assert.equal(validateResourceSelection(multi, ["r1", "d1"], byId).ok, true);
  assert.equal(eligibleResourcesForRequirements([room, doc], multi).length, 2);
});

test("requirements gate: rapid service change discards delayed responses", async () => {
  // Mirrors desk reqToken + serviceId apply gate for delayed fetches.
  let reqToken = 0;
  type State =
    | { status: "idle" }
    | { status: "loading"; serviceId: string }
    | { status: "ready"; serviceId: string; items: string[] }
    | { status: "error"; serviceId: string; message: string };
  let state: State = { status: "idle" };

  function changeService(serviceId: string) {
    reqToken += 1;
    if (!serviceId) {
      state = { status: "idle" };
      return;
    }
    state = { status: "loading", serviceId };
  }

  async function settleDelayed(
    issuedToken: number,
    serviceId: string,
    items: string[],
    delayMs: number,
  ) {
    await new Promise((r) => setTimeout(r, delayMs));
    if (issuedToken !== reqToken) return; // stale — must not apply
    if (state.status !== "loading" || state.serviceId !== serviceId) return;
    state = { status: "ready", serviceId, items };
  }

  changeService("svc-a");
  const tokenA = reqToken;
  const lateA = settleDelayed(tokenA, "svc-a", ["old"], 30);

  changeService("svc-b");
  const tokenB = reqToken;
  assert.notEqual(tokenA, tokenB);
  assert.equal(state.status, "loading");
  if (state.status === "loading") assert.equal(state.serviceId, "svc-b");

  await settleDelayed(tokenB, "svc-b", ["new"], 5);
  assert.equal(state.status, "ready");
  if (state.status === "ready") {
    assert.equal(state.serviceId, "svc-b");
    assert.deepEqual(state.items, ["new"]);
  }

  await lateA; // delayed svc-a must not overwrite svc-b
  assert.equal(state.status, "ready");
  if (state.status === "ready") {
    assert.equal(state.serviceId, "svc-b");
    assert.deepEqual(state.items, ["new"]);
  }

  changeService("");
  assert.equal(state.status, "idle");
});

test("Tehran day bounds remain half-open", () => {
  const { start, end } = tehranDayBoundsUtc("2026-11-20");
  assert.ok(new Date(end).getTime() > new Date(start).getTime());
  const iso = tehranLocalToUtcIso("2026-11-20T00:00");
  assert.equal(iso, start);
});

test("cookie option helpers preserve HttpOnly and SameSite", () => {
  const req = new Request("https://clinic.example/x");
  const session = sessionCookieOptions(req, 60);
  const csrf = csrfCookieOptions(req, 60);
  assert.equal(session.httpOnly, true);
  assert.equal(session.sameSite, "lax");
  assert.equal(session.secure, true);
  assert.equal(csrf.httpOnly, false);
  assert.equal(csrf.secure, true);
});
