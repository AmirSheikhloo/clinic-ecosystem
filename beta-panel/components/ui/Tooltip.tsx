import type { ReactNode } from "react";

type Props = { label: string; children: ReactNode; below?: boolean; disabled?: boolean };

/**
 * Visual-only hint for controls that already carry an accessible name
 * (aria-label or visible text). Shows on hover and keyboard focus.
 */
export function Tooltip({ label, children, below = false, disabled = false }: Props) {
  if (disabled) return <>{children}</>;
  return (
    <span className="ds-tooltip-wrap">
      {children}
      <span aria-hidden="true" className={`ds-tooltip ${below ? "ds-tooltip-below" : ""}`.trim()}>
        {label}
      </span>
    </span>
  );
}

/** Small "i" helper that explains a field; the text is available to screen readers. */
export function InfoHint({ text }: { text: string }) {
  return (
    <Tooltip label={text} below>
      <span
        tabIndex={0}
        role="note"
        aria-label={text}
        className="inline-grid h-4 w-4 cursor-help place-items-center rounded-full border border-[var(--ds-border-strong)] text-[10px] leading-none text-[var(--ds-text-muted)]"
      >
        ?
      </span>
    </Tooltip>
  );
}
