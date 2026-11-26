import type { ReactNode } from "react";
import Link from "next/link";
import { Icon } from "./Icon";
import type { IconName } from "./icon-paths";
import { Skeleton } from "./Skeleton";

type Props = {
  label: string;
  value: string;
  hint?: string;
  testId?: string;
  icon?: IconName;
  href?: string;
  footer?: ReactNode;
  /** Shows a value-sized placeholder instead of the number, keeping the card height fixed. */
  loading?: boolean;
};

export function StatCard({ label, value, hint, testId, icon, href, footer, loading = false }: Props) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm text-[var(--ds-text-muted)]">{label}</p>
        {icon ? (
          <span className="ds-avatar !h-9 !w-9 flex-none !rounded-[var(--ds-radius-md)]">
            <Icon name={icon} size="sm" />
          </span>
        ) : null}
      </div>
      <div className="mt-2 h-9">
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <p className="text-3xl font-bold leading-9 tabular-nums text-[var(--ds-text)]" data-testid={testId}>
            {value}
          </p>
        )}
      </div>
      {hint ? <p className="mt-1 text-xs text-[var(--ds-text-muted)]">{hint}</p> : null}
      {footer}
    </>
  );
  const cls = "ds-card block p-4 transition-shadow duration-[var(--ds-motion-dropdown)]";
  return href ? (
    <Link href={href} className={`${cls} hover:border-[var(--ds-primary)]`} aria-busy={loading || undefined}>
      {body}
    </Link>
  ) : (
    <div className={cls} aria-busy={loading || undefined}>
      {body}
    </div>
  );
}
