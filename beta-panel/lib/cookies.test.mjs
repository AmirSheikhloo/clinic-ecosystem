import assert from "node:assert/strict";
import test from "node:test";

function cookieSecureFromRequest(request) {
  const url = new URL(request.url);
  if (url.protocol === "https:") return true;
  const forwarded = (request.headers.get("x-forwarded-proto") || "")
    .split(",")[0]
    .trim()
    .toLowerCase();
  return forwarded === "https";
}

test("HTTP loopback does not force Secure (npm start / next start)", () => {
  const req = new Request("http://127.0.0.1:3100/api/auth/login");
  assert.equal(cookieSecureFromRequest(req), false);
});

test("HTTPS requests set Secure=true", () => {
  const req = new Request("https://clinic.example/api/auth/login");
  assert.equal(cookieSecureFromRequest(req), true);
});

test("x-forwarded-proto=https sets Secure=true behind TLS terminator", () => {
  const req = new Request("http://127.0.0.1:3100/api/auth/login", {
    headers: { "x-forwarded-proto": "https" },
  });
  assert.equal(cookieSecureFromRequest(req), true);
});
