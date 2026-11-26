"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { apiJson, buildQuery } from "@/lib/api";
import { useSession } from "@/components/session/SessionProvider";
import type { DeskFeedback } from "./useDeskFeedback";
import type { Patient } from "./types";

const SEARCH_DEBOUNCE_MS = 300;
export const PATIENT_SEARCH_MIN = 2;

type SearchState = { q: string; items: Patient[] } | null;

/** Patient search (debounced, cancellable), quick registration and `?patient=<id>` deep-link selection. */
export function useDeskPatients(feedback: DeskFeedback, onSelectionChange: () => void) {
  const router = useRouter();
  const { status } = useSession();
  const requestedPatientId = useSearchParams().get("patient");
  const { setError, setMessage } = feedback;
  const [query, setQuery] = useState("");
  const [searchState, setSearchState] = useState<SearchState>(null);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [identityExceptionReason, setIdentityExceptionReason] = useState("");
  const [registering, setRegistering] = useState(false);

  const term = query.trim();
  const searchable = term.length >= PATIENT_SEARCH_MIN;
  const patients = searchState?.q === term ? searchState.items : [];
  const searching = status === "ready" && searchable && searchState?.q !== term;

  useEffect(() => {
    if (status !== "ready" || term.length < PATIENT_SEARCH_MIN) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void apiJson<{ items?: Patient[] }>(`/api/patients${buildQuery({ q: term, limit: 20 })}`, {
        signal: controller.signal,
        fallbackMessage: "جستجوی بیمار ناموفق بود",
      }).then((result) => {
        if (!result.ok) {
          if (result.aborted) return;
          setError(result.message);
          setSearchState({ q: term, items: [] });
          return;
        }
        setSearchState({ q: term, items: result.data.items ?? [] });
      });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [term, status, setError]);

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

  function clearSelection() {
    setSelectedPatient(null);
    setQuery("");
    setSearchState(null);
    onSelectionChange();
  }

  /** Immediate search for the Search button / Enter; short terms are explained, not sent. */
  async function searchPatients() {
    setError(null);
    if (!searchable) {
      setError(`برای جستجو حداقل ${PATIENT_SEARCH_MIN} حرف وارد کنید`);
      return;
    }
    const result = await apiJson<{ items?: Patient[] }>(`/api/patients${buildQuery({ q: term, limit: 20 })}`, {
      fallbackMessage: "جستجوی بیمار ناموفق بود",
    });
    if (!result.ok) {
      if (result.status !== 401) setError(result.message);
      return;
    }
    setSearchState({ q: term, items: result.data.items ?? [] });
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
          national_id: nationalId.trim() || null,
          identity_exception_reason: nationalId.trim() ? null : (identityExceptionReason.trim() || null),
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
      setMessage(`بیمار ثبت شد: ${data.first_name} ${data.last_name}`);
      setFirstName("");
      setLastName("");
      setBirthDate("");
      setNationalId("");
      setIdentityExceptionReason("");
    } catch {
      setError("ارتباط برای ثبت بیمار برقرار نشد — نتیجه نامشخص است؛ پیش از ثبت دوباره، جستجو کنید");
    } finally {
      setRegistering(false);
    }
  }

  return {
    query,
    setQuery,
    patients,
    searching,
    searched: searchState?.q === term && searchable,
    selectedPatient,
    selectPatient,
    clearSelection,
    firstName,
    setFirstName,
    lastName,
    setLastName,
    birthDate,
    setBirthDate,
    nationalId,
    setNationalId,
    identityExceptionReason,
    setIdentityExceptionReason,
    registering,
    searchPatients,
    registerPatient,
  };
}
