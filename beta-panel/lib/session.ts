import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { CSRF_COOKIE, SESSION_COOKIE } from "./config";
import { csrfCookieOptions, sessionCookieOptions } from "./cookies";

export async function getSessionToken(): Promise<string | null> {
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
  const header = request.headers.get("x-csrf-token") || "";
  const jar = await cookies();
  const cookie = jar.get(CSRF_COOKIE)?.value || "";
  if (!header || !cookie || header !== cookie) {
    throw new Error("csrf_failed");
  }
  const origin = request.headers.get("origin");
  if (origin) {
    const expected = new URL(request.url).origin;
    if (origin !== expected) {
      throw new Error("csrf_failed");
    }
  }
}

export async function backendFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const { backendBaseUrl } = await import("./config");
  const base = backendBaseUrl();
  const token = await getSessionToken();
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
