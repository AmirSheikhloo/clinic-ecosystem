export function pageInfo(total: number, limit: number, offset: number) {
  const pages = Math.max(1, Math.ceil(total / limit));
  const page = Math.min(pages, Math.floor(offset / limit) + 1);
  return { pages, page, from: total === 0 ? 0 : offset + 1, to: Math.min(total, offset + limit) };
}

/** Offset to land on after a page changes size or the filter shrinks the result set. */
export function clampOffset(total: number, limit: number, offset: number): number {
  if (total <= 0) return 0;
  return Math.min(offset, Math.floor((total - 1) / limit) * limit);
}
