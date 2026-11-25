"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

export type ToastTone = "ok" | "danger" | "info";
type ToastItem = { id: number; tone: ToastTone; message: string };

type ToastApi = {
  notify: (tone: ToastTone, message: string) => void;
  success: (message: string) => void;
  failure: (message: string) => void;
};

const NOOP: ToastApi = { notify: () => {}, success: () => {}, failure: () => {} };
const ToastContext = createContext<ToastApi>(NOOP);

const LIFETIME_MS: Record<ToastTone, number> = { ok: 5000, info: 5000, danger: 9000 };
const MAX_VISIBLE = 4;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback(
    (tone: ToastTone, message: string) => {
      const id = nextId.current++;
      setItems((current) => [...current.slice(-(MAX_VISIBLE - 1)), { id, tone, message }]);
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
            className={`ds-toast animate-fade-in ${
              item.tone === "ok" ? "ds-toast-ok" : item.tone === "danger" ? "ds-toast-danger" : ""
            }`}
          >
            <span>{item.message}</span>
            <button
              type="button"
              className="text-[var(--ds-text-muted)] hover:text-[var(--ds-text)]"
              aria-label="بستن اعلان"
              onClick={() => dismiss(item.id)}
            >
              ×
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
