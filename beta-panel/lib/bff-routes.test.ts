/**
 * Exercises the ACTUAL BFF handlers used by app/api routes.
 */
import assert from "node:assert/strict";
import test from "node:test";
import {
  handleAppointmentsGet,
  handleAppointmentsPost,
  handleCsrfGet,
  handleLoginPost,
  handleLogoutPost,
} from "./bff-handlers.ts";
import { CSRF_COOKIE, SESSION_COOKIE } from "./constants.ts";

function jar(entries: Record<string, string> = {}) {
  const map = new Map(Object.entries(entries).map(([k, v]) => [k, { value: v }]));
  return {
    get: (name: string) => map.get(name),
  };
}

const enabledEnv = {
  CLINIC_ENV: "test",
  CLINIC_BETA_PANEL_ENABLED: "1",
  CLINIC_API_BASE_URL: "http://127.0.0.1:9",
};

test("login: CSRF / origin / cookie creation / no token in JSON / disabled panel", async () => {
  const prev = { ...process.env };
  Object.assign(process.env, enabledEnv);
  try {
    const missing = await handleLoginPost(
      new Request("http://127.0.0.1:3100/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json", origin: "http://127.0.0.1:3100" },
        body: JSON.stringify({ login_identifier: "a", password: "b" }),
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
    );
    assert.equal(missing.status, 403);

    const cross = await handleLoginPost(
      new Request("http://127.0.0.1:3100/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": "csrf-token",
          origin: "https://evil.example",
        },
        body: JSON.stringify({ login_identifier: "a", password: "b" }),
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
    );
    assert.equal(cross.status, 403);

    const fetchOk: typeof fetch = async () =>
      new Response(
        JSON.stringify({
          access_token: "secret-access-token",
          account_id: "acc",
          tenant_id: "ten",
          expires_in: 900,
        }),
        { status: 200 },
      );
    const ok = await handleLoginPost(
      new Request("http://127.0.0.1:3100/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": "csrf-token",
          origin: "http://127.0.0.1:3100",
        },
        body: JSON.stringify({ login_identifier: "a", password: "b" }),
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
      fetchOk,
    );
    assert.equal(ok.status, 200);
    const body = await ok.json();
    assert.equal(body.account_id, "acc");
    assert.equal("access_token" in body, false);
    assert.equal(ok.cookies.get(SESSION_COOKIE)?.value, "secret-access-token");
    assert.equal(ok.cookies.get(SESSION_COOKIE)?.httpOnly, true);
    assert.ok(ok.cookies.get(CSRF_COOKIE)?.value);

    process.env.CLINIC_BETA_PANEL_ENABLED = "0";
    const disabled = await handleLoginPost(
      new Request("http://127.0.0.1:3100/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": "csrf-token",
          origin: "http://127.0.0.1:3100",
        },
        body: JSON.stringify({ login_identifier: "a", password: "b" }),
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
    );
    assert.equal(disabled.status, 503);
  } finally {
    process.env = prev;
  }
});

test("logout clears cookies only when CSRF succeeds", async () => {
  const prev = { ...process.env };
  Object.assign(process.env, enabledEnv);
  try {
    const bad = await handleLogoutPost(
      new Request("http://127.0.0.1:3100/api/auth/logout", {
        method: "POST",
        headers: { origin: "http://127.0.0.1:3100" },
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
    );
    assert.equal(bad.status, 403);

    const ok = await handleLogoutPost(
      new Request("http://127.0.0.1:3100/api/auth/logout", {
        method: "POST",
        headers: {
          "x-csrf-token": "csrf-token",
          origin: "http://127.0.0.1:3100",
        },
      }),
      jar({ [CSRF_COOKIE]: "csrf-token" }),
    );
    assert.equal(ok.status, 200);
    assert.equal(ok.cookies.get(SESSION_COOKIE)?.value, "");
    assert.equal(ok.cookies.get(CSRF_COOKIE)?.value, "");
  } finally {
    process.env = prev;
  }
});

test("csrf bootstrap + appointments expired/missing auth + unexpected upstream", async () => {
  const prev = { ...process.env };
  Object.assign(process.env, enabledEnv);
  try {
    const csrf = await handleCsrfGet(new Request("http://127.0.0.1:3100/api/auth/csrf"));
    assert.equal(csrf.status, 200);
    assert.ok(csrf.cookies.get(CSRF_COOKIE)?.value);

    const expired = await handleAppointmentsGet(
      new Request(
        "http://127.0.0.1:3100/api/appointments?start_at_utc=2026-11-20T00:00:00Z&end_at_utc=2026-11-21T00:00:00Z",
      ),
      jar({ [SESSION_COOKIE]: "tok" }),
      async () =>
        new Response(JSON.stringify({ detail: { error: "invalid_token" } }), {
          status: 401,
        }),
    );
    assert.equal(expired.status, 401);
    assert.equal((await expired.json()).error, "session_expired");
    assert.equal(expired.cookies.get(SESSION_COOKIE)?.value, "");

    const unexpected = await handleAppointmentsGet(
      new Request(
        "http://127.0.0.1:3100/api/appointments?start_at_utc=2026-11-20T00:00:00Z&end_at_utc=2026-11-21T00:00:00Z",
      ),
      jar({ [SESSION_COOKIE]: "tok" }),
      async () => new Response("nope", { status: 502 }),
    );
    assert.equal(unexpected.status, 502);
    assert.equal((await unexpected.json()).error, "upstream_error");

    const postMissingCsrf = await handleAppointmentsPost(
      new Request("http://127.0.0.1:3100/api/appointments", {
        method: "POST",
        headers: { "content-type": "application/json", origin: "http://127.0.0.1:3100" },
        body: JSON.stringify({}),
      }),
      jar({ [CSRF_COOKIE]: "csrf-token", [SESSION_COOKIE]: "tok" }),
    );
    assert.equal(postMissingCsrf.status, 403);
  } finally {
    process.env = prev;
  }
});
