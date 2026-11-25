import { Button } from "./Button";
import { formatCount } from "@/lib/format/numbers";
import { pageInfo } from "@/lib/pagination";

type Props = {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
};

export function Pagination({ total, limit, offset, onOffsetChange }: Props) {
  const { pages, page, from, to } = pageInfo(total, limit, offset);
  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3 text-sm"
      aria-label="صفحه‌بندی"
      data-testid="pagination"
    >
      <span className="tabular-nums text-[var(--ds-text-muted)]" data-testid="pagination-summary">
        {formatCount(from)}–{formatCount(to)} از {formatCount(total)}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          disabled={offset <= 0}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
          data-testid="pagination-prev"
        >
          قبلی
        </Button>
        <span className="tabular-nums">
          صفحه {formatCount(page)} از {formatCount(pages)}
        </span>
        <Button
          variant="ghost"
          disabled={offset + limit >= total}
          onClick={() => onOffsetChange(offset + limit)}
          data-testid="pagination-next"
        >
          بعدی
        </Button>
      </div>
    </nav>
  );
}
