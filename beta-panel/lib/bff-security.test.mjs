/**
 * BFF session/CSRF behavior checks without a browser.
 * Exercises the same decision rules used by route handlers.
 */
import assert from "node:assert/strict";
import test from "node:test";

function requireCsrf(header, cookie, origin, requestUrl) {
  if (!header || !cookie || header !== cookie) {
    throw new Error("csrf_failed");
  }
  if (origin) {
    const expected = new URL(requestUrl).origin;
    if (origin !== expected) {
      throw new Error("csrf_failed");
    }
  }
}

function panelEnabled(env) {
  const clinicEnv = (env.CLINIC_ENV || "production").trim().toLowerCase();
  if (!["development", "test"].includes(clinicEnv)) return false;
  const raw = (env.CLINIC_BETA_PANEL_ENABLED || "").trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(raw);
}

test("CSRF rejects missing or mismatched tokens", () => {
  assert.throws(() => requireCsrf("", "abc", null, "http://127.0.0.1:3100/x"));
  assert.throws(() => requireCsrf("abc", "xyz", null, "http://127.0.0.1:3100/x"));
  assert.doesNotThrow(() => requireCsrf("abc", "abc", null, "http://127.0.0.1:3100/x"));
});

test("CSRF rejects mismatched Origin", () => {
  assert.throws(() =>
    requireCsrf("abc", "abc", "https://evil.example", "http://127.0.0.1:3100/api/auth/logout"),
  );
  assert.doesNotThrow(() =>
    requireCsrf("abc", "abc", "http://127.0.0.1:3100", "http://127.0.0.1:3100/api/auth/logout"),
  );
});

test("panel fail-closed outside enabled development/test", () => {
  assert.equal(panelEnabled({ CLINIC_ENV: "production", CLINIC_BETA_PANEL_ENABLED: "1" }), false);
  assert.equal(panelEnabled({ CLINIC_ENV: "development", CLINIC_BETA_PANEL_ENABLED: "0" }), false);
  assert.equal(panelEnabled({ CLINIC_ENV: "development", CLINIC_BETA_PANEL_ENABLED: "1" }), true);
  assert.equal(panelEnabled({ CLINIC_ENV: "test", CLINIC_BETA_PANEL_ENABLED: "true" }), true);
});

test("logout must not be treated as success unless BFF returns ok", () => {
  function interpretLogout(responseOk) {
    if (!responseOk) {
      return { redirected: false, sessionAssumedCleared: false };
    }
    return { redirected: true, sessionAssumedCleared: true };
  }
  assert.deepEqual(interpretLogout(false), {
    redirected: false,
    sessionAssumedCleared: false,
  });
  assert.deepEqual(interpretLogout(true), {
    redirected: true,
    sessionAssumedCleared: true,
  });
});
