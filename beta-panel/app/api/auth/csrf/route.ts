import { NextResponse } from "next/server";
import { CSRF_COOKIE, requireBetaPanelEnabled } from "@/lib/config";
import { handleRouteError } from "@/lib/api-error";

/** Bootstrap a Readable CSRF cookie for same-origin state-changing requests. */
export async function GET() {
  try {
    requireBetaPanelEnabled();
    const csrf = crypto.randomUUID().replace(/-/g, "");
    const response = NextResponse.json({ ok: true });
    response.cookies.set(CSRF_COOKIE, csrf, {
      httpOnly: false,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60,
    });
    return response;
  } catch (err) {
    return handleRouteError(err);
  }
}
