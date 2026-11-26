import type { ReactNode } from "react";
import type { ApiFail } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { SkeletonRows } from "@/components/ui/Skeleton";
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
    return <SkeletonRows testId="loading" />;
  }
  if (error?.status === 403) return <AccessDenied what={deniedWhat} />;
  if (error) {
    return (
      <div className="space-y-2" data-testid="query-error">
        <Alert
          action={
            onRetry ? (
              <Button variant="ghost" size="sm" icon="refresh" onClick={onRetry}>
                تلاش دوباره
              </Button>
            ) : undefined
          }
        >
          {error.message}
        </Alert>
      </div>
    );
  }
  return <>{children}</>;
}
