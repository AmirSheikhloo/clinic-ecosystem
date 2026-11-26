"use client";

import { Dialog } from "@/components/ui/Dialog";
import type { NavItem } from "@/lib/permissions";
import { NavList } from "./NavList";

type Props = { open: boolean; onClose: () => void; items: NavItem[]; pathname: string; pending?: boolean };

/** Off-canvas navigation for widths below the desktop sidebar breakpoint. */
export function MobileNav({ open, onClose, items, pathname, pending = false }: Props) {
  return (
    <Dialog open={open} onClose={onClose} title="منوی اصلی" placement="drawer-start" testId="mobile-nav" description="نسخهٔ توسعه — فقط داده مصنوعی">
      <div className="-m-5 bg-[var(--ds-sidebar)] text-[var(--ds-sidebar-text)]">
        <NavList items={items} pathname={pathname} pending={pending} onNavigate={onClose} />
      </div>
    </Dialog>
  );
}
