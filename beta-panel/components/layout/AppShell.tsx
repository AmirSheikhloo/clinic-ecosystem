"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { SessionProvider, useSession } from "@/components/session/SessionProvider";
import { activeNav, NAV_ITEMS, visibleNav } from "@/lib/permissions";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

function ShellFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { permissions, status } = useSession();
  const [collapsed, setCollapsed] = useState(false);
  const items = status === "ready" ? visibleNav(permissions) : NAV_ITEMS.filter((i) => i.anyOf.length === 0);
  const pageTitle = activeNav(pathname)?.label ?? "پنل کلینیک";

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar
        items={items}
        pathname={pathname}
        collapsed={collapsed}
        onToggle={() => setCollapsed((value) => !value)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={pageTitle} />
        <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</div>
      </div>
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
