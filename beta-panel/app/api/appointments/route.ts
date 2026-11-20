import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { backendFetch, clearSessionCookies, requireCsrf } from "@/lib/session";

export async function GET(request: Request) {
  try {
    requireBetaPanelEnabled();
    const { searchParams } = new URL(request.url);
    const start = searchParams.get("start_at_utc") || "";
    const end = searchParams.get("end_at_utc") || "";
    const upstream = await backendFetch(
      `/api/v1/appointments?start_at_utc=${encodeURIComponent(start)}&end_at_utc=${encodeURIComponent(end)}`,
    );
    const data = await upstream.json().catch(() => ({}));
    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      clearSessionCookies(response, request);
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

export async function POST(request: Request) {
  try {
    requireBetaPanelEnabled();
    await requireCsrf(request);
    const body = await request.json();
    const idempotencyKey = String(
      request.headers.get("idempotency-key")
        || body.idempotency_key
        || crypto.randomUUID(),
    );
    const upstream = await backendFetch("/api/v1/appointments", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    });
    const data = await upstream.json().catch(() => ({}));
    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      clearSessionCookies(response, request);
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
