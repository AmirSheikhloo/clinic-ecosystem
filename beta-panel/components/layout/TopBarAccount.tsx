"use client";

import { useSession } from "@/components/session/SessionProvider";
import { Skeleton } from "@/components/ui/Skeleton";
import { Icon } from "@/components/ui/Icon";
import { NotificationBell } from "./NotificationBell";

const ROLE_FA: Record<string, string> = {
  CLINIC_OWNER: "مالک کلینیک",
  CLINIC_MANAGER: "مدیر",
  DEPUTY_ADMIN: "مدیر داخلی",
  RECEPTIONIST: "منشی",
};

/**
 * Account strip: silhouette at logical start (visual right in RTL) + Persian name + job title.
 * Never falls back to email as the ordinary second line.
 */
export function TopBarAccount() {
  const { me, status } = useSession();
  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || "کاربر" : "";
  const roleCode = me?.governance_roles?.[0];
  const secondLine =
    (me?.job_title && me.job_title.trim()) ||
    (roleCode ? ROLE_FA[roleCode] || null : null) ||
    "کاربر مجاز";

  return (
    <div className="ds-topbar-account" data-testid="topbar-account">
      <NotificationBell />
      <div className="ds-topbar-user" data-testid={displayName ? "current-user" : undefined} title={undefined}>
        {status === "loading" ? (
          <>
            <Skeleton className="h-8 w-8 flex-none !rounded-full" />
            <span className="flex min-w-0 flex-1 flex-col items-end justify-center gap-1">
              <Skeleton className="h-3.5 w-[5.5rem]" />
              <Skeleton className="h-2.5 w-[3.5rem]" />
            </span>
          </>
        ) : (
          <>
            <span className="ds-avatar" aria-hidden="true" title="نمایه کاربر">
              <Icon name="user" />
            </span>
            <span className="min-w-0 flex-1 truncate text-end">
              <span className="block truncate text-sm font-medium leading-tight">{displayName}</span>
              <span className="block truncate text-[11px] leading-tight text-[var(--ds-text-muted)]" data-testid="account-job-title">
                {secondLine}
              </span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
