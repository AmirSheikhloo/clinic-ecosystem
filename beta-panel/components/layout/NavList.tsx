import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Tooltip } from "@/components/ui/Tooltip";
import { NAV_GROUPS, activeNav, type NavItem } from "@/lib/permissions";

type Props = {
  items: NavItem[];
  pathname: string;
  collapsed?: boolean;
  onNavigate?: () => void;
};

/** Grouped navigation shared by the desktop sidebar and the mobile drawer. */
export function NavList({ items, pathname, collapsed = false, onNavigate }: Props) {
  const current = activeNav(pathname, items);
  return (
    <nav className="ds-nav" aria-label="ناوبری اصلی">
      {NAV_GROUPS.map((group) => {
        const groupItems = items.filter((item) => item.group === group.id);
        if (!groupItems.length) return null;
        return (
          <div key={group.id} className="flex flex-col gap-0.5" role="group" aria-label={group.label}>
            <p className="ds-nav-group-label" aria-hidden="true">
              {group.label}
            </p>
            {groupItems.map((item) => (
              <Tooltip key={item.href} label={item.label} disabled={!collapsed}>
                <Link
                  href={item.href}
                  aria-label={item.label}
                  aria-current={current?.href === item.href ? "page" : undefined}
                  className="ds-nav-link w-full"
                  onClick={onNavigate}
                >
                  <Icon name={item.icon} />
                  <span className="ds-nav-label">{item.label}</span>
                </Link>
              </Tooltip>
            ))}
          </div>
        );
      })}
    </nav>
  );
}
