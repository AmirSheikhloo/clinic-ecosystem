import type { ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import type { IconName } from "@/components/ui/icon-paths";

type Tone = "danger" | "ok" | "warn" | "info";

type Props = {
  tone?: Tone;
  children: ReactNode;
  role?: "alert" | "status";
  testId?: string;
  action?: ReactNode;
};

const CLASS: Record<Tone, string> = {
  danger: "ds-alert ds-alert-danger",
  ok: "ds-alert ds-alert-ok",
  warn: "ds-alert ds-alert-warn",
  info: "ds-alert ds-alert-info",
};

const ICON: Record<Tone, IconName> = { danger: "alert", ok: "success", warn: "alert", info: "info" };

export function Alert({ tone = "danger", children, role, testId, action }: Props) {
  return (
    <div className={CLASS[tone]} role={role ?? (tone === "danger" ? "alert" : "status")} data-testid={testId}>
      <Icon name={ICON[tone]} size="sm" className="mt-1" />
      <div className="min-w-0 flex-1">{children}</div>
      {action}
    </div>
  );
}
