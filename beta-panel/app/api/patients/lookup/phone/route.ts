import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { backendFetch, clearSessionCookies, requireCsrf } from "@/lib/session";

/** POST-only shared-phone lookup — never put raw phones in query strings. */
export async function POST(request: Request) {
  try {
    requireBetaPanelEnabled();
    await requireCsrf(request);
    const body = await request.json();
    const upstream = await backendFetch(
      "/api/v1/patients/lookup/phone",
      { method: "POST", body: JSON.stringify(body) },
      request,
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
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    return handleRouteError(err);
  }
}
