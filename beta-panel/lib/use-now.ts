"use client";

import { useSyncExternalStore } from "react";

/** Wall-clock time rounded down to `stepMs`, re-read on a timer; 0 during server render. */
export function useNow(stepMs = 60_000): number {
  return useSyncExternalStore(
    (notify) => {
      const timer = window.setInterval(notify, stepMs);
      return () => window.clearInterval(timer);
    },
    () => Math.floor(Date.now() / stepMs) * stepMs,
    () => 0,
  );
}
