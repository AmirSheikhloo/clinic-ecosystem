/**
 * Durable per-checkout-intent idempotency keys.
 * Same intent fingerprint → same UUID; payload change → new UUID; no truncation.
 */

export type CheckoutIntentFingerprint = {
  patientId: string;
  lineServiceIds: string[];
  lineAppointmentIds: Array<string | null>;
  discountFixed: number;
  discountBps: number;
  payMethod: string;
  paymentAmountIrr: number | null;
  acceptCredit: boolean;
  post: boolean;
};

export class CheckoutIntentStore {
  private readonly byFingerprint = new Map<string, string>();
  private activeKey: string | null = null;
  private activeFingerprint: string | null = null;

  fingerprint(intent: CheckoutIntentFingerprint): string {
    return [
      intent.patientId,
      intent.lineServiceIds.join(","),
      intent.lineAppointmentIds.map((id) => id ?? "-").join(","),
      String(intent.discountFixed),
      String(intent.discountBps),
      intent.payMethod,
      String(intent.paymentAmountIrr ?? "none"),
      intent.acceptCredit ? "1" : "0",
      intent.post ? "1" : "0",
    ].join("|");
  }

  /** Stable UUID for this intent until payload changes or rotate()/clear(). */
  keyFor(
    intent: CheckoutIntentFingerprint,
    createId: () => string = () => crypto.randomUUID(),
  ): string {
    const fp = this.fingerprint(intent);
    if (this.activeFingerprint === fp && this.activeKey) {
      return this.activeKey;
    }
    const existing = this.byFingerprint.get(fp);
    if (existing) {
      this.activeFingerprint = fp;
      this.activeKey = existing;
      return existing;
    }
    const created = createId();
    this.byFingerprint.set(fp, created);
    this.activeFingerprint = fp;
    this.activeKey = created;
    return created;
  }

  /**
   * After a successful checkout, drop the completed fingerprint so an independent
   * identical purchase later receives a new durable key (retries still reuse until then).
   */
  complete(): void {
    if (this.activeFingerprint) {
      this.byFingerprint.delete(this.activeFingerprint);
    }
    this.activeKey = null;
    this.activeFingerprint = null;
  }

  /** @deprecated prefer complete() after success */
  rotate(): void {
    this.complete();
  }

  clear(): void {
    this.byFingerprint.clear();
    this.activeKey = null;
    this.activeFingerprint = null;
  }
}

/** Integer IRR largest-remainder allocation of a fixed discount across line grosses. */
export function allocateFixedDiscountIrr(
  grosses: number[],
  totalDiscount: number,
): number[] {
  const n = grosses.length;
  if (n === 0 || totalDiscount <= 0) return grosses.map(() => 0);
  const totalGross = grosses.reduce((s, g) => s + g, 0);
  if (totalGross <= 0) return grosses.map(() => 0);
  const capped = Math.min(totalDiscount, totalGross);
  const exact = grosses.map((g) => (capped * g) / totalGross);
  const floors = exact.map((v) => Math.floor(v));
  let rem = capped - floors.reduce((s, v) => s + v, 0);
  const order = exact
    .map((v, i) => ({ i, frac: v - Math.floor(v) }))
    .sort((a, b) => b.frac - a.frac || a.i - b.i);
  const out = [...floors];
  for (const { i } of order) {
    if (rem <= 0) break;
    const room = Math.max(0, grosses[i] - out[i]);
    if (room <= 0) continue;
    out[i] += 1;
    rem -= 1;
  }
  return out;
}
