import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { backendFetch, clearSessionCookies } from "@/lib/session";

export async function GET(request: Request) {
  try {
    requireBetaPanelEnabled();
    const upstream = await backendFetch("/api/v1/catalog/services");
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
