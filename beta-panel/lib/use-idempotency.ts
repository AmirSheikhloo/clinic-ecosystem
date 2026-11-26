"use client";

import { useCallback, useRef } from "react";

/**
 * One Idempotency-Key per distinct request payload: an automatic or manual retry
 * of the same intent reuses the key (safe replay); a changed payload gets a new one.
 */
export function useIdempotencyKey() {
  const current = useRef<{ fingerprint: string; key: string } | null>(null);
  const keyFor = useCallback((payload: unknown) => {
    const fingerprint = JSON.stringify(payload);
    if (current.current?.fingerprint !== fingerprint) {
      current.current = { fingerprint, key: crypto.randomUUID() };
    }
    return current.current.key;
  }, []);
  const reset = useCallback(() => {
    current.current = null;
  }, []);
  return { keyFor, reset };
}
