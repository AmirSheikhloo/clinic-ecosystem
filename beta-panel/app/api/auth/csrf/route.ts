import { NextResponse } from "next/server";
import { CSRF_COOKIE, requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError } from "@/lib/api-error";
import { csrfCookieOptions } from "@/lib/cookies";

/** Bootstrap a Readable CSRF cookie for same-origin state-changing requests. */
export async function GET(request: Request) {
  try {
    requireBetaPanelEnabled();
    const csrf = crypto.randomUUID().replace(/-/g, "");
    const response = NextResponse.json({ ok: true });
    response.cookies.set(CSRF_COOKIE, csrf, csrfCookieOptions(request, 60 * 60));
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}
