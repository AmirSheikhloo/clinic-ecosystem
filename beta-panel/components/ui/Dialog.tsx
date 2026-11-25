"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { Icon } from "./Icon";

type Props = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  testId?: string;
  size?: "md" | "lg";
  /** "center" modal, "drawer" slides from the inline-end edge (left in RTL), "drawer-start" from the right. */
  placement?: "center" | "drawer" | "drawer-start";
  description?: string;
  footer?: ReactNode;
};

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/** Open dialogs, innermost last: only the top one handles Escape and focus trapping. */
const openStack: symbol[] = [];

export function Dialog({ open, title, onClose, children, testId, size = "md", placement = "center", description, footer }: Props) {
  const descriptionId = useId();
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const self = Symbol("dialog");
    openStack.push(self);
    const previous = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const first =
      panel?.querySelector<HTMLElement>("[data-autofocus]") ??
      panel?.querySelector<HTMLElement>(".ds-dialog-body")?.querySelector<HTMLElement>(FOCUSABLE) ??
      panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (openStack[openStack.length - 1] !== self) return;
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!nodes.length) {
        event.preventDefault();
        return;
      }
      const firstNode = nodes[0];
      const lastNode = nodes[nodes.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === firstNode) {
        event.preventDefault();
        lastNode.focus();
      } else if (!event.shiftKey && active === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      const index = openStack.indexOf(self);
      if (index >= 0) openStack.splice(index, 1);
      previous?.focus?.();
    };
  }, [open]);

  if (!open) return null;
  const drawer = placement !== "center";
  const overlayClass = `ds-overlay ${drawer ? "ds-overlay-drawer" : ""} ${placement === "drawer-start" ? "ds-overlay-drawer-start" : ""}`.trim();
  const panelClass = [
    "ds-dialog",
    placement === "drawer" ? "ds-drawer" : "",
    placement === "drawer-start" ? "ds-drawer ds-drawer-start" : "",
    size === "lg" && !drawer ? "ds-dialog-lg" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div
      className={overlayClass}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        data-testid={testId}
        className={panelClass}
      >
        <div className="ds-dialog-head">
          <div className="min-w-0">
            <h3 id={titleId} className="text-lg font-bold">
              {title}
            </h3>
            {description ? (
              <p id={descriptionId} className="mt-0.5 text-sm text-[var(--ds-text-muted)]">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            className="ds-btn ds-btn-subtle ds-btn-sm ds-btn-icon !text-[var(--ds-text-muted)]"
            aria-label="بستن"
            onClick={onClose}
          >
            <Icon name="close" size="sm" />
          </button>
        </div>
        <div className="ds-dialog-body">{children}</div>
        {footer ? <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--ds-border)] px-5 py-3">{footer}</div> : null}
      </div>
    </div>
  );
}
