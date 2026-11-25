"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { formatApiError, formatTehran, sortedConflictIds, type BookingIntent } from "@/lib/client";
import {
  eligibleResourcesForRequirements,
  requiredSelectionCount,
  validateResourceSelection,
} from "@/lib/resources";
import { postManualAppointment } from "./desk-booking-api";
import type { DeskBookingState } from "./useDeskBookingState";
import type { DeskCatalog } from "./useDeskCatalog";
import type { DeskFeedback } from "./useDeskFeedback";
import type { Patient } from "./types";

type Inputs = {
  feedback: DeskFeedback;
  state: DeskBookingState;
  catalog: DeskCatalog;
  selectedPatient: Patient | null;
};

const replayNote = (replayed?: boolean) => (replayed ? " (بازیابی تکرار)" : "");

/** Validation, submit and explicit overlap confirmation for manual bookings. */
export function useDeskSubmit({ feedback, state, catalog, selectedPatient }: Inputs) {
  const router = useRouter();
  const { setError, setMessage } = feedback;
  const { selectedResourceIds, localStart, pendingConflicts, setPendingConflicts, keyStore } = state;
  const { serviceId, requirements, requirementsReady, resources, durationMinutes } = catalog;
  const [submitting, setSubmitting] = useState(false);
  const confirmingRef = useRef(false);

  const resourcesById = useMemo(() => new Map(resources.map((item) => [item.id, item])), [resources]);
  const eligibleResources = useMemo(
    () => eligibleResourcesForRequirements(resources, requirements),
    [resources, requirements],
  );
  const selectionCheck = useMemo(
    () => validateResourceSelection(requirements, selectedResourceIds, resourcesById),
    [requirements, selectedResourceIds, resourcesById],
  );
  const neededCount = requiredSelectionCount(requirements);

  function baseIntent(overrides: Partial<BookingIntent> = {}): BookingIntent | null {
    if (!selectedPatient || !serviceId || !localStart) return null;
    return {
      patientId: selectedPatient.patient_profile_id,
      serviceId,
      resourceIds: selectedResourceIds,
      startLocal: localStart,
      durationMinutes,
      acknowledgeOverlap: false,
      acknowledgedConflictIds: [],
      ...overrides,
    };
  }

  const selectionOk: boolean = selectionCheck.ok;
  const canSubmit =
    catalog.catalogReady &&
    !!selectedPatient &&
    requirementsReady &&
    selectionOk &&
    !!localStart &&
    !submitting &&
    !pendingConflicts;

  async function submitAppointment(event: FormEvent) {
    event.preventDefault();
    if (submitting || !canSubmit) return;
    setError(null);
    setMessage(null);
    const intent = baseIntent();
    if (!intent) {
      setError("بیمار، خدمت و زمان الزامی است");
      return;
    }
    if (!requirementsReady) {
      setError("الزامات منابع هنوز آماده نیست");
      return;
    }
    if (!selectionCheck.ok) {
      setError(selectionCheck.message);
      return;
    }
    setSubmitting(true);
    try {
      const { response, data, startIso, conflicts } = await postManualAppointment(
        intent,
        keyStore.current.keyFor(intent),
      );
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (conflicts) {
        setPendingConflicts(conflicts);
        setError(null);
        return;
      }
      if (!response.ok) {
        setError(formatApiError(data, "ثبت نوبت ناموفق بود"));
        return;
      }
      setPendingConflicts(null);
      setMessage(`نوبت ثبت شد — شناسه: ${data.appointment_id}${replayNote(data.replayed)} — ${formatTehran(startIso)}`);
    } catch {
      setError("ارتباط برای ثبت نوبت برقرار نشد — نتیجه نامشخص است؛ همان درخواست را با همان کلید می‌توانید تکرار کنید");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmOverlap() {
    if (!pendingConflicts || submitting || confirmingRef.current) return;
    confirmingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const intent = baseIntent({
        acknowledgeOverlap: true,
        acknowledgedConflictIds: sortedConflictIds(pendingConflicts),
      });
      if (!intent) {
        setError("درخواست تأیید ناقص است");
        return;
      }
      const { response, data, startIso, conflicts } = await postManualAppointment(
        intent,
        keyStore.current.keyFor(intent),
      );
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (conflicts) {
        setPendingConflicts(conflicts);
        keyStore.current.clear();
        setError("تعارض‌ها تغییر کرده است — فهرست به‌روز شد؛ دوباره تأیید کنید");
        return;
      }
      if (response.status === 403) {
        setPendingConflicts(null);
        setError("اجازه تأیید تداخل نوبت دستی برای این کاربر وجود ندارد");
        return;
      }
      if (!response.ok) {
        setError(formatApiError(data, "تأیید تداخل ناموفق بود"));
        return;
      }
      setPendingConflicts(null);
      setMessage(
        `نوبت با تأیید تداخل ثبت شد — شناسه: ${data.appointment_id}${replayNote(data.replayed)} — ${formatTehran(startIso)}`,
      );
    } catch {
      setError("ارتباط برای تأیید تداخل برقرار نشد — نتیجه نامشخص است؛ همان تأیید را می‌توانید تکرار کنید");
    } finally {
      confirmingRef.current = false;
      setSubmitting(false);
    }
  }

  function dismissOverlap() {
    setPendingConflicts(null);
    keyStore.current.clear();
  }

  return {
    eligibleResources,
    selectionCheck,
    neededCount,
    canSubmit,
    submitting,
    submitAppointment,
    confirmOverlap,
    dismissOverlap,
  };
}
