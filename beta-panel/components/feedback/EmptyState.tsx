import type { ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import type { IconName } from "@/components/ui/icon-paths";

type Props = {
  title: string;
  description?: string;
  icon?: IconName;
  action?: ReactNode;
};

export function EmptyState({ title, description, icon = "info", action }: Props) {
  return (
    <div className="ds-empty">
      <span className="ds-empty-icon">
        <Icon name={icon} />
      </span>
      <p className="font-semibold text-[var(--ds-text)]">{title}</p>
      {description && <p className="max-w-md text-sm text-[var(--ds-text-muted)]">{description}</p>}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
