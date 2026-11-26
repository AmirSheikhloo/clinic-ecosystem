"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import type { IconName } from "@/components/ui/icon-paths";

export type ToastTone = "ok" | "danger" | "info";
type ToastItem = { id: number; tone: ToastTone; message: string; leaving: boolean };

type ToastApi = {
  notify: (tone: ToastTone, message: string) => void;
  success: (message: string) => void;
  failure: (message: string) => void;
};

const NOOP: ToastApi = { notify: () => {}, success: () => {}, failure: () => {} };
const ToastContext = createContext<ToastApi>(NOOP);

const LIFETIME_MS: Record<ToastTone, number> = { ok: 5000, info: 5000, danger: 9000 };
const LEAVE_MS = 180;
const MAX_VISIBLE = 4;
const ICON: Record<ToastTone, IconName> = { ok: "success", danger: "alert", info: "info" };
const TONE_CLASS: Record<ToastTone, string> = { ok: "ds-toast-ok", danger: "ds-toast-danger", info: "ds-toast-info" };
const TONE_COLOR: Record<ToastTone, string> = {
  ok: "text-[var(--ds-success)]",
  danger: "text-[var(--ds-danger)]",
  info: "text-[var(--ds-info)]",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, leaving: true } : item)));
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), LEAVE_MS);
  }, []);

  const notify = useCallback(
    (tone: ToastTone, message: string) => {
      const id = nextId.current++;
      setItems((current) => [...current.slice(-(MAX_VISIBLE - 1)), { id, tone, message, leaving: false }]);
      window.setTimeout(() => dismiss(id), LIFETIME_MS[tone]);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      notify,
      success: (message) => notify("ok", message),
      failure: (message) => notify("danger", message),
    }),
    [notify],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="ds-toast-region" data-testid="toast-region" aria-live="polite" aria-atomic="false">
        {items.map((item) => (
          <div
            key={item.id}
            role={item.tone === "danger" ? "alert" : "status"}
            data-testid="toast-item"
            className={`ds-toast ${TONE_CLASS[item.tone]} ${item.leaving ? "ds-toast-leaving" : ""}`.trim()}
          >
            <Icon name={ICON[item.tone]} size="sm" className={`mt-1 ${TONE_COLOR[item.tone]}`} />
            <span className="min-w-0 flex-1">{item.message}</span>
            <button
              type="button"
              className="rounded text-[var(--ds-text-muted)] hover:text-[var(--ds-text)]"
              aria-label="بستن اعلان"
              onClick={() => dismiss(item.id)}
            >
              <Icon name="close" size="sm" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
