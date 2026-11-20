"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch,
  formatApiError,
  formatTehran,
  tehranLocalToUtcIso,
  type ApiErrorBody,
} from "@/lib/client";

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

type Resource = {
  id: string;
  resource_type: string;
  resource_name: string;
  is_active: boolean;
};

type Requirement = {
  id: string;
  requirement_group: string;
  required_resource_type: string;
  specific_resource_id: string | null;
  quantity_required: number;
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
  const [resourceId, setResourceId] = useState("");
  const [localStart, setLocalStart] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());

  const durationMinutes = useMemo(() => {
    const svc = services.find((s) => s.id === serviceId);
    return svc?.default_duration_minutes || 30;
  }, [services, serviceId]);

  const eligibleResources = useMemo(() => {
    if (!requirements.length) return resources;
    return resources.filter((resource) =>
      requirements.some((req) => {
        if (req.specific_resource_id) {
          return req.specific_resource_id === resource.id;
        }
        return req.required_resource_type === resource.resource_type;
      }),
    );
  }, [resources, requirements]);

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
        setResourceId("");
        return;
      }
      const response = await apiFetch(
        `/api/catalog/resources?service_id=${encodeURIComponent(serviceId)}`,
      );
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      if (!response.ok) {
        setError("خواندن الزامات منابع ناموفق بود");
        return;
      }
      const data = await response.json();
      setRequirements(data.items || []);
      setResourceId("");
    }
    void loadRequirements();
  }, [serviceId, router]);

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
    setError(null);
    setMessage(null);
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
    if (!serviceId || !resourceId || !localStart) {
      setError("خدمت، منبع و زمان الزامی است");
      return;
    }
    setSubmitting(true);
    try {
      const startIso = tehranLocalToUtcIso(localStart);
      const endDate = new Date(
        new Date(startIso).getTime() + durationMinutes * 60_000,
      );
      const response = await apiFetch("/api/appointments", {
        method: "POST",
        csrf: true,
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          beneficiary_patient_id: selectedPatient.patient_profile_id,
          service_id: serviceId,
          resource_ids: [resourceId],
          start_at_utc: startIso,
          end_at_utc: endDate.toISOString(),
          booking_channel: "MANUAL_STAFF",
          capacity_pool: "MANUAL",
        }),
      });
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
        appointment_id?: string;
        replayed?: boolean;
        detail?: { error?: string; conflicts?: Array<{ appointment_id: string }> };
      };
      if (!response.ok) {
        const detailError =
          data.detail && typeof data.detail === "object"
            ? (data.detail as { error?: string }).error
            : undefined;
        if (
          response.status === 409
          && (detailError === "manual_overlap_acknowledgement_required"
            || data.error === "manual_overlap_acknowledgement_required")
        ) {
          setError(
            "تداخل نوبت دستی — برای ادامه، تایید صریح تداخل از API با شناسه‌های تعارض لازم است.",
          );
          return;
        }
        setError(formatApiError(data, "ثبت نوبت ناموفق بود"));
        return;
      }
      setMessage(
        `نوبت ثبت شد — شناسه: ${data.appointment_id}${data.replayed ? " (بازیابی تکرار)" : ""} — ${formatTehran(startIso)}`,
      );
      setIdempotencyKey(crypto.randomUUID());
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
          جستجو/ثبت بیمار مصنوعی، انتخاب خدمت و منبع معتبر، ثبت نوبت دستی
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
              className="rounded-lg border border-[var(--color-sea)] px-4 py-2 text-[var(--color-sea-deep)]"
            >
              ثبت بیمار
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
          <label className="block space-y-1">
            <span className="text-sm">منبع معتبر</span>
            <select
              className="w-full rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={resourceId}
              onChange={(e) => setResourceId(e.target.value)}
              required
            >
              <option value="">انتخاب کنید</option>
              {eligibleResources.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.resource_name} ({resource.resource_type})
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm">زمان شروع (Asia/Tehran)</span>
            <input
              type="datetime-local"
              className="w-full rounded-lg border border-[#c9d5e1] px-3 py-2"
              value={localStart}
              onChange={(e) => {
                setLocalStart(e.target.value);
                setIdempotencyKey(crypto.randomUUID());
              }}
              required
            />
          </label>
          <p className="text-xs text-[var(--color-ink)]/55">
            مدت خدمت: {durationMinutes} دقیقه — کلید ایدمپوتنسی ثابت تا تغییر فرم
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[var(--color-sea)] px-4 py-2.5 font-medium text-white disabled:opacity-60"
          >
            {submitting ? "در حال ثبت…" : "ثبت نوبت"}
          </button>
        </form>
      </section>

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
