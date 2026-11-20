import { NextResponse } from "next/server";
import { requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError } from "@/lib/api-error";
import { clearSessionCookies, requireCsrf } from "@/lib/session";

export async function POST(request: Request) {
  try {
    requireBetaPanelEnabled();
    await requireCsrf(request);
    const response = NextResponse.json({ ok: true });
    clearSessionCookies(response, request);
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}
