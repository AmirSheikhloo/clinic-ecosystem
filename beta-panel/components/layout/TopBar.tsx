"use client";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button } from "@/components/ui/Button";
import { breadcrumbsFor } from "@/lib/breadcrumbs";
import { GlobalSearch } from "./GlobalSearch";
import { TopBarAccount } from "./TopBarAccount";

/**
 * Header geometry is a grid with explicit tracks (see layout.css): the lead area takes the
 * remaining space and truncates, the search and account areas never depend on breadcrumb text.
 */
export function TopBar({ pathname, onOpenNav }: { pathname: string; onOpenNav: () => void }) {
  return (
    <header className="ds-topbar" data-testid="app-topbar">
      <Button
        variant="ghost"
        icon="menu"
        className="ds-topbar-menu"
        aria-label="باز کردن منو"
        onClick={onOpenNav}
        data-testid="mobile-nav-open"
      />
      <div className="ds-topbar-lead">
        <span className="ds-dev-notice" data-testid="dev-notice">
          نسخهٔ توسعه — داده مصنوعی
        </span>
        <Breadcrumbs items={breadcrumbsFor(pathname)} />
      </div>
      <div className="ds-topbar-search">
        <GlobalSearch />
      </div>
      <TopBarAccount />
    </header>
  );
}
