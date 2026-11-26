"use client";

import { useEffect, useLayoutEffect, useRef, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  onClose: () => void;
  anchorRef: RefObject<HTMLElement | null>;
  /** Element that regains focus when the popover closes with Escape/Tab; defaults to the anchor. */
  returnFocusRef?: RefObject<HTMLElement | null>;
  label: string;
  children: ReactNode;
  role?: "dialog" | "group";
  className?: string;
  testId?: string;
  /** Which edge of the anchor the panel aligns to; RTL "start" is the right edge. */
  align?: "start" | "end";
};

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]';
const GAP = 6;
const MARGIN = 8;

/**
 * Floating panel anchored to a control. Rendered in a portal with fixed positioning so it is never
 * clipped by dialogs or scroll containers. Escape and outside press close it; Tab leaves it.
 */
export function Popover({ open, onClose, anchorRef, returnFocusRef, label, children, role = "group", className = "", testId, align = "start" }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useLayoutEffect(() => {
    if (!open) return;
    function place() {
      const panel = panelRef.current;
      const anchor = anchorRef.current;
      if (!panel || !anchor) return;
      const rect = anchor.getBoundingClientRect();
      const width = panel.offsetWidth;
      const height = panel.offsetHeight;
      const viewportW = document.documentElement.clientWidth;
      const viewportH = window.innerHeight;
      let left = align === "start" ? rect.right - width : rect.left;
      left = Math.min(Math.max(left, MARGIN), Math.max(MARGIN, viewportW - width - MARGIN));
      const fitsBelow = rect.bottom + GAP + height <= viewportH - MARGIN;
      const top = fitsBelow ? rect.bottom + GAP : Math.max(MARGIN, rect.top - GAP - height);
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
      panel.style.visibility = "visible";
    }
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, anchorRef, align]);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const anchor = anchorRef.current;
    const preferred = panel?.querySelector<HTMLElement>("[data-autofocus]") ?? panel?.querySelector<HTMLElement>(FOCUSABLE);
    (preferred ?? panel)?.focus();

    function close(restoreFocus: boolean) {
      onCloseRef.current();
      if (restoreFocus) (returnFocusRef?.current ?? anchor)?.focus();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (!panel?.contains(document.activeElement) && document.activeElement !== anchor) return;
      if (event.key === "Escape") {
        event.stopPropagation();
        event.preventDefault();
        close(true);
      } else if (event.key === "Tab") {
        event.preventDefault();
        close(true);
      }
    }
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (panel?.contains(target) || anchor?.contains(target)) return;
      close(false);
    }
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("pointerdown", onPointerDown, true);
    };
  }, [open, anchorRef, returnFocusRef]);

  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div
      ref={panelRef}
      role={role}
      aria-label={label}
      tabIndex={-1}
      data-testid={testId}
      className={`ds-popover ${className}`.trim()}
      style={{ visibility: "hidden", top: 0, left: 0 }}
    >
      {children}
    </div>,
    document.body,
  );
}
