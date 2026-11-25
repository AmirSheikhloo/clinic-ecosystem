import type { ReactNode } from "react";

type Props = { open: boolean; children: ReactNode; id?: string; testId?: string };

/** Height-animated expandable region; hidden content is removed from the tab order. */
export function Collapsible({ open, children, id, testId }: Props) {
  return (
    <div id={id} className="ds-collapsible" data-open={open} data-testid={testId} aria-hidden={!open}>
      <div inert={!open}>{children}</div>
    </div>
  );
}
