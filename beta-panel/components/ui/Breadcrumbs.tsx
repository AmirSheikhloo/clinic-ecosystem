import Link from "next/link";
import type { Crumb } from "@/lib/breadcrumbs";
import { Icon } from "./Icon";

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="مسیر صفحه" className="ds-breadcrumbs" data-testid="breadcrumbs">
      <Link href="/dashboard" className="hidden sm:inline">
        خانه
      </Link>
      {items.map((crumb, index) => {
        const last = index === items.length - 1;
        return (
          <span key={crumb.label} className="flex min-w-0 items-center gap-1.5">
            <Icon name="chevronLeft" size="sm" className={index === 0 ? "hidden sm:block" : ""} />
            {crumb.href && !last ? (
              <Link href={crumb.href}>{crumb.label}</Link>
            ) : (
              <span aria-current={last ? "page" : undefined} className="truncate">
                {crumb.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
