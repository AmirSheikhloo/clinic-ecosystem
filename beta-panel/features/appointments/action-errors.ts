import type { ApiFail } from "../../lib/api";

/** User-facing message for lifecycle failures, including precondition and retry cases. */
export function failureMessage(failure: Pick<ApiFail, "status" | "error" | "message">): string {
  if (failure.status === 412) return "این نوبت در این فاصله تغییر کرده است؛ جزئیات را دوباره بارگذاری کنید.";
  if (failure.status === 428) return "نسخهٔ نوبت مشخص نیست؛ جزئیات را دوباره بارگذاری کنید.";
  if (failure.status === 425) return "درخواست قبلی هنوز در حال پردازش است؛ چند لحظه بعد دوباره تلاش کنید.";
  if (failure.status === 0) return "ارتباط قطع شد؛ دوباره تلاش کنید — درخواست تکراری دوبار اعمال نمی‌شود.";
  if (failure.status === 403) return "برای این عملیات مجوز لازم را ندارید.";
  return failure.message;
}
