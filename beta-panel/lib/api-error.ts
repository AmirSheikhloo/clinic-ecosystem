import { NextResponse } from "next/server";
import { BetaPanelConfigError } from "./config";
import { CookieTransportError } from "./cookies";
import { CsrfError } from "./csrf";

export function jsonError(status: number, error: string, message: string) {
  return NextResponse.json({ error, message }, { status });
}

export function mapUpstream(response: Response, body: unknown) {
  if (
    typeof body === "object"
    && body !== null
    && "detail" in body
  ) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "object" && detail !== null && "error" in detail) {
      const d = detail as { error: string; message?: string };
      return NextResponse.json(
        { error: d.error, message: d.message || d.error, detail },
        { status: response.status },
      );
    }
  }
  return NextResponse.json(
    { error: "upstream_error", message: "Upstream request failed" },
    { status: response.status },
  );
}

export function handleRouteError(err: unknown) {
  if (err instanceof BetaPanelConfigError) {
    return jsonError(503, "panel_disabled", err.message);
  }
  if (err instanceof CookieTransportError) {
    return jsonError(503, "unsafe_cookie_transport", err.message);
  }
  if (
    err instanceof CsrfError
    || (err instanceof Error && err.message === "csrf_failed")
  ) {
    return jsonError(403, "csrf_failed", "CSRF validation failed");
  }
  return jsonError(500, "internal_error", "Unexpected server error");
}
