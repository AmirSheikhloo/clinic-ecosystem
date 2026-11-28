"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { useSession } from "@/components/session/SessionProvider";
import { apiJson } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api-query";

type NotificationItem = {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  deep_link?: string | null;
  related_appointment_id?: string | null;
  created_at_utc: string;
  read: boolean;
};

type ListResponse = { items: NotificationItem[]; unread_count: number };

/** Restrained top-bar notification center. Reading ≠ booking review. */
export function NotificationBell() {
  const { status } = useSession();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [tick, setTick] = useState(0);
  const query = useApiQuery<ListResponse>(
    status === "ready" ? "/api/v1/notifications?limit=30" : null,
    "بارگذاری اعلان‌ها ناموفق بود",
    tick,
  );
  const unread = query.data?.unread_count ?? 0;
  const items = query.data?.items ?? [];

  useEffect(() => {
    if (!open) return;
    function onDoc(ev: MouseEvent) {
      if (!rootRef.current?.contains(ev.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function markRead(id: string) {
    await apiJson(`/api/v1/notifications/${id}/read`, { method: "POST" });
    setTick((v) => v + 1);
  }

  return (
    <div className="ds-notify" ref={rootRef} data-testid="notification-bell">
      <button
        type="button"
        className="ds-notify-trigger"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={unread ? `اعلان‌ها، ${unread} خوانده‌نشده` : "اعلان‌ها"}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="bell" />
        {unread > 0 ? (
          <span className="ds-notify-badge" aria-hidden="true">
            {unread > 99 ? "99+" : unread}
          </span>
        ) : null}
      </button>
      {open ? (
        <div id={panelId} className="ds-notify-panel" role="dialog" aria-label="مرکز اعلان‌ها">
          {query.loading && !query.data ? <p className="ds-hint p-3">در حال بارگذاری…</p> : null}
          {query.error ? <p className="ds-hint p-3 text-[var(--ds-danger)]">{query.error.message}</p> : null}
          {!query.loading && items.length === 0 ? (
            <p className="ds-hint p-3" data-testid="notifications-empty">
              اعلان جدیدی نیست
            </p>
          ) : null}
          <ul className="ds-notify-list">
            {items.map((item) => (
              <li key={item.id} className={item.read ? "is-read" : "is-unread"} data-testid="notification-item">
                <button
                  type="button"
                  className="ds-notify-item"
                  onClick={() => {
                    if (!item.read) void markRead(item.id);
                    if (item.deep_link) window.location.href = item.deep_link;
                  }}
                >
                  <span className="font-medium">{item.title}</span>
                  <span className="block text-xs text-[var(--ds-text-muted)]">{item.body}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
