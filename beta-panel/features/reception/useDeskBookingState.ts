"use client";

import { useRef, useState } from "react";
import { IdempotencyKeyStore, type OverlapConflict } from "@/lib/client";

export type BookedLineLink = {
  clientLineId: string;
  serviceId: string;
  appointmentId: string;
};

export type BookedSummary = {
  appointmentId: string;
  startIso: string;
  patientId: string;
  patientName: string;
  serviceName: string;
  overlapAcknowledged: boolean;
  replayed: boolean;
  /** Per-service appointment links for multi-line desk checkout. */
  lines?: BookedLineLink[];
};

/** Mutable booking-intent state; any change to the intent invalidates cached keys and pending overlap. */
export function useDeskBookingState() {
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [localStart, setLocalStartRaw] = useState("");
  const [pendingConflicts, setPendingConflicts] = useState<OverlapConflict[] | null>(null);
  /** When set, pendingConflicts belong to this draft client_line_id (group ack must target it). */
  const [pendingConflictLineId, setPendingConflictLineId] = useState<string | null>(null);
  const [pendingLineConflicts, setPendingLineConflicts] = useState<Record<
    string,
    OverlapConflict[]
  > | null>(null);
  const [immediateCheckIn, setImmediateCheckIn] = useState(false);
  const [lastBooking, setLastBooking] = useState<BookedSummary | null>(null);
  const keyStore = useRef(new IdempotencyKeyStore());

  function invalidate() {
    setPendingConflicts(null);
    setPendingConflictLineId(null);
    setPendingLineConflicts(null);
    setLastBooking(null);
    keyStore.current.clear();
  }

  function resetForServiceChange() {
    setSelectedResourceIds([]);
    invalidate();
  }

  function toggleResource(id: string) {
    setPendingConflicts(null);
    setPendingConflictLineId(null);
    setPendingLineConflicts(null);
    setSelectedResourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  function setLocalStart(value: string) {
    setLocalStartRaw(value);
    setImmediateCheckIn(false);
    invalidate();
  }

  function markWalkInNow(value: string) {
    setLocalStartRaw(value);
    setImmediateCheckIn(true);
    invalidate();
  }

  return {
    selectedResourceIds,
    toggleResource,
    localStart,
    setLocalStart,
    markWalkInNow,
    immediateCheckIn,
    pendingConflicts,
    setPendingConflicts,
    pendingConflictLineId,
    setPendingConflictLineId,
    pendingLineConflicts,
    setPendingLineConflicts,
    lastBooking,
    setLastBooking,
    keyStore,
    invalidate,
    resetForServiceChange,
  };
}

export type DeskBookingState = ReturnType<typeof useDeskBookingState>;
