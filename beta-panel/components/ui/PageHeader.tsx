import type { ReactNode } from "react";

type Props = { title: string; description?: ReactNode; actions?: ReactNode; meta?: ReactNode };

/**
 * One page title per screen (the only h1 on a screen). The title block flexes and wraps,
 * while the action area keeps its own size and never shrinks.
 */
export function PageHeader({ title, description, actions, meta }: Props) {
  return (
    <header className="ds-page-header">
      <div className="ds-page-header-text">
        <h1 className="ds-page-title">{title}</h1>
        {description ? <p className="ds-page-description">{description}</p> : null}
        {meta ? <div className="flex flex-wrap items-center gap-2 pt-1">{meta}</div> : null}
      </div>
      {actions ? <div className="ds-page-header-actions">{actions}</div> : null}
    </header>
  );
}
