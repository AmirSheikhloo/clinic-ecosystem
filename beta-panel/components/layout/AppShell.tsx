"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { SessionProvider, useSession } from "@/components/session/SessionProvider";
import { NAV_ITEMS, visibleNav } from "@/lib/permissions";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

function ShellFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { permissions, status } = useSession();
  const [collapsed, setCollapsed] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const items = status === "ready" ? visibleNav(permissions) : NAV_ITEMS.filter((i) => i.anyOf.length === 0);

  return (
    <div className="ds-shell">
      <Sidebar items={items} pathname={pathname} collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <div className="ds-main">
        <TopBar pathname={pathname} onOpenNav={() => setNavOpen(true)} />
        <div className="ds-page">{children}</div>
      </div>
      <MobileNav open={navOpen} onClose={() => setNavOpen(false)} items={items} pathname={pathname} />
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const hideNav = pathname === "/login" || pathname === "/";
  if (hideNav) return <div className="min-h-screen">{children}</div>;
  return (
    <SessionProvider>
      <ShellFrame>{children}</ShellFrame>
    </SessionProvider>
  );
}
