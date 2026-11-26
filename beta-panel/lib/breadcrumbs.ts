import { NAV_ITEMS } from "./permissions";

export type Crumb = { label: string; href?: string };

const EXTRA: Record<string, string> = {
  "/catalog/manage": "مدیریت",
};

/** Contextual trail derived from the path; the last crumb is the current page. */
export function breadcrumbsFor(pathname: string): Crumb[] {
  const root = NAV_ITEMS.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`)).sort(
    (a, b) => b.href.length - a.href.length,
  )[0];
  if (!root) return [{ label: "پنل کلینیک" }];
  const trail: Crumb[] = [];
  if (pathname === root.href) return [{ label: root.label }];
  trail.push({ label: root.label, href: root.href });
  if (EXTRA[pathname]) trail.push({ label: EXTRA[pathname] });
  else if (root.href === "/patients") trail.push({ label: "پروندهٔ بیمار" });
  else trail.push({ label: "جزئیات" });
  return trail;
}
