"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { useSession } from "@/components/session/SessionProvider";
import { GlobalSearch } from "./GlobalSearch";

export function TopBar({ title }: { title: string }) {
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
    <header className="sticky top-0 z-[var(--ds-z-header)] border-b border-[var(--ds-border)] bg-[var(--ds-surface)]/80 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <h1 className="text-lg font-bold text-[var(--ds-primary-strong)]">{title}</h1>
          <p className="text-xs text-[var(--ds-text-muted)]">محیط توسعه — داده مصنوعی</p>
        </div>
        <div className="order-3 w-full sm:order-none sm:w-auto sm:flex-1 sm:px-4 sm:flex sm:justify-center">
          <GlobalSearch />
        </div>
        <div className="flex items-center gap-3">
          {displayName && (
            <span className="hidden text-sm text-[var(--ds-text-muted)] md:inline" data-testid="current-user">
              {displayName}
            </span>
          )}
          {logoutError && (
            <span className="max-w-xs text-xs text-[var(--ds-danger)]" role="alert">
              {logoutError}
            </span>
          )}
          <button
            type="button"
            data-testid="logout-button"
            onClick={logout}
            disabled={loggingOut}
            className="ds-btn ds-btn-ghost text-sm"
          >
            {loggingOut ? "خروج…" : "خروج"}
          </button>
        </div>
      </div>
    </header>
  );
}
