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

function truthy(raw: string | undefined): boolean {
  return (raw || "").trim().toLowerCase() === "1"
    || (raw || "").trim().toLowerCase() === "true"
    || (raw || "").trim().toLowerCase() === "yes"
    || (raw || "").trim().toLowerCase() === "on";
}

export function requireBetaPanelEnabled(): void {
  const clinicEnv = (process.env.CLINIC_ENV || "production").trim().toLowerCase();
  if (!ALLOWED_ENVS.has(clinicEnv)) {
    throw new BetaPanelConfigError(
      "Beta panel is disabled outside development/test environments",
    );
  }
  if (!truthy(process.env.CLINIC_BETA_PANEL_ENABLED)) {
    throw new BetaPanelConfigError("CLINIC_BETA_PANEL_ENABLED is not enabled");
  }
}

export function backendBaseUrl(): string {
  requireBetaPanelEnabled();
  const base = (process.env.CLINIC_API_BASE_URL || "").trim().replace(/\/$/, "");
  if (!base) {
    throw new BetaPanelConfigError("CLINIC_API_BASE_URL is required");
  }
  return base;
}

export { SESSION_COOKIE, CSRF_COOKIE } from "./constants";
