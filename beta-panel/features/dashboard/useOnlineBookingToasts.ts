"use client";

import { useEffect, useRef } from "react";
import { useToast } from "@/components/feedback/Toast";
import { useApiQuery } from "@/lib/use-api-query";

type NotificationItem = {
  id: string;
  notification_type: string;
  title: string;
  body: string;
};

type ListResponse = { items: NotificationItem[]; unread_count: number };

const SEEN_KEY = "clinic.notify.toastSeen.v1";

/** Surface new ONLINE booking notifications as non-blocking toasts (no focus steal). */
export function useOnlineBookingToasts(enabled: boolean, refreshKey: number) {
  const toast = useToast();
  const seen = useRef<Set<string>>(readSeen());
  const primed = useRef(false);
  const query = useApiQuery<ListResponse>(
    enabled ? "/api/v1/notifications?limit=20" : null,
    "اعلان",
    refreshKey,
  );

  useEffect(() => {
    const items = query.data?.items ?? [];
    if (!items.length) return;
    const online = items.filter(
      (i) => i.notification_type.toUpperCase().includes("ONLINE") || i.title.includes("آنلاین"),
    );
    if (!primed.current) {
      for (const item of online) seen.current.add(item.id);
      writeSeen(seen.current);
      primed.current = true;
      return;
    }
    const fresh = online.filter((i) => !seen.current.has(i.id));
    if (!fresh.length) return;
    for (const item of fresh) seen.current.add(item.id);
    writeSeen(seen.current);
    if (fresh.length === 1) {
      toast.notify("info", `${fresh[0].title || "رزرو آنلاین جدید"} — ${fresh[0].body || "یک نوبت جدید ثبت شد."}`);
    } else {
      toast.notify("info", `رزروهای آنلاین جدید — ${fresh.length} رزرو آنلاین جدید ثبت شد.`);
    }
  }, [query.data, toast]);
}

function readSeen(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.sessionStorage.getItem(SEEN_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function writeSeen(set: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(SEEN_KEY, JSON.stringify([...set].slice(-100)));
  } catch {
    /* ignore */
  }
}
