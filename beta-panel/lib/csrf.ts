/** Pure CSRF / Origin evaluation used by the BFF session layer. */

export class CsrfError extends Error {
  constructor(message = "csrf_failed") {
    super(message);
    this.name = "CsrfError";
  }
}

export function evaluateCsrf(options: {
  headerToken: string | null | undefined;
  cookieToken: string | null | undefined;
  origin: string | null | undefined;
  requestUrl: string;
}): void {
  const header = (options.headerToken || "").trim();
  const cookie = (options.cookieToken || "").trim();
  if (!header || !cookie || header !== cookie) {
    throw new CsrfError("csrf_failed");
  }
  const origin = (options.origin || "").trim();
  if (origin) {
    const expected = new URL(options.requestUrl).origin;
    if (origin !== expected) {
      throw new CsrfError("csrf_failed");
    }
  }
}
