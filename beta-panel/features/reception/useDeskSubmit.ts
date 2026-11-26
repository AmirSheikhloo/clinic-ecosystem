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
import type { DraftServiceLine, Patient } from "./types";

type Inputs = {
  feedback: DeskFeedback;
  state: DeskBookingState;
  catalog: DeskCatalog;
  selectedPatient: Patient | null;
  draftLines?: DraftServiceLine[];
  clearDraftLines?: () => void;
};

const replayNote = (replayed?: boolean) => (replayed ? " (بازیابی تکرار)" : "");

/** Validation, submit and explicit overlap confirmation for manual bookings. */
export function useDeskSubmit({
  feedback,
  state,
  catalog,
  selectedPatient,
  draftLines = [],
  clearDraftLines,
}: Inputs) {
  const router = useRouter();
  const { setError, setMessage } = feedback;
  const { selectedResourceIds, localStart, pendingConflicts, setPendingConflicts, setLastBooking, keyStore } = state;
  const { serviceId, requirements, requirementsReady, resources, durationMinutes, services } = catalog;
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

  function recordBooking(appointmentId: string, startIso: string, flags: { overlapAcknowledged: boolean; replayed?: boolean }) {
    if (!selectedPatient) return;
    setLastBooking({
      appointmentId,
      startIso,
      patientId: selectedPatient.patient_profile_id,
      patientName: `${selectedPatient.first_name} ${selectedPatient.last_name}`,
      serviceName: services.find((item) => item.id === serviceId)?.service_name ?? "",
      overlapAcknowledged: flags.overlapAcknowledged,
      replayed: !!flags.replayed,
    });
  }

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
      setMessage(`نوبت ثبت شد — کد پیگیری: ${data.appointment_id}${replayNote(data.replayed)} — ${formatTehran(startIso)}`);
      recordBooking(String(data.appointment_id), startIso, { overlapAcknowledged: false, replayed: data.replayed });
    } catch {
      setError("ارتباط با سرور برقرار نشد و نتیجه نامشخص است. می‌توانید دوباره «ثبت نوبت» را بزنید؛ نوبت تکراری ایجاد نمی‌شود.");
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
        `نوبت با تأیید تداخل ثبت شد — کد پیگیری: ${data.appointment_id}${replayNote(data.replayed)} — ${formatTehran(startIso)}`,
      );
      recordBooking(String(data.appointment_id), startIso, { overlapAcknowledged: true, replayed: data.replayed });
    } catch {
      setError("ارتباط با سرور برقرار نشد و نتیجه نامشخص است. می‌توانید دوباره تأیید کنید؛ نوبت تکراری ایجاد نمی‌شود.");
    } finally {
      confirmingRef.current = false;
      setSubmitting(false);
    }
  }

  function dismissOverlap() {
    setPendingConflicts(null);
    keyStore.current.clear();
  }

  /**
   * Submit queued service lines as independent appointments (sequential).
   * Partial success is reported honestly — each line keeps its own idempotency key.
   */
  async function submitGroup() {
    if (submitting || !selectedPatient || draftLines.length === 0) return;
    setError(null);
    setMessage(null);
    setSubmitting(true);
    const created: string[] = [];
    try {
      for (const line of draftLines) {
        const intent: BookingIntent = {
          patientId: selectedPatient.patient_profile_id,
          serviceId: line.serviceId,
          resourceIds: line.resourceIds,
          startLocal: line.localStart,
          durationMinutes: line.durationMinutes,
          acknowledgeOverlap: false,
          acknowledgedConflictIds: [],
        };
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
          setError(
            created.length
              ? `تداخل برای «${line.serviceName}» — ${created.length} نوبت قبلاً ثبت شد`
              : `تداخل برای «${line.serviceName}»؛ گروه متوقف شد`,
          );
          return;
        }
        if (!response.ok) {
          setError(
            created.length
              ? `${formatApiError(data, "ثبت گروه ناقص ماند")} — ${created.length} نوبت ثبت شد`
              : formatApiError(data, "ثبت گروه ناموفق بود"),
          );
          return;
        }
        created.push(String(data.appointment_id));
        recordBooking(String(data.appointment_id), startIso, {
          overlapAcknowledged: false,
          replayed: data.replayed,
        });
      }
      clearDraftLines?.();
      setMessage(`گروه پذیرش ثبت شد — ${created.length} نوبت مستقل: ${created.join("، ")}`);
    } catch {
      setError(
        created.length
          ? `ارتباط قطع شد؛ ${created.length} نوبت ممکن است ثبت شده باشد — پیش از تکرار، فهرست نوبت‌ها را بررسی کنید`
          : "ارتباط با سرور برقرار نشد و نتیجه نامشخص است",
      );
    } finally {
      setSubmitting(false);
    }
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
    submitGroup,
  };
}
