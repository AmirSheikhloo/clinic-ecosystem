/**
 * Testable BFF handlers used by app/api route modules.
 * Cookie jar access is injected so tests exercise the real security path.
 */
import { NextResponse } from "next/server";
import { handleRouteError, jsonError, mapUpstream } from "./api-error";
import { backendBaseUrl, CSRF_COOKIE, requireBetaPanelEnabled, SESSION_COOKIE } from "./config";
import { csrfCookieOptions, sessionCookieOptions } from "./cookies";
import { evaluateCsrf } from "./csrf";

export type CookieReader = {
  get: (name: string) => { value: string } | undefined;
};

export async function handleCsrfGet(request: Request): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    const csrf = crypto.randomUUID().replace(/-/g, "");
    const response = NextResponse.json({ ok: true });
    response.cookies.set(CSRF_COOKIE, csrf, csrfCookieOptions(request, 60 * 60));
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}

export async function handleLoginPost(
  request: Request,
  cookies: CookieReader,
  fetchImpl: typeof fetch = fetch,
): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    evaluateCsrf({
      headerToken: request.headers.get("x-csrf-token"),
      cookieToken: cookies.get(CSRF_COOKIE)?.value,
      origin: request.headers.get("origin"),
      requestUrl: request.url,
      hostHeader: request.headers.get("host"),
    });
    const body = await request.json();
    const login = String(body.login_identifier || "").trim();
    const password = String(body.password || "");
    if (!login || !password) {
      return jsonError(400, "validation_error", "Login and password are required");
    }
    const upstream = await fetchImpl(`${backendBaseUrl()}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login_identifier: login, password }),
      cache: "no-store",
    });
    const data = await upstream.json().catch(() => ({}));
    if (!upstream.ok) {
      return mapUpstream(upstream, data);
    }
    const response = NextResponse.json({
      account_id: data.account_id,
      tenant_id: data.tenant_id,
      expires_in: data.expires_in,
    });
    response.cookies.set(
      SESSION_COOKIE,
      String(data.access_token || ""),
      sessionCookieOptions(request, Number(data.expires_in) || 900),
    );
    const csrf = crypto.randomUUID().replace(/-/g, "");
    response.cookies.set(
      CSRF_COOKIE,
      csrf,
      csrfCookieOptions(request, Number(data.expires_in) || 900),
    );
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}

export async function handleLogoutPost(
  request: Request,
  cookies: CookieReader,
): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    evaluateCsrf({
      headerToken: request.headers.get("x-csrf-token"),
      cookieToken: cookies.get(CSRF_COOKIE)?.value,
      origin: request.headers.get("origin"),
      requestUrl: request.url,
      hostHeader: request.headers.get("host"),
    });
    const response = NextResponse.json({ ok: true });
    response.cookies.set(SESSION_COOKIE, "", sessionCookieOptions(request, 0));
    response.cookies.set(CSRF_COOKIE, "", csrfCookieOptions(request, 0));
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}

export async function handleAppointmentsGet(
  request: Request,
  cookies: CookieReader,
  fetchImpl: typeof fetch = fetch,
): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    const { searchParams } = new URL(request.url);
    const start = searchParams.get("start_at_utc") || "";
    const end = searchParams.get("end_at_utc") || "";
    const token = cookies.get(SESSION_COOKIE)?.value;
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const upstream = await fetchImpl(
      `${backendBaseUrl()}/api/v1/appointments?start_at_utc=${encodeURIComponent(start)}&end_at_utc=${encodeURIComponent(end)}`,
      { headers, cache: "no-store" },
    );
    const data = await upstream.json().catch(() => ({}));
    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      response.cookies.set(SESSION_COOKIE, "", sessionCookieOptions(request, 0));
      response.cookies.set(CSRF_COOKIE, "", csrfCookieOptions(request, 0));
      return response;
    }
    if (!upstream.ok) {
      return mapUpstream(upstream, data);
    }
    return NextResponse.json(data);
  } catch (err) {
    return handleRouteError(err);
  }
}

export async function handleAppointmentsPost(
  request: Request,
  cookies: CookieReader,
  fetchImpl: typeof fetch = fetch,
): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    evaluateCsrf({
      headerToken: request.headers.get("x-csrf-token"),
      cookieToken: cookies.get(CSRF_COOKIE)?.value,
      origin: request.headers.get("origin"),
      requestUrl: request.url,
      hostHeader: request.headers.get("host"),
    });
    const body = await request.json();
    const idempotencyKey = String(
      request.headers.get("idempotency-key")
        || body.idempotency_key
        || crypto.randomUUID(),
    );
    const token = cookies.get(SESSION_COOKIE)?.value;
    const headers = new Headers({
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const upstream = await fetchImpl(`${backendBaseUrl()}/api/v1/appointments`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await upstream.json().catch(() => ({}));
    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      response.cookies.set(SESSION_COOKIE, "", sessionCookieOptions(request, 0));
      response.cookies.set(CSRF_COOKIE, "", csrfCookieOptions(request, 0));
      return response;
    }
    if (!upstream.ok) {
      return mapUpstream(upstream, data);
    }
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    return handleRouteError(err);
  }
}
