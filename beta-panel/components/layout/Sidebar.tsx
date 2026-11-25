"use client";

import Link from "next/link";
import { useTheme } from "@/components/feedback/ThemeProvider";
import { THEME_LABELS, type ThemeId } from "@/config/theme";
import { activeNav, type NavItem } from "@/lib/permissions";

type Props = {
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
  onToggle: () => void;
};

export function Sidebar({ items, pathname, collapsed, onToggle }: Props) {
  const { theme, appearance, setTheme, toggleAppearance } = useTheme();
  const current = activeNav(pathname, items);
  return (
    <aside
      className={`motion-sidebar z-[var(--ds-z-sidebar)] flex w-full flex-col bg-[var(--ds-sidebar)] text-[var(--ds-sidebar-text)] md:sticky md:top-0 md:h-screen ${
        collapsed ? "md:w-[4.5rem]" : "md:w-64"
      }`}
      data-testid="app-sidebar"
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
          data-testid="sidebar-toggle"
          onClick={onToggle}
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>
      <nav className="flex flex-1 flex-row gap-1 overflow-x-auto p-2 text-sm md:flex-col md:overflow-x-visible md:overflow-y-auto" aria-label="ناوبری اصلی">
        {items.map((item) => {
          const active = current?.href === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 transition-colors duration-[var(--ds-motion-micro)] ${
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
        <div className="flex flex-wrap items-end gap-2 border-t border-white/10 p-3 text-xs md:block md:space-y-2">
          <label className="block space-y-1">
            <span className="text-[var(--ds-sidebar-muted)]">پالت رنگی</span>
            <select
              className="rounded-md border border-white/20 bg-transparent px-2 py-1.5 md:w-full"
              value={theme}
              onChange={(e) => setTheme(e.target.value as ThemeId)}
              aria-label="انتخاب تم"
              data-testid="theme-select"
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
            className="rounded-md border border-white/20 px-2 py-1.5 hover:bg-white/10 md:w-full"
            onClick={toggleAppearance}
            data-testid="appearance-toggle"
          >
            {appearance === "light" ? "حالت تیره" : "حالت روشن"}
          </button>
        </div>
      )}
    </aside>
  );
}
