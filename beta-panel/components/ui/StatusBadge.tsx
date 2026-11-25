type Tone = "neutral" | "ok" | "warn" | "danger";

const CLASS: Record<Tone, string> = {
  neutral: "ds-badge",
  ok: "ds-badge ds-badge-ok",
  warn: "ds-badge ds-badge-warn",
  danger: "ds-badge ds-badge-danger",
};

export function StatusBadge({ tone = "neutral", children, testId }: { tone?: Tone; children: React.ReactNode; testId?: string }) {
  return (
    <span className={CLASS[tone]} data-testid={testId}>
      {children}
    </span>
  );
}

export function ActiveBadge({ active }: { active: boolean }) {
  return <StatusBadge tone={active ? "ok" : "neutral"}>{active ? "فعال" : "غیرفعال"}</StatusBadge>;
}
