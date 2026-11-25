import { Card } from "./Card";

type Props = { label: string; value: string; hint?: string; testId?: string };

export function StatCard({ label, value, hint, testId }: Props) {
  return (
    <Card>
      <p className="text-sm text-[var(--ds-text-muted)]">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums" data-testid={testId}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--ds-text-muted)]">{hint}</p> : null}
    </Card>
  );
}
