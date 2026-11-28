type Props = {
  total: number;
  pageSize: number;
  offset: number;
  pageSizes: readonly number[];
  onPageSizeChange: (size: number) => void;
  onOffsetChange: (offset: number) => void;
};

/** IBM Carbon / Fluent-style numbered pagination with bounded window + ellipsis. */
export function PaginationFooter({
  total,
  pageSize,
  offset,
  pageSizes,
  onPageSizeChange,
  onOffsetChange,
}: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const page = Math.min(pages, Math.floor(offset / pageSize) + 1);
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = total === 0 ? 0 : Math.min(total, page * pageSize);
  const windowPages = visiblePages(page, pages);

  return (
    <div className="ds-pagination-footer" data-testid="pagination-footer">
      <p className="ds-pagination-range tabular-nums" data-testid="pagination-range">
        {total === 0 ? "۰ نتیجه" : `${from}–${to} از ${total}`}
      </p>
      <nav className="ds-pagination-pages" aria-label="صفحه‌بندی">
        <button
          type="button"
          className="ds-btn ds-btn-ghost ds-btn-sm"
          disabled={page <= 1}
          aria-label="صفحه اول"
          onClick={() => onOffsetChange(0)}
        >
          «
        </button>
        <button
          type="button"
          className="ds-btn ds-btn-ghost ds-btn-sm"
          disabled={page <= 1}
          aria-label="صفحه قبل"
          onClick={() => onOffsetChange(Math.max(0, (page - 2) * pageSize))}
        >
          ‹
        </button>
        {windowPages.map((item, idx) =>
          item === "…" ? (
            <span key={`e-${idx}`} className="ds-pagination-ellipsis" aria-hidden="true">
              …
            </span>
          ) : (
            <button
              key={item}
              type="button"
              className={`ds-btn ds-btn-sm ${item === page ? "ds-btn-primary" : "ds-btn-ghost"}`}
              aria-current={item === page ? "page" : undefined}
              onClick={() => onOffsetChange((item - 1) * pageSize)}
            >
              {item}
            </button>
          ),
        )}
        <button
          type="button"
          className="ds-btn ds-btn-ghost ds-btn-sm"
          disabled={page >= pages}
          aria-label="صفحه بعد"
          onClick={() => onOffsetChange(page * pageSize)}
        >
          ›
        </button>
        <button
          type="button"
          className="ds-btn ds-btn-ghost ds-btn-sm"
          disabled={page >= pages}
          aria-label="صفحه آخر"
          onClick={() => onOffsetChange((pages - 1) * pageSize)}
        >
          »
        </button>
      </nav>
      <label className="ds-pagination-size text-sm">
        در صفحه
        <select
          className="ds-input ds-pagination-size-select"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          data-testid="dashboard-day-page-size"
        >
          {pageSizes.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function visiblePages(current: number, total: number): Array<number | "…"> {
  if (total <= 9) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set<number>([1, total, current]);
  for (let d = 1; d <= 2; d += 1) {
    if (current - d > 1) set.add(current - d);
    if (current + d < total) set.add(current + d);
  }
  const sorted = [...set].sort((a, b) => a - b);
  const out: Array<number | "…"> = [];
  for (let i = 0; i < sorted.length; i += 1) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) out.push("…");
    out.push(sorted[i]);
  }
  return out;
}
