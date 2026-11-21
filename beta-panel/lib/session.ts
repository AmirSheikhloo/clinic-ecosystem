import { NextResponse } from "next/server";
import { CSRF_COOKIE, SESSION_COOKIE } from "./config";
import { csrfCookieOptions, sessionCookieOptions } from "./cookies";
import { CsrfError, evaluateCsrf } from "./csrf";
import { cookiesFromRequest } from "./request-cookies";

export { evaluateCsrf, CsrfError } from "./csrf";

/** Prefer request Cookie header when available (Route Handlers). */
export async function getSessionToken(request?: Request): Promise<string | null> {
  if (request) {
    const value = cookiesFromRequest(request).get(SESSION_COOKIE)?.value;
    return value && value.length > 0 ? value : null;
  }
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const value = jar.get(SESSION_COOKIE)?.value;
  return value && value.length > 0 ? value : null;
}

export function setSessionCookies(
  response: NextResponse,
  request: Request,
  options: { accessToken: string; maxAgeSeconds: number },
): void {
  response.cookies.set(
    SESSION_COOKIE,
    options.accessToken,
    sessionCookieOptions(request, options.maxAgeSeconds),
  );
  const csrf = crypto.randomUUID().replace(/-/g, "");
  response.cookies.set(
    CSRF_COOKIE,
    csrf,
    csrfCookieOptions(request, options.maxAgeSeconds),
  );
}

export function clearSessionCookies(response: NextResponse, request: Request): void {
  response.cookies.set(SESSION_COOKIE, "", sessionCookieOptions(request, 0));
  response.cookies.set(CSRF_COOKIE, "", csrfCookieOptions(request, 0));
}

export async function requireCsrf(request: Request): Promise<void> {
  const jar = cookiesFromRequest(request);
  try {
    evaluateCsrf({
      headerToken: request.headers.get("x-csrf-token"),
      cookieToken: jar.get(CSRF_COOKIE)?.value,
      origin: request.headers.get("origin"),
      requestUrl: request.url,
      hostHeader: request.headers.get("host"),
    });
  } catch (err) {
    if (err instanceof CsrfError) {
      throw new Error("csrf_failed");
    }
    throw err;
  }
}

export async function backendFetch(
  path: string,
  init: RequestInit = {},
  request?: Request,
): Promise<Response> {
  const { backendBaseUrl } = await import("./config");
  const base = backendBaseUrl();
  const token = await getSessionToken(request);
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${base}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

/** True when the Set-Cookie header marks the session cookie HttpOnly. */
export function sessionCookieIsHttpOnly(setCookieHeaders: string[]): boolean {
  return setCookieHeaders.some((header) => {
    const lower = header.toLowerCase();
    return lower.includes("ce_beta_session=") && lower.includes("httponly");
  });
}
