import { financialStatusFa } from "@/lib/format/operational-status";

type Props = {
  code?: string | null;
  label?: string | null;
  outstandingIrr?: number | null;
  paymentMethodLabel?: string | null;
  financeReviewRequired?: boolean;
  onOpen?: () => void;
  canOpen?: boolean;
};

/** Meaningful localized financial status — never raw UNPAID / «مشاهده مالی» as the state. */
export function FinancialStatusCell({
  code,
  label,
  outstandingIrr,
  paymentMethodLabel,
  financeReviewRequired,
  onOpen,
  canOpen,
}: Props) {
  const text = label && !/^[A-Z_]+$/.test(label) ? label : financialStatusFa(code ?? label);
  const body = (
    <span className="ds-finance-cell" data-testid="finance-status-cell">
      <span className="ds-finance-status-label">{text}</span>
      {paymentMethodLabel ? <span className="ds-finance-method">{paymentMethodLabel}</span> : null}
      {typeof outstandingIrr === "number" && outstandingIrr > 0 ? (
        <span className="ltr-isolate ds-finance-outstanding" dir="ltr" data-testid="dashboard-outstanding">
          مانده {outstandingIrr.toLocaleString("en-US")} ریال
        </span>
      ) : null}
      {financeReviewRequired ? (
        <span className="ds-finance-review-warn" data-testid="finance-review-warn">
          نیازمند بررسی مالی
        </span>
      ) : null}
    </span>
  );
  if (canOpen && onOpen) {
    return (
      <button type="button" className="ds-finance-cell-btn" data-testid="dashboard-open-finance" onClick={onOpen}>
        {body}
      </button>
    );
  }
  return body;
}
