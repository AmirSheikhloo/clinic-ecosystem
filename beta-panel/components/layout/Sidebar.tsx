"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useToast } from "@/components/feedback/Toast";
import { Icon } from "@/components/ui/Icon";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import type { NavItem } from "@/lib/permissions";
import { clearQueryCache } from "@/lib/query-cache";
import { NavList } from "./NavList";

type Props = {
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
  pending?: boolean;
  onToggle: () => void;
};

export function SidebarBrand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link href="/dashboard" className="ds-brand" aria-label="کلینیک اکوسیستم" title={collapsed ? "کلینیک اکوسیستم" : undefined}>
      <span className="ds-brand-mark">
        <Icon name="stethoscope" />
      </span>
      <span className="ds-brand-text truncate">کلینیک اکوسیستم</span>
    </Link>
  );
}

export function Sidebar({ items, pathname, collapsed, pending = false, onToggle }: Props) {
  const router = useRouter();
  const toast = useToast();
  const [loggingOut, setLoggingOut] = useState(false);

  async function logout() {
    if (loggingOut) return;
    const dirty = typeof window !== "undefined" && window.sessionStorage.getItem("clinic.draft.dirty") === "1";
    if (dirty && !window.confirm("پیش‌نویس ذخیره‌نشده دارید. خروج باعث از دست رفتن آن می‌شود. ادامه می‌دهید؟")) {
      return;
    }
    setLoggingOut(true);
    try {
      const response = await apiFetch("/api/auth/logout", { method: "POST", csrf: true });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
        toast.failure(formatApiError(data, "خروج ناموفق بود — نشست هنوز فعال است"));
        return;
      }
      clearQueryCache();
      window.sessionStorage.removeItem("clinic.draft.dirty");
      router.replace("/login");
    } catch {
      toast.failure("ارتباط برای خروج برقرار نشد — نشست هنوز فعال است");
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <aside className="ds-sidebar" data-collapsed={collapsed} data-testid="app-sidebar">
      <div className="ds-sidebar-inner">
        <div className="ds-sidebar-head">
          <SidebarBrand collapsed={collapsed} />
          <button
            type="button"
            className="ds-sidebar-toggle"
            aria-expanded={!collapsed}
            aria-label={collapsed ? "گسترش نوار کناری" : "جمع‌کردن نوار کناری"}
            data-testid="sidebar-toggle"
            onClick={onToggle}
          >
            <Icon name={collapsed ? "sidebarExpand" : "sidebarCollapse"} />
          </button>
        </div>
        <NavList items={items} pathname={pathname} collapsed={collapsed} pending={pending} />
        <div className="ds-sidebar-foot space-y-2">
          {collapsed ? (
            <Icon name="info" size="sm" />
          ) : (
            <span className="block text-[11px] text-[var(--ds-text-muted)]" data-testid="synthetic-env-marker">
              محیط مصنوعی — داده آزمایشی
            </span>
          )}
          <button
            type="button"
            className="ds-logout-sidebar"
            data-testid="logout-button"
            aria-label="خروج از حساب"
            disabled={loggingOut}
            onClick={() => void logout()}
          >
            <Icon name="logout" size="sm" />
            {collapsed ? null : <span>{loggingOut ? "خروج…" : "خروج"}</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
