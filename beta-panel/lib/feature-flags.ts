/**
 * Client-visible feature flags. Shared multi-patient settlement stays OFF until
 * ACR-D0.11 R2 amendment is ratified (MULTI-02). Never weaken one-beneficiary guards.
 */
export const FEATURE_FLAGS = {
  /** Temporary multi-patient cart UI (independent per-patient invoices). */
  multiPatientCart: true,
  /**
   * Shared single-inflow multi-beneficiary settlement — DISABLED.
   * When false, UI must settle each patient as a separate invoice/receipt.
   */
  multiPatientSharedSettlement: false,
} as const;
