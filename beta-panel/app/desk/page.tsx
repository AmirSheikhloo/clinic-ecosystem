"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch,
  bookingFingerprint,
  extractOverlapConflicts,
  formatApiError,
  formatTehran,
  tehranLocalToUtcIso,
  type ApiErrorBody,
  type OverlapConflict,
} from "@/lib/client";
import {
  eligibleResourcesForRequirements,
  requiredSelectionCount,
  validateResourceSelection,
  type Requirement,
  type Resource,
} from "@/lib/resources";

type Patient = {
  patient_profile_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  birth_date: string | null;
};

type Service = {
  id: string;
  service_name: string;
  default_duration_minutes: number;
  is_active: boolean;
};

export default function DeskPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
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
  const reqSeq = useRef(0);
  const keyCache = useRef(new Map<string, string>());

  const durationMinutes = useMemo(() => {
    const svc = services.find((s) => s.id === serviceId);
    return svc?.default_duration_minutes || 30;
  }, [services, serviceId]);

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

  function idempotencyForPayload(resourceIds: string[]): string {
    if (!selectedPatient || !serviceId || !localStart) {
      return crypto.randomUUID();
    }
    const fp = bookingFingerprint({
      patientId: selectedPatient.patient_profile_id,
      serviceId,
      resourceIds,
      startLocal: localStart,
      durationMinutes,
    });
    const existing = keyCache.current.get(fp);
    if (existing) return existing;
    const created = crypto.randomUUID();
    keyCache.current.set(fp, created);
    return created;
  }

  useEffect(() => {
    async function boot() {
      const me = await apiFetch("/api/auth/me");
      if (me.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (!me.ok) {
        setError("نشست معتبر نیست");
        return;
      }
      const [svcRes, resRes] = await Promise.all([
        apiFetch("/api/catalog/services"),
        apiFetch("/api/catalog/resources"),
      ]);
      if (svcRes.status === 401 || resRes.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (!svcRes.ok || !resRes.ok) {
        setError("بارگذاری فهرست خدمات/منابع ناموفق بود");
        return;
      }
      const svcData = await svcRes.json();
      const resData = await resRes.json();
      setServices(svcData.items || []);
      setResources(resData.items || []);
      setReady(true);
    }
    void boot();
  }, [router]);

  useEffect(() => {
    async function loadRequirements() {
      if (!serviceId) {
        setRequirements([]);
        setSelectedResourceIds([]);
        setPendingConflicts(null);
        return;
      }
      const seq = ++reqSeq.current;
      const response = await apiFetch(
        `/api/catalog/resources?service_id=${encodeURIComponent(serviceId)}`,
      );
      if (seq !== reqSeq.current) return;
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (!response.ok) {
        setError("خواندن الزامات منابع ناموفق بود");
        return;
      }
      const data = await response.json();
      if (seq !== reqSeq.current) return;
      setRequirements(data.items || []);
      setSelectedResourceIds([]);
      setPendingConflicts(null);
    }
    void loadRequirements();
  }, [serviceId, router]);

  function toggleResource(id: string) {
    setPendingConflicts(null);
    setSelectedResourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  async function searchPatients() {
    setError(null);
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
      setMessage(`بیمار ثبت شد — شناسه پروفایل: ${data.patient_profile_id}`);
      setFirstName("");
      setLastName("");
      setBirthDate("");
    } catch {
      setError("ارتباط برای ثبت بیمار برقرار نشد");
    } finally {
      setRegistering(false);
    }
  }

  async function postAppointment(options: {
    acknowledge: boolean;
    conflictIds: string[];
    idempotencyKey: string;
  }) {
    if (!selectedPatient) return;
    const startIso = tehranLocalToUtcIso(localStart);
    const endDate = new Date(
      new Date(startIso).getTime() + durationMinutes * 60_000,
    );
    const response = await apiFetch("/api/appointments", {
      method: "POST",
      csrf: true,
      headers: { "Idempotency-Key": options.idempotencyKey },
      body: JSON.stringify({
        beneficiary_patient_id: selectedPatient.patient_profile_id,
        service_id: serviceId,
        resource_ids: selectedResourceIds,
        start_at_utc: startIso,
        end_at_utc: endDate.toISOString(),
        booking_channel: "MANUAL_STAFF",
        capacity_pool: "MANUAL",
        acknowledge_overlap: options.acknowledge,
        acknowledged_conflict_ids: options.conflictIds,
      }),
    });
    return { response, startIso };
  }

  async function submitAppointment(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    setMessage(null);
    if (!selectedPatient) {
      setError("ابتدا بیمار را انتخاب کنید");
      return;
    }
    if (!serviceId || !localStart) {
      setError("خدمت و زمان الزامی است");
      return;
    }
    if (!selectionCheck.ok) {
      setError(selectionCheck.message);
      return;
    }
    setSubmitting(true);
    try {
      const key = idempotencyForPayload(selectedResourceIds);
      const result = await postAppointment({
        acknowledge: false,
        conflictIds: [],
        idempotencyKey: key,
      });
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
      // New booking after success uses a fresh key for a changed payload.
      keyCache.current.clear();
    } catch {
      setError("ارتباط برای ثبت نوبت برقرار نشد — نتیجه نامشخص است؛ از تکرار کور خودداری کنید");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmOverlap() {
    if (!pendingConflicts || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      // Confirmed overlap is a different fingerprint → distinct idempotency key.
      const confirmKey = crypto.randomUUID();
      const conflictIds = pendingConflicts.map((item) => item.appointment_id);
      const result = await postAppointment({
        acknowledge: true,
        conflictIds,
        idempotencyKey: confirmKey,
      });
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
        `نوبت با تأیید تداخل ثبت شد — شناسه: ${data.appointment_id} — ${formatTehran(startIso)}`,
      );
      keyCache.current.clear();
    } catch {
      setError("ارتباط برای تأیید تداخل برقرار نشد");
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready) {
    return <p className="animate-fade-in text-[var(--color-ink)]/70">در حال آماده‌سازی میز پذیرش…</p>;
  }

  return (
    <main className="space-y-8 animate-rise">
      <header>
        <h1 className="text-2xl font-bold text-[var(--color-sea-deep)]">میز پذیرش</h1>
        <p className="text-[var(--color-ink)]/70">
          جستجو/ثبت بیمار مصنوعی، انتخاب خدمت و منابع معتبر، ثبت نوبت دستی
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-2xl border border-[#d7e0ea] bg-white/90 p-5">
          <h2 className="font-semibold">جستجوی بیمار</h2>
          <div className="flex gap-2">
            <input
              className="flex-1 rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="نام یا نام خانوادگی"
            />
            <button
              type="button"
              onClick={searchPatients}
              className="rounded-lg bg-[var(--color-sea)] px-4 py-2 text-white"
            >
              جستجو
            </button>
          </div>
          <ul className="max-h-48 space-y-2 overflow-auto">
            {patients.map((patient) => (
              <li key={patient.patient_profile_id}>
                <button
                  type="button"
                  onClick={() => setSelectedPatient(patient)}
                  className={`w-full rounded-lg border px-3 py-2 text-right ${
                    selectedPatient?.patient_profile_id === patient.patient_profile_id
                      ? "border-[var(--color-sea)] bg-[var(--color-mist)]"
                      : "border-[#d7e0ea] hover:bg-[var(--color-sand)]"
                  }`}
                >
                  {patient.first_name} {patient.last_name}
                  <span className="mt-1 block text-xs text-[var(--color-ink)]/55">
                    پروفایل: {patient.patient_profile_id}
                  </span>
                </button>
              </li>
            ))}
            {!patients.length && (
              <li className="text-sm text-[var(--color-ink)]/55">نتیجه‌ای نیست</li>
            )}
          </ul>

          <form onSubmit={registerPatient} className="space-y-3 border-t border-[#e4ebf2] pt-4">
            <h3 className="font-medium">ثبت بیمار مصنوعی</h3>
            <div className="grid grid-cols-2 gap-2">
              <input
                className="rounded-lg border border-[#c9d5e1] px-3 py-2"
                placeholder="نام"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
              <input
                className="rounded-lg border border-[#c9d5e1] px-3 py-2"
                placeholder="نام خانوادگی"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
            <input
              type="date"
              className="w-full rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
            />
            <button
              type="submit"
              disabled={registering}
              className="rounded-lg border border-[var(--color-sea)] px-4 py-2 text-[var(--color-sea-deep)] disabled:opacity-60"
            >
              {registering ? "در حال ثبت…" : "ثبت بیمار"}
            </button>
          </form>
        </div>

        <form
          onSubmit={submitAppointment}
          className="space-y-4 rounded-2xl border border-[#d7e0ea] bg-white/90 p-5"
        >
          <h2 className="font-semibold">ثبت نوبت دستی</h2>
          <p className="rounded-md bg-[var(--color-mist)] px-3 py-2 text-sm">
            بیمار انتخاب‌شده:{" "}
            {selectedPatient
              ? `${selectedPatient.first_name} ${selectedPatient.last_name}`
              : "انتخاب نشده"}
          </p>
          <label className="block space-y-1">
            <span className="text-sm">خدمت</span>
            <select
              className="w-full rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={serviceId}
              onChange={(e) => setServiceId(e.target.value)}
              required
            >
              <option value="">انتخاب کنید</option>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.service_name}
                </option>
              ))}
            </select>
          </label>

          <fieldset className="space-y-2">
            <legend className="text-sm">
              منابع معتبر ({selectedResourceIds.length}/{neededCount})
            </legend>
            {!eligibleResources.length && serviceId && (
              <p className="text-sm text-[var(--color-alert)]">
                منبع معتبری برای الزامات این خدمت در دسترس نیست
              </p>
            )}
            <ul className="max-h-40 space-y-2 overflow-auto">
              {eligibleResources.map((resource) => {
                const checked = selectedResourceIds.includes(resource.id);
                return (
                  <li key={resource.id}>
                    <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-[#d7e0ea] px-3 py-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleResource(resource.id)}
                      />
                      <span>
                        {resource.resource_name}
                        <span className="mr-2 text-xs text-[var(--color-ink)]/55">
                          ({resource.resource_type})
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
            {!selectionCheck.ok && selectedResourceIds.length > 0 && (
              <p className="text-xs text-[var(--color-alert)]">{selectionCheck.message}</p>
            )}
            {requirements.length > 0 && (
              <ul className="text-xs text-[var(--color-ink)]/60">
                {requirements.map((req) => (
                  <li key={req.id}>
                    گروه {req.requirement_group}: {req.quantity_required}× {req.required_resource_type}
                    {req.specific_resource_id ? " (منبع مشخص)" : ""}
                  </li>
                ))}
              </ul>
            )}
          </fieldset>

          <label className="block space-y-1">
            <span className="text-sm">زمان شروع (Asia/Tehran)</span>
            <input
              type="datetime-local"
              className="w-full rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={localStart}
              onChange={(e) => {
                setLocalStart(e.target.value);
                setPendingConflicts(null);
              }}
              required
            />
          </label>
          <p className="text-xs text-[var(--color-ink)]/55">
            مدت خدمت: {durationMinutes} دقیقه — کلید ایدمپوتنسی برای همان درخواست پایدار می‌ماند
          </p>
          <button
            type="submit"
            disabled={submitting || !selectionCheck.ok || !!pendingConflicts}
            className="w-full rounded-lg bg-[var(--color-sea)] px-4 py-2.5 font-medium text-white disabled:opacity-60"
          >
            {submitting ? "در حال ثبت…" : "ثبت نوبت"}
          </button>
        </form>
      </section>

      {pendingConflicts && (
        <section className="space-y-3 rounded-2xl border border-amber-300 bg-amber-50 p-5" role="dialog" aria-labelledby="overlap-title">
          <h2 id="overlap-title" className="font-semibold text-amber-900">
            تأیید صریح تداخل نوبت دستی
          </h2>
          <p className="text-sm text-amber-900/90">
            این نوبت با نوبت‌های موجود هم‌پوشانی دارد. فقط داده‌های مجاز سرور نمایش داده می‌شود.
            ادامه فقط با تأیید آگاهانه و مجوز ALLOW_MANUAL_OVERBOOKING ممکن است.
          </p>
          <ul className="space-y-2 text-sm">
            {pendingConflicts.map((conflict) => (
              <li key={conflict.appointment_id} className="rounded-lg bg-white/80 px-3 py-2">
                <div>شناسه نوبت: {conflict.appointment_id}</div>
                {conflict.display_safe_patient_name !== undefined && (
                  <div>بیمار: {conflict.display_safe_patient_name || "—"}</div>
                )}
                {conflict.scheduled_start_at_utc && (
                  <div>زمان: {formatTehran(conflict.scheduled_start_at_utc)}</div>
                )}
                {conflict.booking_channel && <div>کانال: {conflict.booking_channel}</div>}
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={confirmOverlap}
              className="rounded-lg bg-amber-700 px-4 py-2 text-white disabled:opacity-60"
            >
              تأیید تداخل و ثبت نوبت
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => setPendingConflicts(null)}
              className="rounded-lg border border-amber-700 px-4 py-2 text-amber-900"
            >
              انصراف
            </button>
          </div>
        </section>
      )}

      {message && (
        <p className="rounded-lg bg-emerald-50 px-4 py-3 text-[var(--color-ok)]" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-[var(--color-alert)]" role="alert">
          {error}
        </p>
      )}
    </main>
  );
}
