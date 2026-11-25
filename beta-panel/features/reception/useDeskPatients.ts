"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { useSession } from "@/components/session/SessionProvider";
import type { DeskFeedback } from "./useDeskFeedback";
import type { Patient } from "./types";

/** Patient search, quick registration and `?patient=<id>` deep-link selection. */
export function useDeskPatients(feedback: DeskFeedback, onSelectionChange: () => void) {
  const router = useRouter();
  const { status } = useSession();
  const requestedPatientId = useSearchParams().get("patient");
  const { setError, setMessage } = feedback;
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    if (status !== "ready" || !requestedPatientId) return;
    let cancelled = false;
    async function loadRequested() {
      try {
        const response = await apiFetch(`/api/v1/patients/${encodeURIComponent(requestedPatientId as string)}`);
        if (cancelled) return;
        if (!response.ok) {
          setError("بیمار انتخاب‌شده یافت نشد یا دسترسی به آن مجاز نیست");
          return;
        }
        const data = (await response.json()) as Patient & { is_active?: boolean };
        if (cancelled) return;
        if (data.is_active === false) {
          setError("این بیمار غیرفعال است و نوبت‌دهی برای او ممکن نیست");
          return;
        }
        setSelectedPatient(data);
        onSelectionChange();
      } catch {
        if (!cancelled) setError("ارتباط برای بارگذاری بیمار برقرار نشد");
      }
    }
    void loadRequested();
    return () => {
      cancelled = true;
    };
    // onSelectionChange is intentionally excluded: the deep link must load once per id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedPatientId, status, setError]);

  function selectPatient(patient: Patient) {
    setSelectedPatient(patient);
    onSelectionChange();
  }

  async function searchPatients() {
    setError(null);
    try {
      const response = await apiFetch(`/api/patients?q=${encodeURIComponent(query.trim())}`);
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & { items?: Patient[] };
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
      onSelectionChange();
      setMessage(`بیمار ثبت شد — شناسه پروفایل: ${data.patient_profile_id}`);
      setFirstName("");
      setLastName("");
      setBirthDate("");
    } catch {
      setError("ارتباط برای ثبت بیمار برقرار نشد — نتیجه نامشخص است؛ از تکرار کور خودداری کنید");
    } finally {
      setRegistering(false);
    }
  }

  return {
    query,
    setQuery,
    patients,
    selectedPatient,
    selectPatient,
    firstName,
    setFirstName,
    lastName,
    setLastName,
    birthDate,
    setBirthDate,
    registering,
    searchPatients,
    registerPatient,
  };
}
