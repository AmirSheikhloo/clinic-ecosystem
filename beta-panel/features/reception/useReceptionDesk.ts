"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch,
  extractOverlapConflicts,
  formatApiError,
  formatTehran,
  IdempotencyKeyStore,
  sortedConflictIds,
  tehranLocalToUtcIso,
  type ApiErrorBody,
  type BookingIntent,
  type OverlapConflict,
} from "@/lib/client";
import {
  eligibleResourcesForRequirements,
  requiredSelectionCount,
  validateResourceSelection,
  type Resource,
} from "@/lib/resources";
import type { Patient, RequirementsState, Service } from "./types";

export function useReceptionDesk() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [requirementsState, setRequirementsState] = useState<RequirementsState>({
    status: "idle",
  });
  const [serviceId, setServiceId] = useState("");
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [localStart, setLocalStart] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [pendingConflicts, setPendingConflicts] = useState<OverlapConflict[] | null>(null);
  const reqToken = useRef(0);
  const keyStore = useRef(new IdempotencyKeyStore());
  const confirmingRef = useRef(false);

  const durationMinutes = useMemo(() => {
    const svc = services.find((s) => s.id === serviceId);
    return svc?.default_duration_minutes || 30;
  }, [services, serviceId]);

  const requirements = useMemo(() => {
    if (requirementsState.status === "ready" && requirementsState.serviceId === serviceId) {
      return requirementsState.items;
    }
    return [];
  }, [requirementsState, serviceId]);

  const requirementsReady =
    !!serviceId
    && requirementsState.status === "ready"
    && requirementsState.serviceId === serviceId;

  const resourcesById = useMemo(
    () => new Map(resources.map((item) => [item.id, item])),
    [resources],
  );

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

  function invalidateBookingState() {
    setPendingConflicts(null);
    keyStore.current.clear();
  }

  function changeService(nextServiceId: string) {
    reqToken.current += 1;
    setServiceId(nextServiceId);
    setSelectedResourceIds([]);
    setPendingConflicts(null);
    keyStore.current.clear();
    if (!nextServiceId) {
      setRequirementsState({ status: "idle" });
      return;
    }
    setRequirementsState({ status: "loading", serviceId: nextServiceId });
  }

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const me = await apiFetch("/api/auth/me");
        if (cancelled) return;
        if (me.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!me.ok) {
          setBootError("نشست معتبر نیست");
          setReady(false);
          return;
        }
        const [svcRes, resRes] = await Promise.all([
          apiFetch("/api/catalog/services"),
          apiFetch("/api/catalog/resources"),
        ]);
        if (cancelled) return;
        if (svcRes.status === 401 || resRes.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!svcRes.ok || !resRes.ok) {
          setBootError("بارگذاری فهرست خدمات/منابع ناموفق بود");
          return;
        }
        const svcData = await svcRes.json();
        const resData = await resRes.json();
        if (cancelled) return;
        setServices(svcData.items || []);
        setResources(resData.items || []);
        setReady(true);
      } catch {
        if (!cancelled) {
          setBootError("ارتباط برای آماده‌سازی میز پذیرش برقرار نشد");
          setReady(false);
        }
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (!serviceId) return;
    if (requirementsState.status !== "loading") return;
    if (requirementsState.serviceId !== serviceId) return;

    const token = reqToken.current;
    const requestedServiceId = serviceId;

    async function loadRequirements() {
      try {
        const response = await apiFetch(
          `/api/catalog/resources?service_id=${encodeURIComponent(requestedServiceId)}`,
        );
        if (token !== reqToken.current) return;
        if (response.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
          if (token !== reqToken.current) return;
          setRequirementsState({
            status: "error",
            serviceId: requestedServiceId,
            message: formatApiError(data, "خواندن الزامات منابع ناموفق بود"),
          });
          return;
        }
        const data = await response.json();
        if (token !== reqToken.current) return;
        setRequirementsState({
          status: "ready",
          serviceId: requestedServiceId,
          items: data.items || [],
        });
      } catch {
        if (token !== reqToken.current) return;
        setRequirementsState({
          status: "error",
          serviceId: requestedServiceId,
          message: "ارتباط برای خواندن الزامات منابع برقرار نشد",
        });
      }
    }
    void loadRequirements();
  }, [serviceId, requirementsState, router]);

  function toggleResource(id: string) {
    setPendingConflicts(null);
    setSelectedResourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  function selectPatient(patient: Patient) {
    setSelectedPatient(patient);
    invalidateBookingState();
  }

  async function searchPatients() {
    setError(null);
    try {
      const response = await apiFetch(
        `/api/patients?q=${encodeURIComponent(query.trim())}`,
      );
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
        items?: Patient[];
      };
      if (!response.ok) {
        setError(formatApiError(data, "جستجوی بیمار ناموفق بود"));
        return;
      }
      setPatients(data.items || []);
    } catch {
      setError("ارتباط برای جستجوی بیمار برقرار نشد");
    }
  }

  async function registerPatient(event: FormEvent) {
    event.preventDefault();
    if (registering) return;
    setError(null);
    setMessage(null);
    setRegistering(true);
    try {
      const response = await apiFetch("/api/patients", {
        method: "POST",
        csrf: true,
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          birth_date: birthDate || null,
        }),
      });
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & Patient;
      if (!response.ok) {
        setError(formatApiError(data, "ثبت بیمار ناموفق بود"));
        return;
      }
      setSelectedPatient(data);
      invalidateBookingState();
      setMessage(`بیمار ثبت شد — شناسه پروفایل: ${data.patient_profile_id}`);
      setFirstName("");
      setLastName("");
      setBirthDate("");
    } catch {
      setError(
        "ارتباط برای ثبت بیمار برقرار نشد — نتیجه نامشخص است؛ از تکرار کور خودداری کنید",
      );
    } finally {
      setRegistering(false);
    }
  }

  async function postAppointment(intent: BookingIntent, idempotencyKey: string) {
    if (!selectedPatient) return null;
    const startIso = tehranLocalToUtcIso(intent.startLocal);
    const endDate = new Date(
      new Date(startIso).getTime() + intent.durationMinutes * 60_000,
    );
    const response = await apiFetch("/api/appointments", {
      method: "POST",
      csrf: true,
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        beneficiary_patient_id: intent.patientId,
        service_id: intent.serviceId,
        resource_ids: intent.resourceIds,
        start_at_utc: startIso,
        end_at_utc: endDate.toISOString(),
        booking_channel: "MANUAL_STAFF",
        capacity_pool: "MANUAL",
        acknowledge_overlap: intent.acknowledgeOverlap,
        acknowledged_conflict_ids: intent.acknowledgedConflictIds,
      }),
    });
    return { response, startIso };
  }

  const canSubmit =
    ready
    && !!selectedPatient
    && requirementsReady
    && selectionCheck.ok
    && !!localStart
    && !submitting
    && !pendingConflicts;

  async function submitAppointment(event: FormEvent) {
    event.preventDefault();
    if (submitting || !canSubmit) return;
    setError(null);
    setMessage(null);
    const intent = baseIntent({ acknowledgeOverlap: false, acknowledgedConflictIds: [] });
    if (!intent) {
      setError("بیمار، خدمت و زمان الزامی است");
      return;
    }
    if (!requirementsReady) {
      setError("الزامات منابع هنوز آماده نیست");
      return;
    }
    const resourceGate = validateResourceSelection(
      requirements,
      selectedResourceIds,
      resourcesById,
    );
    if (!resourceGate.ok) {
      setError(resourceGate.message);
      return;
    }
    setSubmitting(true);
    try {
      const key = keyStore.current.keyFor(intent);
      const result = await postAppointment(intent, key);
      if (!result) return;
      const { response, startIso } = result;
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
        appointment_id?: string;
        replayed?: boolean;
      };
      const conflicts = extractOverlapConflicts(data);
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
      setMessage(
        `نوبت ثبت شد — شناسه: ${data.appointment_id}${data.replayed ? " (بازیابی تکرار)" : ""} — ${formatTehran(startIso)}`,
      );
    } catch {
      setError(
        "ارتباط برای ثبت نوبت برقرار نشد — نتیجه نامشخص است؛ همان درخواست را با همان کلید می‌توانید تکرار کنید",
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
      const conflictIds = sortedConflictIds(pendingConflicts);
      const intent = baseIntent({
        acknowledgeOverlap: true,
        acknowledgedConflictIds: conflictIds,
      });
      if (!intent) {
        setError("درخواست تأیید ناقص است");
        return;
      }
      const confirmKey = keyStore.current.keyFor(intent);
      const result = await postAppointment(intent, confirmKey);
      if (!result) return;
      const { response, startIso } = result;
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
        appointment_id?: string;
        replayed?: boolean;
      };
      const refreshed = extractOverlapConflicts(data);
      if (refreshed) {
        setPendingConflicts(refreshed);
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
        `نوبت با تأیید تداخل ثبت شد — شناسه: ${data.appointment_id}${data.replayed ? " (بازیابی تکرار)" : ""} — ${formatTehran(startIso)}`,
      );
    } catch {
      setError(
        "ارتباط برای تأیید تداخل برقرار نشد — نتیجه نامشخص است؛ همان تأیید را می‌توانید تکرار کنید",
      );
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
    ready,
    bootError,
    query,
    setQuery,
    patients,
    selectedPatient,
    selectPatient,
    services,
    serviceId,
    changeService,
    requirementsState,
    requirementsReady,
    eligibleResources,
    selectedResourceIds,
    toggleResource,
    selectionCheck,
    neededCount,
    localStart,
    setLocalStart: (value: string) => {
      setLocalStart(value);
      invalidateBookingState();
    },
    firstName,
    setFirstName,
    lastName,
    setLastName,
    birthDate,
    setBirthDate,
    message,
    error,
    submitting,
    registering,
    pendingConflicts,
    durationMinutes,
    canSubmit,
    searchPatients,
    registerPatient,
    submitAppointment,
    confirmOverlap,
    dismissOverlap,
  };
}

export type ReceptionDeskModel = ReturnType<typeof useReceptionDesk>;
