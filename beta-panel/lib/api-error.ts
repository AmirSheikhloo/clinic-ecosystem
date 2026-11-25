import { NextResponse } from "next/server";
import { BetaPanelConfigError } from "./config";
import { CookieTransportError } from "./cookies";
import { CsrfError } from "./csrf";

export function jsonError(status: number, error: string, message: string) {
  return NextResponse.json({ error, message }, { status });
}

type Problem = { error?: unknown; message?: unknown };

export function mapUpstream(response: Response, body: unknown) {
  if (typeof body === "object" && body !== null) {
    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === "object" && detail !== null && !Array.isArray(detail) && "error" in detail) {
      const d = detail as { error: string; message?: string };
      return NextResponse.json(
        { error: d.error, message: d.message || d.error, detail },
        { status: response.status },
      );
    }
    const problem = record as Problem;
    if (typeof problem.error === "string") {
      return NextResponse.json(
        {
          error: problem.error,
          message: typeof problem.message === "string" ? problem.message : problem.error,
          detail: record,
        },
        { status: response.status },
      );
    }
    if (Array.isArray(detail)) {
      return NextResponse.json(
        { error: "validation_error", message: "ورودی نامعتبر است" },
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
