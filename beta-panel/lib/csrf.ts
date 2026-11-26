/** Pure CSRF / Origin evaluation used by the BFF session layer. */

export class CsrfError extends Error {
  constructor(message = "csrf_failed") {
    super(message);
    this.name = "CsrfError";
  }
}

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

/** Same-origin for this loopback-only panel, treating localhost ≡ 127.0.0.1. */
export function originsMatch(
  originHeader: string,
  requestUrl: string,
  hostHeader?: string | null,
): boolean {
  let requestOrigin: string;
  try {
    requestOrigin = new URL(requestUrl).origin;
  } catch {
    return false;
  }
  if (originHeader === requestOrigin) return true;

  if (hostHeader) {
    try {
      const proto = new URL(requestUrl).protocol;
      const fromHost = `${proto}//${hostHeader}`;
      if (originHeader === fromHost) return true;
    } catch {
      /* ignore */
    }
  }

  try {
    const a = new URL(originHeader);
    const b = new URL(requestOrigin);
    if (a.protocol !== b.protocol) return false;
    if (a.port !== b.port) return false;
    return LOOPBACK_HOSTS.has(a.hostname) && LOOPBACK_HOSTS.has(b.hostname);
  } catch {
    return false;
  }
}

export function evaluateCsrf(options: {
  headerToken: string | null | undefined;
  cookieToken: string | null | undefined;
  origin: string | null | undefined;
  requestUrl: string;
  hostHeader?: string | null | undefined;
}): void {
  const header = (options.headerToken || "").trim();
  const cookie = (options.cookieToken || "").trim();
  if (!header || !cookie || header !== cookie) {
    throw new CsrfError("csrf_failed");
  }
  const origin = (options.origin || "").trim();
  if (origin) {
    if (!originsMatch(origin, options.requestUrl, options.hostHeader)) {
      throw new CsrfError("csrf_failed");
    }
  }
}
