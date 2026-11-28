/**
 * Pay-per-session workflow stubs — finance stays on ordinary invoice/receipt
 * per visit. Course rows never mint prepaid entitlements.
 */

export type PayPerSessionCheckoutStub = {
  courseId: string;
  sessionNo: number;
  appointmentId?: string;
  /** Always false until owner ratification. */
  prepaidEntitlementEnabled: false;
  /** Always false until MULTI-02 ratification. */
  sharedSettlementEnabled: false;
  hintFa: string;
};

export function buildPayPerSessionCheckoutStub(input: {
  courseId: string;
  sessionNo: number;
  appointmentId?: string;
}): PayPerSessionCheckoutStub {
  return {
    courseId: input.courseId,
    sessionNo: input.sessionNo,
    appointmentId: input.appointmentId,
    prepaidEntitlementEnabled: false,
    sharedSettlementEnabled: false,
    hintFa: "هزینه این جلسه به‌صورت جداگانه در صورتحساب ثبت می‌شود؛ بسته پیش‌پرداخت فعال نیست.",
  };
}
