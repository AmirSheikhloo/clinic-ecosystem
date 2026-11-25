import { StatCard } from "@/components/ui/StatCard";
import { formatCount } from "@/lib/format/numbers";
import type { MetricCardDef } from "./types";

type Props = { cards: MetricCardDef[]; loading: boolean };

const show = (value: number | null | undefined) => (value === null || value === undefined ? "—" : formatCount(value));

/** Renders a permission-stable metric grid; card identity never depends on response values. */
export function DashboardMetrics({ cards, loading }: Props) {
  if (!cards.length) return null;
  return (
    <section className="ds-metric-grid" aria-label="شاخص‌ها" data-testid="dashboard-metrics">
      {cards.map((card) => (
        <StatCard
          key={card.testId}
          icon={card.icon}
          label={card.label}
          value={show(card.value)}
          hint={card.hint}
          loading={loading}
          testId={card.testId}
          href={card.href}
        />
      ))}
    </section>
  );
}
