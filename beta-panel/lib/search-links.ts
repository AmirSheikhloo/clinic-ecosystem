export type SearchKind = "patient" | "staff" | "service";

export type SearchHit = { kind: SearchKind; id: string; title: string; subtitle: string | null };

export const SEARCH_KIND_LABEL: Record<SearchKind, string> = {
  patient: "بیمار",
  staff: "کارکنان",
  service: "خدمت",
};

export const SEARCH_MIN_LENGTH = 2;

/** Destination for a global-search hit; ids are server UUIDs, titles are encoded. */
export function searchHitHref(hit: SearchHit): string {
  if (hit.kind === "patient") return `/patients/${encodeURIComponent(hit.id)}`;
  if (hit.kind === "staff") return `/staff?q=${encodeURIComponent(hit.title)}`;
  return `/catalog?q=${encodeURIComponent(hit.title)}`;
}

/** True when a "/" shortcut should be ignored because the user is typing. */
export function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as { tagName?: string; isContentEditable?: boolean } | null;
  if (!el?.tagName) return false;
  const tag = el.tagName.toUpperCase();
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable === true;
}
