import type { ReactNode } from "react";

type Props = { title: string; description?: ReactNode; actions?: ReactNode; meta?: ReactNode };

/** One page title per screen (the only h1 on a screen). */
export function PageHeader({ title, description, actions, meta }: Props) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 space-y-1">
        <h1 className="ds-page-title">{title}</h1>
        {description ? <p className="max-w-3xl text-sm text-[var(--ds-text-muted)]">{description}</p> : null}
        {meta ? <div className="flex flex-wrap items-center gap-2 pt-1">{meta}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
