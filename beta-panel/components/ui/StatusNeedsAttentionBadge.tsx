"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

type Props = {
  /** When true, allow at most two gentle pulses once per appointment id. */
  animate?: boolean;
  appointmentId?: string;
};

const seen = new Set<string>();

/**
 * Shared amber warning badge: نیازمند تعیین وضعیت (Task 34 §9 / DASH-03).
 * Pulses at most twice, then stays static. Respects prefers-reduced-motion.
 */
export function StatusNeedsAttentionBadge({ animate = true, appointmentId }: Props) {
  const [pulse, setPulse] = useState(false);
  const reduced = useRef(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
  }, []);

  useEffect(() => {
    if (!animate || reduced.current) return;
    const key = appointmentId || "anon";
    if (seen.has(key)) return;
    seen.add(key);
    setPulse(true);
    const t = window.setTimeout(() => setPulse(false), 1600);
    return () => window.clearTimeout(t);
  }, [animate, appointmentId]);

  return (
    <span
      className={`ds-needs-status-badge${pulse ? " is-pulse" : ""}`}
      data-testid="needs-status-badge"
      role="status"
      aria-label="نیازمند تعیین وضعیت"
    >
      <Icon name="alert" size="sm" />
      <span>نیازمند تعیین وضعیت</span>
    </span>
  );
}
