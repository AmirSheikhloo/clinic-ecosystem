import assert from "node:assert/strict";
import test from "node:test";
import { proxyV1, resolveUpstreamPath } from "./bff-proxy.ts";
import { CSRF_COOKIE, SESSION_COOKIE } from "./constants.ts";

const ORIGIN = "http://127.0.0.1:3100";

function withEnv<T>(fn: () => Promise<T>): Promise<T> {
  const previous = { ...process.env };
  Object.assign(process.env, {
    CLINIC_ENV: "test",
    CLINIC_BETA_PANEL_ENABLED: "1",
    CLINIC_API_BASE_URL: "http://127.0.0.1:9",
  });
  return fn().finally(() => {
    process.env = previous;
  });
}

type Captured = { url: string; init: RequestInit };

async function withFetch<T>(
  respond: (call: Captured) => Response,
  run: (calls: Captured[]) => Promise<T>,
): Promise<T> {
  const original = globalThis.fetch;
  const calls: Captured[] = [];
  globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
    const call = { url: String(input), init: init ?? {} };
    calls.push(call);
    return respond(call);
  }) as typeof fetch;
  try {
    return await run(calls);
  } finally {
    globalThis.fetch = original;
  }
}

function req(path: string, init: RequestInit = {}, cookies = true, csrf = true) {
  const headers = new Headers(init.headers);
  if (cookies) headers.set("cookie", `${SESSION_COOKIE}=jwt-token; ${CSRF_COOKIE}=csrf-1`);
  if (csrf && init.method && init.method !== "GET") {
    headers.set("x-csrf-token", "csrf-1");
    headers.set("origin", ORIGIN);
  }
  return new Request(`${ORIGIN}${path}`, { ...init, headers });
}

test("resolveUpstreamPath allowlists roots and rejects traversal and auth", () => {
  assert.equal(resolveUpstreamPath(["patients", "directory"]), "/api/v1/patients/directory");
  assert.equal(
    resolveUpstreamPath(["catalog", "admin", "services", "0191-aa"]),
    "/api/v1/catalog/admin/services/0191-aa",
  );
  for (const bad of [
    undefined,
    [],
    ["auth", "login"],
    ["health"],
    ["patients", ".."],
    ["patients", "a/b"],
    ["patients", "%2e%2e"],
    ["patients", "x".repeat(65)],
    ["patients", "a", "b", "c", "d", "e", "f"],
    ["patients", "http://evil.test"],
    ["patients", ""],
  ]) {
    assert.equal(resolveUpstreamPath(bad as string[] | undefined), null, JSON.stringify(bad));
  }
});

test("proxy attaches bearer from cookie, forwards only allowlisted headers, relays ETag", async () => {
  await withEnv(() =>
    withFetch(
      () => new Response(JSON.stringify({ ok: 1 }), { status: 200, headers: { etag: '"3"' } }),
      async (calls) => {
        const response = await proxyV1(
          req("/api/v1/patients/abc?x=1", {
            method: "GET",
            headers: { authorization: "Bearer attacker", "x-forwarded-for": "1.1.1.1", "if-match": '"2"' },
          }),
          ["patients", "abc"],
        );
        assert.equal(response.status, 200);
        assert.equal(response.headers.get("etag"), '"3"');
        assert.equal(calls.length, 1);
        assert.equal(calls[0].url, "http://127.0.0.1:9/api/v1/patients/abc?x=1");
        const sent = new Headers(calls[0].init.headers);
        assert.equal(sent.get("authorization"), "Bearer jwt-token");
        assert.equal(sent.get("x-forwarded-for"), null);
        assert.equal(sent.get("if-match"), '"2"');
      },
    ),
  );
});

test("mutations require CSRF + same origin; blocked requests never reach upstream", async () => {
  await withEnv(() =>
    withFetch(
      () => new Response("{}", { status: 200 }),
      async (calls) => {
        const noCsrf = await proxyV1(
          req("/api/v1/staff", { method: "POST", body: "{}" }, true, false),
          ["staff"],
        );
        assert.equal(noCsrf.status, 403);
        const crossOrigin = await proxyV1(
          new Request(`${ORIGIN}/api/v1/staff`, {
            method: "POST",
            body: "{}",
            headers: {
              cookie: `${SESSION_COOKIE}=t; ${CSRF_COOKIE}=csrf-1`,
              "x-csrf-token": "csrf-1",
              origin: "https://evil.example",
            },
          }),
          ["staff"],
        );
        assert.equal(crossOrigin.status, 403);
        assert.equal(calls.length, 0);
      },
    ),
  );
});

test("mutations forward body, If-Match and Idempotency-Key", async () => {
  await withEnv(() =>
    withFetch(
      () => new Response(JSON.stringify({ id: "1" }), { status: 201, headers: { "idempotent-replay": "true" } }),
      async (calls) => {
        const response = await proxyV1(
          req("/api/v1/staff", {
            method: "POST",
            body: JSON.stringify({ first_name: "A" }),
            headers: { "idempotency-key": "key-1", "if-match": '"7"' },
          }),
          ["staff"],
        );
        assert.equal(response.status, 201);
        assert.equal(response.headers.get("idempotent-replay"), "true");
        assert.equal(calls[0].init.method, "POST");
        assert.equal(calls[0].init.body, JSON.stringify({ first_name: "A" }));
        const sent = new Headers(calls[0].init.headers);
        assert.equal(sent.get("idempotency-key"), "key-1");
        assert.equal(sent.get("if-match"), '"7"');
        assert.equal(sent.get("content-type"), "application/json");
      },
    ),
  );
});

test("unknown roots, oversized bodies and long queries are rejected locally", async () => {
  await withEnv(() =>
    withFetch(
      () => new Response("{}", { status: 200 }),
      async (calls) => {
        assert.equal((await proxyV1(req("/api/v1/auth/login"), ["auth", "login"])).status, 404);
        const big = await proxyV1(
          req("/api/v1/staff", { method: "POST", body: "x".repeat(70 * 1024) }),
          ["staff"],
        );
        assert.equal(big.status, 413);
        const longQuery = await proxyV1(req(`/api/v1/search?q=${"a".repeat(2000)}`), ["search"]);
        assert.equal(longQuery.status, 414);
        assert.equal(calls.length, 0);
      },
    ),
  );
});

test("401 clears cookies; problem bodies are normalised; 204 passes through", async () => {
  await withEnv(async () => {
    await withFetch(
      () => new Response("{}", { status: 401 }),
      async () => {
        const response = await proxyV1(req("/api/v1/staff"), ["staff"]);
        assert.equal(response.status, 401);
        const cookies = response.headers.getSetCookie().join(";");
        assert.match(cookies, new RegExp(`${SESSION_COOKIE}=;`));
        assert.equal(((await response.json()) as { error: string }).error, "session_expired");
      },
    );
    await withFetch(
      () =>
        new Response(
          JSON.stringify({ error: "precondition_failed", message: "stale", current_version: 4 }),
          { status: 412, headers: { "content-type": "application/problem+json" } },
        ),
      async () => {
        const response = await proxyV1(
          req("/api/v1/patients/x", { method: "PATCH", body: "{}" }),
          ["patients", "x"],
        );
        const body = (await response.json()) as { error: string; detail: { current_version: number } };
        assert.equal(response.status, 412);
        assert.equal(body.error, "precondition_failed");
        assert.equal(body.detail.current_version, 4);
      },
    );
    await withFetch(
      () => new Response(JSON.stringify({ detail: [{ loc: ["body"], msg: "bad" }] }), { status: 422 }),
      async () => {
        const body = (await (await proxyV1(req("/api/v1/staff"), ["staff"])).json()) as { error: string };
        assert.equal(body.error, "validation_error");
      },
    );
    await withFetch(
      () => new Response(null, { status: 204 }),
      async () => {
        const response = await proxyV1(
          req("/api/v1/access/roles/abc", { method: "DELETE" }),
          ["access", "roles", "abc"],
        );
        assert.equal(response.status, 204);
      },
    );
  });
});

test("unauthenticated requests are still forwarded without a bearer (upstream decides)", async () => {
  await withEnv(() =>
    withFetch(
      () => new Response("{}", { status: 401 }),
      async (calls) => {
        await proxyV1(req("/api/v1/staff", {}, false), ["staff"]);
        assert.equal(new Headers(calls[0].init.headers).get("authorization"), null);
      },
    ),
  );
});
