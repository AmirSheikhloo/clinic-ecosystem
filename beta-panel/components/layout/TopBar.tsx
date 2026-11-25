"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button } from "@/components/ui/Button";
import { useSession } from "@/components/session/SessionProvider";
import { breadcrumbsFor } from "@/lib/breadcrumbs";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { GlobalSearch } from "./GlobalSearch";
import { ThemeMenu } from "./ThemeMenu";

function initials(first: string, last: string, fallback: string): string {
  const letters = `${first.trim().charAt(0)}${last.trim().charAt(0)}`.trim();
  return letters || fallback.charAt(0).toUpperCase();
}

export function TopBar({ pathname, onOpenNav }: { pathname: string; onOpenNav: () => void }) {
  const router = useRouter();
  const { me } = useSession();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  async function logout() {
    if (loggingOut) return;
    setLogoutError(null);
    setLoggingOut(true);
    try {
      const response = await apiFetch("/api/auth/logout", { method: "POST", csrf: true });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
        setLogoutError(formatApiError(data, "خروج ناموفق بود — نشست هنوز فعال است"));
        return;
      }
      router.replace("/login");
    } catch {
      setLogoutError("ارتباط برای خروج برقرار نشد — نشست هنوز فعال است");
    } finally {
      setLoggingOut(false);
    }
  }

  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.login_identifier : "";

  return (
    <header className="ds-topbar">
      <Button
        variant="ghost"
        icon="menu"
        className="lg:!hidden"
        aria-label="باز کردن منو"
        onClick={onOpenNav}
        data-testid="mobile-nav-open"
      />
      <Breadcrumbs items={breadcrumbsFor(pathname)} />
      <span className="ds-dev-notice hidden xl:inline" data-testid="dev-notice">
        نسخهٔ توسعه — داده مصنوعی
      </span>
      <div className="order-last w-full sm:order-none sm:mx-auto sm:w-auto sm:flex-1 sm:max-w-md">
        <GlobalSearch />
      </div>
      <div className="ms-auto flex items-center gap-2 sm:ms-0">
        <ThemeMenu />
        {displayName ? (
          <span className="hidden items-center gap-2 md:flex" data-testid="current-user" title={me?.login_identifier}>
            <span className="ds-avatar" aria-hidden="true">
              {initials(me?.first_name ?? "", me?.last_name ?? "", displayName)}
            </span>
            <span className="max-w-40 truncate text-sm">{displayName}</span>
          </span>
        ) : null}
        <Button
          variant="ghost"
          icon="logout"
          onClick={logout}
          loading={loggingOut}
          data-testid="logout-button"
          aria-label="خروج از حساب"
        >
          <span className="hidden sm:inline">خروج</span>
        </Button>
      </div>
      {logoutError ? (
        <p className="w-full text-xs text-[var(--ds-danger)]" role="alert">
          {logoutError}
        </p>
      ) : null}
    </header>
  );
}
