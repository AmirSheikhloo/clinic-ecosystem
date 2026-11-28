"use client";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button } from "@/components/ui/Button";
import { breadcrumbsFor } from "@/lib/breadcrumbs";
import { LiveTehranClock } from "./LiveTehranClock";
import { TopBarAccount } from "./TopBarAccount";

/**
 * Header: breadcrumbs + live Jalali/Tehran clock + account (no global search/theme/logout).
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
        <Breadcrumbs items={breadcrumbsFor(pathname)} />
      </div>
      <div className="ds-topbar-search">
        <LiveTehranClock />
      </div>
      <TopBarAccount />
    </header>
  );
}
