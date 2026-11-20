import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { backendFetch, clearSessionCookies, getSessionToken } from "@/lib/session";

export async function GET() {
  try {
    requireBetaPanelEnabled();
    const token = await getSessionToken();
    if (!token) {
      return jsonError(401, "authentication_required", "Authentication required");
    }
    const upstream = await backendFetch("/api/v1/auth/me");
    const data = await upstream.json().catch(() => ({}));
    if (upstream.status === 401) {
      const response = jsonError(401, "session_expired", "Session expired");
      clearSessionCookies(response);
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
