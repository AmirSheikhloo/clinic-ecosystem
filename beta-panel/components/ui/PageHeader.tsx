import type { ReactNode } from "react";

type Props = { title: string; description?: ReactNode; actions?: ReactNode };

export function PageHeader({ title, description, actions }: Props) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">{title}</h2>
        {description ? <p className="text-[var(--ds-text-muted)]">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
