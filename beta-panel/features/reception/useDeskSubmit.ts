"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  formatApiError,
  formatTehran,
  sortedConflictIds,
  type BookingIntent,
  type OverlapConflict,
} from "@/lib/client";
import type { GroupBookingIntent } from "@/lib/booking";
import {
  eligibleResourcesForRequirements,
  requiredSelectionCount,
  validateResourceSelection,
} from "@/lib/resources";
import { postGroupAppointments, postManualAppointment } from "./desk-booking-api";
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
  const {
    selectedResourceIds,
    localStart,
    pendingConflicts,
    setPendingConflicts,
    pendingConflictLineId,
    setPendingConflictLineId,
    pendingLineConflicts,
    setPendingLineConflicts,
    immediateCheckIn,
    setLastBooking,
    keyStore,
  } = state;
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

  function recordBooking(
    appointmentId: string,
    startIso: string,
    flags: { overlapAcknowledged: boolean; replayed?: boolean },
  ) {
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
      immediateCheckIn,
      ...overrides,
    };
  }

  function buildGroupIntent(
    ackByLine: Record<string, OverlapConflict[]> | null = null,
  ): GroupBookingIntent | null {
    if (!selectedPatient || draftLines.length === 0) return null;
    return {
      patientId: selectedPatient.patient_profile_id,
      immediateCheckIn,
      lines: draftLines.map((line) => {
        const lineConflicts = ackByLine?.[line.key];
        return {
          clientLineId: line.key,
          serviceId: line.serviceId,
          resourceIds: line.resourceIds,
          startLocal: line.localStart,
          durationMinutes: line.durationMinutes,
          acknowledgeOverlap: !!lineConflicts,
          acknowledgedConflictIds: lineConflicts ? sortedConflictIds(lineConflicts) : [],
        };
      }),
    };
  }

  function applyGroupConflicts(lineConflicts: Record<string, OverlapConflict[]>) {
    const entries = Object.entries(lineConflicts);
    if (!entries.length) {
      setPendingConflicts([]);
      setPendingConflictLineId(null);
      setPendingLineConflicts({});
      return;
    }
    setPendingLineConflicts(lineConflicts);
    // Show the first conflicting line's snapshot; confirm resubmits the whole group.
    const [lineId, conflicts] = entries[0];
    setPendingConflictLineId(lineId);
    setPendingConflicts(conflicts);
    const serviceName =
      draftLines.find((line) => line.key === lineId)?.serviceName ?? "خدمت";
    setError(`تداخل برای «${serviceName}» — گروه ثبت نشد (همه یا هیچ)`);
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
        setPendingConflictLineId(null);
        setPendingLineConflicts(null);
        setError(null);
        return;
      }
      if (!response.ok) {
        setError(formatApiError(data, "ثبت نوبت ناموفق بود"));
        return;
      }
      setPendingConflicts(null);
      setPendingConflictLineId(null);
      setPendingLineConflicts(null);
      const statusNote = data.status === "CHECKED_IN" ? " — حضور ثبت شد" : "";
      setMessage(
        `نوبت ثبت شد — کد پیگیری: ${data.appointment_id}${replayNote(data.replayed)}${statusNote} — ${formatTehran(startIso)}`,
      );
      recordBooking(String(data.appointment_id), startIso, {
        overlapAcknowledged: false,
        replayed: data.replayed,
      });
    } catch {
      setError(
        "ارتباط با سرور برقرار نشد و نتیجه نامشخص است. می‌توانید دوباره «ثبت نوبت» را بزنید؛ نوبت تکراری ایجاد نمی‌شود.",
      );
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
      // Group path: ack belongs to a specific draft line, never the current form selection.
      if (pendingConflictLineId && pendingLineConflicts && draftLines.length > 0) {
        const intent = buildGroupIntent(pendingLineConflicts);
        if (!intent) {
          setError("درخواست تأیید ناقص است");
          return;
        }
        const { response, data, lineConflicts } = await postGroupAppointments(
          intent,
          keyStore.current.keyForGroup(intent),
        );
        if (response.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (lineConflicts && Object.keys(lineConflicts).length > 0) {
          applyGroupConflicts(lineConflicts);
          keyStore.current.clear();
          setError("تعارض‌ها تغییر کرده است — فهرست به‌روز شد؛ دوباره تأیید کنید");
          return;
        }
        if (response.status === 403) {
          setPendingConflicts(null);
          setPendingConflictLineId(null);
          setPendingLineConflicts(null);
          setError("اجازه تأیید تداخل نوبت دستی برای این کاربر وجود ندارد");
          return;
        }
        if (!response.ok) {
          setError(formatApiError(data, "تأیید تداخل گروه ناموفق بود"));
          return;
        }
        setPendingConflicts(null);
        setPendingConflictLineId(null);
        setPendingLineConflicts(null);
        clearDraftLines?.();
        const ids = (data.lines ?? []).map((line) => line.appointment_id);
        setMessage(
          `گروه پذیرش با تأیید تداخل ثبت شد — ${ids.length} نوبت: ${ids.join("، ")}${replayNote(data.replayed)}`,
        );
        if (data.lines?.[0]) {
          const first = draftLines[0];
          recordBooking(data.lines[0].appointment_id, "", {
            overlapAcknowledged: true,
            replayed: data.replayed,
          });
          void first;
        }
        return;
      }

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
      recordBooking(String(data.appointment_id), startIso, {
        overlapAcknowledged: true,
        replayed: data.replayed,
      });
    } catch {
      setError(
        "ارتباط با سرور برقرار نشد و نتیجه نامشخص است. می‌توانید دوباره تأیید کنید؛ نوبت تکراری ایجاد نمی‌شود.",
      );
    } finally {
      confirmingRef.current = false;
      setSubmitting(false);
    }
  }

  function dismissOverlap() {
    setPendingConflicts(null);
    setPendingConflictLineId(null);
    setPendingLineConflicts(null);
    keyStore.current.clear();
  }

  /**
   * Submit queued service lines as one atomic group under a single Idempotency-Key.
   * On 409, conflicts are shown for the specific client_line_id; drafts are preserved.
   */
  async function submitGroup() {
    if (submitting || !selectedPatient || draftLines.length === 0) return;
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const intent = buildGroupIntent(pendingLineConflicts);
      if (!intent) {
        setError("گروه پذیرش ناقص است");
        return;
      }
      const { response, data, lineConflicts } = await postGroupAppointments(
        intent,
        keyStore.current.keyForGroup(intent),
      );
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (lineConflicts && Object.keys(lineConflicts).length > 0) {
        applyGroupConflicts(lineConflicts);
        return;
      }
      if (!response.ok) {
        setError(formatApiError(data, "ثبت گروه ناموفق بود"));
        return;
      }
      setPendingConflicts(null);
      setPendingConflictLineId(null);
      setPendingLineConflicts(null);
      clearDraftLines?.();
      const ids = (data.lines ?? []).map((line) => line.appointment_id);
      const checkedIn = (data.lines ?? []).some((line) => line.status === "CHECKED_IN");
      setMessage(
        `گروه پذیرش ثبت شد — ${ids.length} نوبت: ${ids.join("، ")}${replayNote(data.replayed)}${
          checkedIn ? " — حضور ثبت شد" : ""
        }`,
      );
      if (data.lines?.[0]) {
        recordBooking(data.lines[0].appointment_id, "", {
          overlapAcknowledged: false,
          replayed: data.replayed,
        });
      }
    } catch {
      // Preserve drafts on network error — atomic group either fully committed or not.
      setError(
        "ارتباط با سرور برقرار نشد و نتیجه نامشخص است. پیش‌فاکتور حفظ شد؛ می‌توانید دوباره ثبت کنید — نوبت تکراری ایجاد نمی‌شود.",
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
