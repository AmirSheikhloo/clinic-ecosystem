import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { backendFetch, clearSessionCookies, requireCsrf } from "@/lib/session";

async function maybeExpire(request: Request, upstream: Response, data: unknown) {
  if (upstream.status === 401) {
    const response = jsonError(401, "session_expired", "Session expired");
    clearSessionCookies(response, request);
    return response;
  }
  if (!upstream.ok) {
    return mapUpstream(upstream, data);
  }
  return NextResponse.json(data, { status: upstream.status });
}

export async function GET(request: Request) {
  try {
    requireBetaPanelEnabled();
    const { searchParams } = new URL(request.url);
    const q = searchParams.get("q") || "";
    const limit = searchParams.get("limit") || "20";
    const offset = searchParams.get("offset") || "0";
    const query = new URLSearchParams();
    if (q) query.set("q", q);
    query.set("limit", limit);
    query.set("offset", offset);
    const upstream = await backendFetch(
      `/api/v1/patients?${query.toString()}`,
      {},
      request,
    );
    const data = await upstream.json().catch(() => ({}));
    return maybeExpire(request, upstream, data);
  } catch (err) {
    return handleRouteError(err);
  }
}

export async function POST(request: Request) {
  try {
    requireBetaPanelEnabled();
    await requireCsrf(request);
    const body = await request.json();
    const upstream = await backendFetch(
      "/api/v1/patients",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      request,
    );
    const data = await upstream.json().catch(() => ({}));
    return maybeExpire(request, upstream, data);
  } catch (err) {
    return handleRouteError(err);
  }
}
