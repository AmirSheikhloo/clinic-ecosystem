"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { clearQueryCache } from "@/lib/query-cache";
import { ThemeMenu } from "./ThemeMenu";

function initials(first: string, last: string, fallback: string): string {
  const letters = `${first.trim().charAt(0)}${last.trim().charAt(0)}`.trim();
  return letters || fallback.charAt(0).toUpperCase();
}

/**
 * Account controls with a fixed footprint: the name box has a set width and truncates,
 * and a same-sized placeholder holds its place until the session is known.
 */
export function TopBarAccount() {
  const router = useRouter();
  const toast = useToast();
  const { me, status } = useSession();
  const [loggingOut, setLoggingOut] = useState(false);
  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.login_identifier : "";

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      const response = await apiFetch("/api/auth/logout", { method: "POST", csrf: true });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
        toast.failure(formatApiError(data, "خروج ناموفق بود — نشست هنوز فعال است"));
        return;
      }
      clearQueryCache();
      router.replace("/login");
    } catch {
      toast.failure("ارتباط برای خروج برقرار نشد — نشست هنوز فعال است");
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="ds-topbar-account" data-testid="topbar-account">
      <ThemeMenu />
      <div className="ds-topbar-user" data-testid={displayName ? "current-user" : undefined} title={me?.login_identifier}>
        {status === "loading" ? (
          <>
            <Skeleton className="h-8 w-8 flex-none !rounded-full" />
            <Skeleton className="h-4 min-w-0 flex-1" />
          </>
        ) : (
          <>
            <span className="ds-avatar" aria-hidden="true">
              {displayName ? initials(me?.first_name ?? "", me?.last_name ?? "", displayName) : "؟"}
            </span>
            <span className="min-w-0 flex-1 truncate text-sm">{displayName}</span>
          </>
        )}
      </div>
      <Button
        variant="ghost"
        icon="logout"
        onClick={logout}
        loading={loggingOut}
        className="ds-topbar-logout"
        data-testid="logout-button"
        aria-label="خروج از حساب"
      >
        <span className="ds-topbar-logout-text">خروج</span>
      </Button>
    </div>
  );
}
