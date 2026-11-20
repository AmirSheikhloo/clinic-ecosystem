/**
 * Cookie Secure flag must follow the actual transport.
 * HTTPS (or x-forwarded-proto=https) → Secure=true.
 * HTTP loopback (npm run start / next start) → Secure=false so browsers accept cookies.
 * Never weakens Secure for real HTTPS deployments.
 */
export function cookieSecureFromRequest(request: Request): boolean {
  const url = new URL(request.url);
  if (url.protocol === "https:") {
    return true;
  }
  const forwarded = (request.headers.get("x-forwarded-proto") || "")
    .split(",")[0]
    .trim()
    .toLowerCase();
  return forwarded === "https";
}

export function sessionCookieOptions(request: Request, maxAge: number) {
  return {
    httpOnly: true as const,
    sameSite: "lax" as const,
    secure: cookieSecureFromRequest(request),
    path: "/",
    maxAge,
  };
}

export function csrfCookieOptions(request: Request, maxAge: number) {
  return {
    httpOnly: false as const,
    sameSite: "lax" as const,
    secure: cookieSecureFromRequest(request),
    path: "/",
    maxAge,
  };
}
