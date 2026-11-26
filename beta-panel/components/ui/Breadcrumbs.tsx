import Link from "next/link";
import type { Crumb } from "@/lib/breadcrumbs";
import { Icon } from "./Icon";

/** Contained trail: items never wrap or push neighbours; the current page truncates last. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="مسیر صفحه" className="ds-breadcrumbs" data-testid="breadcrumbs">
      <ol className="ds-breadcrumbs-list">
        <li className="ds-crumb ds-crumb-home">
          <Link href="/dashboard">خانه</Link>
        </li>
        {items.map((crumb, index) => {
          const last = index === items.length - 1;
          return (
            <li key={crumb.label} className={`ds-crumb ${last ? "ds-crumb-current" : ""}`.trim()}>
              <Icon name="chevronLeft" size="sm" className={index === 0 ? "ds-crumb-sep-home" : "ds-crumb-sep"} />
              {crumb.href && !last ? (
                <Link href={crumb.href} title={crumb.label}>
                  {crumb.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} title={crumb.label}>
                  {crumb.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
