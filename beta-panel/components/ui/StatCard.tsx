import type { ReactNode } from "react";
import Link from "next/link";
import { Icon } from "./Icon";
import type { IconName } from "./icon-paths";

type Props = {
  label: string;
  value: string;
  hint?: string;
  testId?: string;
  icon?: IconName;
  href?: string;
  footer?: ReactNode;
};

export function StatCard({ label, value, hint, testId, icon, href, footer }: Props) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-[var(--ds-text-muted)]">{label}</p>
        {icon ? (
          <span className="ds-avatar !h-9 !w-9 !rounded-[var(--ds-radius-md)]">
            <Icon name={icon} size="sm" />
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-3xl font-bold tabular-nums text-[var(--ds-text)]" data-testid={testId}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--ds-text-muted)]">{hint}</p> : null}
      {footer}
    </>
  );
  const cls = "ds-card block p-4 transition-shadow duration-[var(--ds-motion-dropdown)]";
  return href ? (
    <Link href={href} className={`${cls} hover:border-[var(--ds-primary)]`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}
