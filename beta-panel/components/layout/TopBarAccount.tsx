"use client";

import { useSession } from "@/components/session/SessionProvider";
import { Skeleton } from "@/components/ui/Skeleton";
import { Icon } from "@/components/ui/Icon";

/**
 * Account strip: Persian name + role, silhouette avatar to the right of the name (RTL).
 * Logout lives in the sidebar footer per Task 34 §6.
 */
export function TopBarAccount() {
  const { me, status } = useSession();
  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.login_identifier : "";
  const roleHint = me?.governance_roles?.[0] ?? me?.login_identifier ?? "";

  return (
    <div className="ds-topbar-account" data-testid="topbar-account">
      <div className="ds-topbar-user" data-testid={displayName ? "current-user" : undefined} title={me?.login_identifier}>
        {status === "loading" ? (
          <>
            <Skeleton className="h-4 min-w-0 flex-1" />
            <Skeleton className="h-8 w-8 flex-none !rounded-full" />
          </>
        ) : (
          <>
            <span className="min-w-0 flex-1 truncate text-end">
              <span className="block truncate text-sm font-medium">{displayName}</span>
              {roleHint ? <span className="block truncate text-[11px] text-[var(--ds-text-muted)]">{roleHint}</span> : null}
            </span>
            <span className="ds-avatar" aria-hidden="true" title="نمایه کاربر">
              <Icon name="user" />
            </span>
          </>
        )}
      </div>
    </div>
  );
}
