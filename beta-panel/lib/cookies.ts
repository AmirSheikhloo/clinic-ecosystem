/**
 * Cookie Secure policy for the development-only Beta panel.
 *
 * - HTTPS URL → Secure=true
 * - Explicitly authorized HTTP loopback (127.0.0.1 / localhost / ::1) → Secure=false
 * - Any other HTTP host → fail closed (throws)
 * - x-forwarded-proto is ignored for security decisions (user-controlled)
 */

export class CookieTransportError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CookieTransportError";
  }
}

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

export function isLoopbackHostname(hostname: string): boolean {
  const host = hostname.trim().toLowerCase().replace(/\.$/, "");
  if (LOOPBACK_HOSTS.has(host)) return true;
  // Strip optional IPv6 brackets already handled; reject spoofed "localhost.evil"
  return false;
}

/**
 * Decide Secure flag from the request URL only.
 * Never trusts forwarding headers.
 */
export function cookieSecureFromRequest(request: Request): boolean {
  const url = new URL(request.url);
  if (url.protocol === "https:") {
    return true;
  }
  if (url.protocol === "http:" && isLoopbackHostname(url.hostname)) {
    return false;
  }
  throw new CookieTransportError(
    "Beta panel cookies refuse non-loopback HTTP transports",
  );
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
