"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import {
  operationalPresentation,
  operationalStatusLabel,
  type OpsPresentation,
} from "@/lib/format/operational-status";

type Props = {
  status: string;
  needsStatus?: boolean;
  appointmentId: string;
};

/**
 * PO-approved operational badge. Needs-status pulses ≤2 times when newly unresolved
 * for this appointment id in the current session — not on every refresh remount.
 */
export function OperationalStatusBadge({ status, needsStatus, appointmentId }: Props) {
  const presentation = operationalPresentation(status, { needsStatus });
  const label = operationalStatusLabel(presentation);
  const [pulse, setPulse] = useState(false);
  const seen = useRef<Set<string>>(readSeen());

  useEffect(() => {
    if (presentation !== "needs_status") return;
    if (seen.current.has(appointmentId)) return;
    seen.current.add(appointmentId);
    writeSeen(seen.current);
    setPulse(true);
    const t = window.setTimeout(() => setPulse(false), 1600);
    return () => window.clearTimeout(t);
  }, [appointmentId, presentation]);

  return (
    <span
      className={`ds-ops-badge ds-ops-badge-${presentation}${pulse ? " is-pulse" : ""}`}
      data-testid="ops-status-badge"
      data-presentation={presentation}
    >
      {presentation === "needs_status" ? <Icon name="alert" size="sm" /> : null}
      {presentation === "completed" ? <Icon name="check" size="sm" /> : null}
      {presentation === "cancelled" ? <Icon name="close" size="sm" /> : null}
      <span>{label}</span>
    </span>
  );
}

function storageKey() {
  return "clinic.ops.needsPulse.v1";
}

function readSeen(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.sessionStorage.getItem(storageKey());
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as string[];
    return new Set(Array.isArray(parsed) ? parsed.slice(-200) : []);
  } catch {
    return new Set();
  }
}

function writeSeen(set: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(storageKey(), JSON.stringify([...set].slice(-200)));
  } catch {
    /* ignore quota */
  }
}

export type { OpsPresentation };
