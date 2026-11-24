type Props = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: Props) {
  return (
    <div className="rounded-[var(--ds-radius-lg)] border border-dashed border-[var(--ds-border-strong)] bg-[var(--ds-surface)]/70 px-4 py-10 text-center">
      <p className="font-medium text-[var(--ds-text)]">{title}</p>
      {description && (
        <p className="mt-2 text-sm text-[var(--ds-text-muted)]">{description}</p>
      )}
    </div>
  );
}
