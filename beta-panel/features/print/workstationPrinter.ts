/** Per-workstation thermal printer profile — local only, no secrets/PHI. */

import type { ThermalWidth } from "./thermalReceipt";

export type WorkstationPrinterProfile = {
  workstationId: string;
  printerName: string;
  widthMm: ThermalWidth;
  templateId: "thermal_compact_v1";
  autoCutPreferred: boolean;
  autoPrintAfterCommit: boolean;
  copies: number;
  /** Enrollment requires an explicit successful simulated/test print. */
  enrolledAtIso: string | null;
  lastTestPrintAtIso: string | null;
  lastTestPrintJobId: string | null;
  health: "UNKNOWN" | "ENROLLED" | "DEGRADED" | "DISCONNECTED";
  adapter: "simulated" | "browser_fallback" | "qz_pending_approval";
};

const STORAGE_KEY = "clinic.workstation.printer.v1";

export function defaultWorkstationId(): string {
  if (typeof window === "undefined") return "server";
  const existing = window.localStorage.getItem("clinic.workstation.id");
  if (existing) return existing;
  const id = `ws-${crypto.randomUUID?.() ?? String(Date.now())}`;
  window.localStorage.setItem("clinic.workstation.id", id);
  return id;
}

export function blankProfile(workstationId?: string): WorkstationPrinterProfile {
  return {
    workstationId: workstationId ?? defaultWorkstationId(),
    printerName: "",
    widthMm: 80,
    templateId: "thermal_compact_v1",
    autoCutPreferred: true,
    autoPrintAfterCommit: false,
    copies: 1,
    enrolledAtIso: null,
    lastTestPrintAtIso: null,
    lastTestPrintJobId: null,
    health: "UNKNOWN",
    adapter: "simulated",
  };
}

export function loadWorkstationPrinterProfile(): WorkstationPrinterProfile {
  if (typeof window === "undefined") return blankProfile("server");
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return blankProfile();
    const parsed = JSON.parse(raw) as WorkstationPrinterProfile;
    // Never trust persisted secrets/PHI — strip unknown keys by rebuilding.
    return {
      ...blankProfile(parsed.workstationId || defaultWorkstationId()),
      printerName: String(parsed.printerName || "").slice(0, 120),
      widthMm: parsed.widthMm === 58 ? 58 : 80,
      autoCutPreferred: Boolean(parsed.autoCutPreferred),
      autoPrintAfterCommit: Boolean(parsed.autoPrintAfterCommit),
      copies: Math.min(5, Math.max(1, Number(parsed.copies) || 1)),
      enrolledAtIso: parsed.enrolledAtIso ?? null,
      lastTestPrintAtIso: parsed.lastTestPrintAtIso ?? null,
      lastTestPrintJobId: parsed.lastTestPrintJobId ?? null,
      health: parsed.health ?? "UNKNOWN",
      adapter:
        parsed.adapter === "browser_fallback" || parsed.adapter === "qz_pending_approval"
          ? parsed.adapter
          : "simulated",
    };
  } catch {
    return blankProfile();
  }
}

export function saveWorkstationPrinterProfile(profile: WorkstationPrinterProfile): void {
  if (typeof window === "undefined") return;
  const safe: WorkstationPrinterProfile = {
    ...blankProfile(profile.workstationId),
    printerName: profile.printerName.slice(0, 120),
    widthMm: profile.widthMm === 58 ? 58 : 80,
    autoCutPreferred: profile.autoCutPreferred,
    autoPrintAfterCommit: profile.autoPrintAfterCommit,
    copies: Math.min(5, Math.max(1, profile.copies)),
    enrolledAtIso: profile.enrolledAtIso,
    lastTestPrintAtIso: profile.lastTestPrintAtIso,
    lastTestPrintJobId: profile.lastTestPrintJobId,
    health: profile.health,
    adapter: profile.adapter,
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(safe));
}

export function clearWorkstationPrinterProfile(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

/** Auto-print only when enrolled + recent test print + simulated/approved adapter. */
export function canAutoPrint(profile: WorkstationPrinterProfile): boolean {
  return (
    profile.autoPrintAfterCommit &&
    profile.health === "ENROLLED" &&
    Boolean(profile.enrolledAtIso) &&
    Boolean(profile.lastTestPrintJobId) &&
    profile.adapter === "simulated" &&
    Boolean(profile.printerName.trim())
  );
}

export function markEnrolledAfterTestPrint(
  profile: WorkstationPrinterProfile,
  jobId: string,
  nowIso = new Date().toISOString(),
): WorkstationPrinterProfile {
  return {
    ...profile,
    enrolledAtIso: profile.enrolledAtIso ?? nowIso,
    lastTestPrintAtIso: nowIso,
    lastTestPrintJobId: jobId,
    health: "ENROLLED",
  };
}

export function markDisconnected(profile: WorkstationPrinterProfile): WorkstationPrinterProfile {
  return { ...profile, health: "DISCONNECTED" };
}
