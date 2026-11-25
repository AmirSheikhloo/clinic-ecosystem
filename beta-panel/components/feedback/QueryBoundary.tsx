import type { ReactNode } from "react";
import type { ApiFail } from "@/lib/api";
import { Alert } from "./Alert";
import { AccessDenied } from "./AccessDenied";

type Props = {
  loading: boolean;
  error: ApiFail | null;
  children: ReactNode;
  deniedWhat?: string;
  onRetry?: () => void;
};

/** Consistent loading / denied / error presentation for server-backed regions. */
export function QueryBoundary({ loading, error, children, deniedWhat, onRetry }: Props) {
  if (loading) {
    return (
      <p className="text-[var(--ds-text-muted)]" role="status" data-testid="loading">
        در حال بارگذاری…
      </p>
    );
  }
  if (error?.status === 403) return <AccessDenied what={deniedWhat} />;
  if (error) {
    return (
      <div className="space-y-2" data-testid="query-error">
        <Alert>{error.message}</Alert>
        {onRetry ? (
          <button type="button" className="ds-btn ds-btn-ghost text-sm" onClick={onRetry}>
            تلاش دوباره
          </button>
        ) : null}
      </div>
    );
  }
  return <>{children}</>;
}
