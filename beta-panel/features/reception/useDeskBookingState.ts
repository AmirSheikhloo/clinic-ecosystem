"use client";

import { useRef, useState } from "react";
import { IdempotencyKeyStore, type OverlapConflict } from "@/lib/client";

export type BookedSummary = {
  appointmentId: string;
  startIso: string;
  patientId: string;
  patientName: string;
  serviceName: string;
  overlapAcknowledged: boolean;
  replayed: boolean;
};

/** Mutable booking-intent state; any change to the intent invalidates cached keys and pending overlap. */
export function useDeskBookingState() {
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [localStart, setLocalStartRaw] = useState("");
  const [pendingConflicts, setPendingConflicts] = useState<OverlapConflict[] | null>(null);
  const [lastBooking, setLastBooking] = useState<BookedSummary | null>(null);
  const keyStore = useRef(new IdempotencyKeyStore());

  function invalidate() {
    setPendingConflicts(null);
    setLastBooking(null);
    keyStore.current.clear();
  }

  function resetForServiceChange() {
    setSelectedResourceIds([]);
    invalidate();
  }

  function toggleResource(id: string) {
    setPendingConflicts(null);
    setSelectedResourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  function setLocalStart(value: string) {
    setLocalStartRaw(value);
    invalidate();
  }

  return {
    selectedResourceIds,
    toggleResource,
    localStart,
    setLocalStart,
    pendingConflicts,
    setPendingConflicts,
    lastBooking,
    setLastBooking,
    keyStore,
    invalidate,
    resetForServiceChange,
  };
}

export type DeskBookingState = ReturnType<typeof useDeskBookingState>;
