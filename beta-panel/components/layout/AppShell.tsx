"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { usePreferences } from "@/components/feedback/ThemeProvider";
import { SessionProvider, useSession } from "@/components/session/SessionProvider";
import { NAV_ITEMS, visibleNav } from "@/lib/permissions";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

function ShellFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { permissions, status } = useSession();
  const { preferences, setPreference } = usePreferences();
  const [navOpen, setNavOpen] = useState(false);
  const collapsed = preferences.sidebar === "collapsed";
  const ready = status === "ready";
  const items = ready ? visibleNav(permissions) : NAV_ITEMS.filter((item) => item.anyOf.length === 0);

  return (
    <div className="ds-shell">
      <Sidebar
        items={items}
        pathname={pathname}
        collapsed={collapsed}
        pending={status === "loading"}
        onToggle={() => setPreference("sidebar", collapsed ? "expanded" : "collapsed")}
      />
      <div className="ds-main">
        <TopBar pathname={pathname} onOpenNav={() => setNavOpen(true)} />
        <div className="ds-page" data-testid="page-frame">
          {children}
        </div>
      </div>
      <MobileNav open={navOpen} onClose={() => setNavOpen(false)} items={items} pathname={pathname} pending={status === "loading"} />
    </div>
  );
}

/** Persistent authenticated shell: mounted once by the (app) route-group layout. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ShellFrame>{children}</ShellFrame>
    </SessionProvider>
  );
}
