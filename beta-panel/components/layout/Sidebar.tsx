"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import type { NavItem } from "@/lib/permissions";
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
        <div className="ds-sidebar-foot">
          {collapsed ? <Icon name="info" size="sm" /> : <span>نسخهٔ توسعه — فقط داده مصنوعی</span>}
        </div>
      </div>
    </aside>
  );
}
