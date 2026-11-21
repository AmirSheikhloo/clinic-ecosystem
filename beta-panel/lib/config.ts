/**
 * Server-only Beta panel configuration.
 * Backend credentials and signing secrets must never use NEXT_PUBLIC_*.
 */

const ALLOWED_ENVS = new Set(["development", "test"]);

export class BetaPanelConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BetaPanelConfigError";
  }
}

export function truthy(raw: string | undefined): boolean {
  return (raw || "").trim().toLowerCase() === "1"
    || (raw || "").trim().toLowerCase() === "true"
    || (raw || "").trim().toLowerCase() === "yes"
    || (raw || "").trim().toLowerCase() === "on";
}

/** Pure enablement check against an env map (testable without mutating process.env). */
export function isBetaPanelEnabled(env: Record<string, string | undefined> = process.env): boolean {
  const clinicEnv = (env.CLINIC_ENV || "production").trim().toLowerCase();
  if (!ALLOWED_ENVS.has(clinicEnv)) return false;
  return truthy(env.CLINIC_BETA_PANEL_ENABLED);
}

export function requireBetaPanelEnabled(
  env: Record<string, string | undefined> = process.env,
): void {
  const clinicEnv = (env.CLINIC_ENV || "production").trim().toLowerCase();
  if (!ALLOWED_ENVS.has(clinicEnv)) {
    throw new BetaPanelConfigError(
      "Beta panel is disabled outside development/test environments",
    );
  }
  if (!truthy(env.CLINIC_BETA_PANEL_ENABLED)) {
    throw new BetaPanelConfigError("CLINIC_BETA_PANEL_ENABLED is not enabled");
  }
}

export function backendBaseUrl(
  env: Record<string, string | undefined> = process.env,
): string {
  requireBetaPanelEnabled(env);
  const base = (env.CLINIC_API_BASE_URL || "").trim().replace(/\/$/, "");
  if (!base) {
    throw new BetaPanelConfigError("CLINIC_API_BASE_URL is required");
  }
  return base;
}

export { SESSION_COOKIE, CSRF_COOKIE } from "./constants";
