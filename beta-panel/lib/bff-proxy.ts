/**
 * Allowlisted generic BFF proxy for /api/v1/* operations endpoints.
 *
 * The browser never receives the bearer token; this layer attaches it from the
 * HttpOnly cookie, enforces CSRF/Origin checks for mutations and restricts the
 * reachable upstream surface to known path roots (no SSRF, no auth routes).
 */
import { NextResponse } from "next/server";
import { handleRouteError, jsonError, mapUpstream } from "./api-error";
import { requireBetaPanelEnabled } from "./config";
import { backendFetch, clearSessionCookies, requireCsrf } from "./session";

export const PROXY_ROOTS = [
  "patients",
  "staff",
  "access",
  "audit",
  "catalog",
  "appointments",
  "dashboard",
  "search",
] as const;

const SEGMENT = /^[A-Za-z0-9_-]{1,64}$/;
const MAX_SEGMENTS = 6;
const MAX_QUERY_LENGTH = 1500;
const MAX_BODY_BYTES = 64 * 1024;
const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const FORWARD_REQUEST_HEADERS = ["if-match", "idempotency-key"] as const;
const FORWARD_RESPONSE_HEADERS = ["etag", "idempotent-replay"] as const;

export function resolveUpstreamPath(segments: string[] | undefined): string | null {
  if (!segments || segments.length === 0 || segments.length > MAX_SEGMENTS) return null;
  if (!segments.every((segment) => SEGMENT.test(segment))) return null;
  if (!(PROXY_ROOTS as readonly string[]).includes(segments[0])) return null;
  return `/api/v1/${segments.join("/")}`;
}

export async function proxyV1(
  request: Request,
  segments: string[] | undefined,
): Promise<NextResponse> {
  try {
    requireBetaPanelEnabled();
    const path = resolveUpstreamPath(segments);
    if (!path) return jsonError(404, "not_found", "Unknown resource");

    const method = request.method.toUpperCase();
    const mutating = MUTATING.has(method);
    if (mutating) await requireCsrf(request);

    const url = new URL(request.url);
    if (url.search.length > MAX_QUERY_LENGTH) {
      return jsonError(414, "query_too_long", "Query string is too long");
    }

    const headers = new Headers();
    for (const name of FORWARD_REQUEST_HEADERS) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    let body: string | undefined;
    if (mutating) {
      body = await request.text();
      if (new TextEncoder().encode(body).length > MAX_BODY_BYTES) {
        return jsonError(413, "payload_too_large", "Request body is too large");
      }
      if (body) headers.set("Content-Type", "application/json");
    }

    const upstream = await backendFetch(
      `${path}${url.search}`,
      { method, headers, body: body || undefined },
      request,
    );

    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      clearSessionCookies(response, request);
      return response;
    }
    if (upstream.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    const data = await upstream.json().catch(() => ({}));
    if (!upstream.ok) return mapUpstream(upstream, data);

    const response = NextResponse.json(data, { status: upstream.status });
    for (const name of FORWARD_RESPONSE_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) response.headers.set(name, value);
    }
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}
