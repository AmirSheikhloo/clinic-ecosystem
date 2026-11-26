/**
 * Read cookies from the incoming Request Cookie header.
 * Prefer this over next/headers cookies() for CSRF double-submit checks so the
 * values match what the browser actually sent on the request.
 */

export type CookieReader = {
  get: (name: string) => { value: string } | undefined;
};

export function cookiesFromRequest(request: Request): CookieReader {
  const map = new Map<string, string>();
  const raw = request.headers.get("cookie") || "";
  for (const part of raw.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const name = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    try {
      map.set(name, decodeURIComponent(value));
    } catch {
      map.set(name, value);
    }
  }
  return {
    get(name: string) {
      const value = map.get(name);
      return value !== undefined ? { value } : undefined;
    },
  };
}
