"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { useTheme } from "@/components/feedback/ThemeProvider";
import {
  THEME_LABELS,
  type ThemeId,
} from "@/config/theme";

const NAV = [
  { href: "/dashboard", label: "داشبورد", icon: "◆" },
  { href: "/desk", label: "میز پذیرش", icon: "▣" },
  { href: "/patients", label: "بیماران", icon: "◎" },
  { href: "/appointments", label: "نوبت‌ها", icon: "▤" },
  { href: "/catalog", label: "فهرست خدمات", icon: "▥" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const hideNav = pathname === "/login" || pathname === "/";
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { theme, appearance, setTheme, toggleAppearance } = useTheme();

  async function logout() {
    if (loggingOut) return;
    setLogoutError(null);
    setLoggingOut(true);
    try {
      const response = await apiFetch("/api/auth/logout", {
        method: "POST",
        csrf: true,
      });
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

  if (hideNav) {
    return <div className="min-h-screen">{children}</div>;
  }

  const pageTitle =
    NAV.find((item) => pathname.startsWith(item.href))?.label ?? "پنل کلینیک";

  return (
    <div className="flex min-h-screen">
      <aside
        className={`motion-sidebar sticky top-0 z-[var(--ds-z-sidebar)] flex h-screen flex-col bg-[var(--ds-sidebar)] text-[var(--ds-sidebar-text)] ${
          collapsed ? "w-[4.5rem]" : "w-64"
        }`}
        aria-label="ناوبری اصلی"
      >
        <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3 py-4">
          {!collapsed && (
            <Link href="/dashboard" className="text-base font-bold tracking-tight">
              کلینیک اکوسیستم
            </Link>
          )}
          <button
            type="button"
            className="rounded-md px-2 py-1 text-sm hover:bg-white/10"
            aria-expanded={!collapsed}
            aria-label={collapsed ? "گسترش نوار کناری" : "جمع‌کردن نوار کناری"}
            onClick={() => setCollapsed((value) => !value)}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-2 text-sm">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 rounded-md px-3 py-2 transition-colors duration-[var(--ds-motion-micro)] ${
                  active
                    ? "bg-white/18 font-medium"
                    : "text-[var(--ds-sidebar-muted)] hover:bg-white/10 hover:text-[var(--ds-sidebar-text)]"
                }`}
                title={item.label}
              >
                <span aria-hidden>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        {!collapsed && (
          <div className="space-y-2 border-t border-white/10 p-3 text-xs">
            <label className="block space-y-1">
              <span className="text-[var(--ds-sidebar-muted)]">پالت رنگی</span>
              <select
                className="w-full rounded-md border border-white/20 bg-transparent px-2 py-1.5"
                value={theme}
                onChange={(e) => setTheme(e.target.value as ThemeId)}
                aria-label="انتخاب تم"
              >
                {(Object.keys(THEME_LABELS) as ThemeId[]).map((id) => (
                  <option key={id} value={id} className="text-black">
                    {THEME_LABELS[id]}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="w-full rounded-md border border-white/20 px-2 py-1.5 hover:bg-white/10"
              onClick={toggleAppearance}
            >
              {appearance === "light" ? "حالت تیره" : "حالت روشن"}
            </button>
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-[var(--ds-z-header)] border-b border-[var(--ds-border)] bg-[var(--ds-surface)]/80 backdrop-blur-md">
          <div className="flex items-center justify-between gap-4 px-4 py-3">
            <div>
              <h1 className="text-lg font-bold text-[var(--ds-primary-strong)]">{pageTitle}</h1>
              <p className="text-xs text-[var(--ds-text-muted)]">محیط توسعه — داده مصنوعی</p>
            </div>
            <div className="flex items-center gap-3">
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
        <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</div>
      </div>
    </div>
  );
}
