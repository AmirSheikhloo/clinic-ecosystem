import { NextResponse } from "next/server";
import { backendBaseUrl, requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError, jsonError, mapUpstream } from "@/lib/api-error";
import { requireCsrf, setSessionCookies } from "@/lib/session";

export async function POST(request: Request) {
  try {
    requireBetaPanelEnabled();
    await requireCsrf(request);
    const body = await request.json();
    const login = String(body.login_identifier || "").trim();
    const password = String(body.password || "");
    if (!login || !password) {
      return jsonError(400, "validation_error", "Login and password are required");
    }
    const upstream = await fetch(`${backendBaseUrl()}/api/v1/auth/login`, {
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
    setSessionCookies(response, {
      accessToken: data.access_token,
      maxAgeSeconds: Number(data.expires_in) || 900,
    });
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}
