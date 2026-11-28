import type { ReactNode } from "react";
import Link from "next/link";
import { Icon } from "./Icon";
import type { IconName } from "./icon-paths";
import { Skeleton } from "./Skeleton";

type Accent = "today" | "upcoming" | "needs" | "cancelled" | "online" | "blue" | "purple" | "amber" | "rose" | "green";

type Props = {
  label: string;
  value: string;
  hint?: string;
  testId?: string;
  icon?: IconName;
  href?: string;
  footer?: ReactNode;
  loading?: boolean;
  accent?: Accent;
  active?: boolean;
  interactive?: boolean;
  badge?: number;
  onClick?: () => void;
};

export function StatCard({
  label,
  value,
  hint,
  testId,
  icon,
  href,
  footer,
  loading = false,
  accent,
  active = false,
  interactive = true,
  badge,
  onClick,
}: Props) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-medium opacity-90">{label}</p>
        <span className="relative flex-none">
          {icon ? (
            <span className="ds-avatar !h-9 !w-9 !rounded-[var(--ds-radius-md)]" data-metric-icon="">
              <Icon name={icon} size="sm" />
            </span>
          ) : null}
          {badge && badge > 0 ? (
            <span className="ds-metric-badge" aria-label={`${badge} نیازمند بررسی`} data-testid={`${testId}-badge`}>
              {badge > 99 ? "99+" : badge}
            </span>
          ) : null}
        </span>
      </div>
      <div className="mt-2 h-9">
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <p className="text-3xl font-bold leading-9 tabular-nums" data-testid={testId}>
            {value}
          </p>
        )}
      </div>
      {hint ? <p className="mt-1 text-xs opacity-80">{hint}</p> : null}
      {footer}
    </>
  );
  const cls = [
    "ds-card ds-metric-card block p-4 transition-[box-shadow,transform] duration-[var(--ds-motion-dropdown)]",
    accent ? `ds-metric-card-${accent}` : "",
    active ? "is-active-metric" : "",
    interactive ? "is-interactive" : "is-static",
  ]
    .filter(Boolean)
    .join(" ");

  if (interactive && onClick) {
    return (
      <button
        type="button"
        className={`${cls} w-full text-start`}
        aria-busy={loading || undefined}
        aria-pressed={active}
        onClick={onClick}
        data-interactive="true"
      >
        {body}
      </button>
    );
  }
  if (interactive && href) {
    return (
      <Link href={href} className={cls} aria-busy={loading || undefined} data-interactive="true">
        {body}
      </Link>
    );
  }
  return (
    <div className={cls} aria-busy={loading || undefined} data-interactive="false" data-testid={testId ? `${testId}-card` : undefined}>
      {body}
    </div>
  );
}
