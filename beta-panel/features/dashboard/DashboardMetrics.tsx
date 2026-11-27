import { StatCard } from "@/components/ui/StatCard";
import { formatCount } from "@/lib/format/numbers";
import type { MetricCardDef } from "./types";

type Card = MetricCardDef & { onActivate?: () => void };

type Props = {
  cards: Card[];
  loading: boolean;
  activeKey?: string;
  onSelect?: (key: string) => void;
};

const show = (value: number | null | undefined) => (value === null || value === undefined ? "—" : formatCount(value));

/** Renders a permission-stable metric grid; card identity never depends on response values. */
export function DashboardMetrics({ cards, loading, activeKey, onSelect }: Props) {
  if (!cards.length) return null;
  return (
    <section className="ds-metric-grid ds-metric-grid-4" aria-label="شاخص‌ها" data-testid="dashboard-metrics">
      {cards.map((card) => {
        const filterKey = card.href.startsWith("#dash-") ? card.href.replace("#dash-", "") : card.key;
        const active = activeKey === filterKey || activeKey === card.key;
        return (
          <StatCard
            key={card.testId}
            icon={card.icon}
            label={card.label}
            value={show(card.value)}
            hint={card.hint}
            loading={loading}
            testId={card.testId}
            href={card.onActivate || onSelect ? undefined : card.href.startsWith("#") ? undefined : card.href}
            accent={card.accent}
            active={active}
            onClick={
              card.onActivate
                ? card.onActivate
                : onSelect && card.href.startsWith("#dash-")
                  ? () => onSelect(filterKey)
                  : undefined
            }
          />
        );
      })}
    </section>
  );
}
