import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { CSRF_COOKIE, SESSION_COOKIE } from "./config";

export async function getSessionToken(): Promise<string | null> {
  const jar = await cookies();
  const value = jar.get(SESSION_COOKIE)?.value;
  return value && value.length > 0 ? value : null;
}

export function setSessionCookies(
  response: NextResponse,
  options: { accessToken: string; maxAgeSeconds: number },
): void {
  const secure = process.env.NODE_ENV === "production";
  response.cookies.set(SESSION_COOKIE, options.accessToken, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: options.maxAgeSeconds,
  });
  const csrf = crypto.randomUUID().replace(/-/g, "");
  response.cookies.set(CSRF_COOKIE, csrf, {
    httpOnly: false,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: options.maxAgeSeconds,
  });
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  response.cookies.set(CSRF_COOKIE, "", {
    httpOnly: false,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
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
