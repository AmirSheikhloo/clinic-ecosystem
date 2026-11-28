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

/** Permission-stable metric grid; Today's card is non-interactive. */
export function DashboardMetrics({ cards, loading, activeKey, onSelect }: Props) {
  if (!cards.length) return null;
  return (
    <section className="ds-metric-grid ds-metric-grid-5" aria-label="شاخص‌ها" data-testid="dashboard-metrics">
      {cards.map((card) => {
        const filterKey = card.href.startsWith("#dash-") ? card.href.replace("#dash-", "") : card.key;
        const interactive = card.interactive !== false && Boolean(card.onActivate || (onSelect && card.href.startsWith("#dash-")));
        const active = interactive && (activeKey === filterKey || activeKey === card.key);
        return (
          <StatCard
            key={card.testId}
            icon={card.icon}
            label={card.label}
            value={show(card.value)}
            hint={card.hint}
            loading={loading}
            testId={card.testId}
            href={!interactive ? undefined : card.onActivate || onSelect ? undefined : card.href.startsWith("#") ? undefined : card.href}
            accent={card.accent}
            active={Boolean(active)}
            interactive={interactive}
            badge={card.badge}
            onClick={
              !interactive
                ? undefined
                : card.onActivate
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
