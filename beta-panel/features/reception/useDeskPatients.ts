"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { apiJson, buildQuery } from "@/lib/api";
import { useSession } from "@/components/session/SessionProvider";
import type { IdentityType } from "@/features/patients/PatientRegisterForm";
import { isValidNationalIdChecksum, normalizeNationalIdInput } from "@/lib/national-id";
import type { DeskFeedback } from "./useDeskFeedback";
import type { Patient } from "./types";

const SEARCH_DEBOUNCE_MS = 300;
export const PATIENT_SEARCH_MIN = 2;

type SearchState = { q: string; items: Patient[] } | null;

type IdentifierLookup = {
  found: boolean;
  patient_profile_id?: string | null;
  person_id?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  masked_display?: string | null;
};

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
  const [phone, setPhone] = useState("");
  const [identityType, setIdentityType] = useState<IdentityType>("IR_NATIONAL_ID");
  const [identityExceptionReason, setIdentityExceptionReason] = useState("");
  const [registering, setRegistering] = useState(false);

  const term = query.trim();
  const nationalDigits = normalizeNationalIdInput(term);
  const lookupByNationalId = nationalDigits.length === 10 && isValidNationalIdChecksum(nationalDigits);
  const searchable = lookupByNationalId || term.length >= PATIENT_SEARCH_MIN;
  const patients = searchState?.q === term ? searchState.items : [];
  const searching = status === "ready" && searchable && searchState?.q !== term;

  useEffect(() => {
    if (status !== "ready" || !searchable) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const request = lookupByNationalId
        ? apiJson<IdentifierLookup>(
            `/api/v1/patients/lookup/identifier${buildQuery({ id_type: "IR_NATIONAL_ID", value: nationalDigits })}`,
            { signal: controller.signal, fallbackMessage: "جستجوی کد ملی ناموفق بود" },
          ).then((result) => {
            if (!result.ok) {
              if (result.aborted) return;
              setError(result.message);
              setSearchState({ q: term, items: [] });
              return;
            }
            const hit = result.data;
            const items: Patient[] =
              hit.found && hit.patient_profile_id
                ? [
                    {
                      patient_profile_id: hit.patient_profile_id,
                      person_id: hit.person_id ?? hit.patient_profile_id,
                      first_name: hit.first_name ?? "",
                      last_name: hit.last_name ?? "",
                      birth_date: null,
                      is_active: true,
                    },
                  ]
                : [];
            setSearchState({ q: term, items });
          })
        : apiJson<{ items?: Patient[] }>(`/api/patients${buildQuery({ q: term, limit: 20 })}`, {
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
      void request;
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [term, status, setError, searchable, lookupByNationalId, nationalDigits]);

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

  async function searchPatients() {
    setError(null);
    if (!searchable) {
      setError(`برای جستجو حداقل ${PATIENT_SEARCH_MIN} حرف وارد کنید`);
      return;
    }
    if (lookupByNationalId) {
      const result = await apiJson<IdentifierLookup>(
        `/api/v1/patients/lookup/identifier${buildQuery({ id_type: "IR_NATIONAL_ID", value: nationalDigits })}`,
        { fallbackMessage: "جستجوی کد ملی ناموفق بود" },
      );
      if (!result.ok) {
        if (result.status !== 401) setError(result.message);
        return;
      }
      const hit = result.data;
      const items: Patient[] =
        hit.found && hit.patient_profile_id
          ? [
              {
                patient_profile_id: hit.patient_profile_id,
                person_id: hit.person_id ?? hit.patient_profile_id,
                first_name: hit.first_name ?? "",
                last_name: hit.last_name ?? "",
                birth_date: null,
                is_active: true,
              },
            ]
          : [];
      setSearchState({ q: term, items });
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
          identity_type: identityType,
          national_id: identityType === "EXCEPTION" ? null : nationalId.trim() || null,
          phone: phone.trim() || null,
          identity_exception_reason: identityType === "EXCEPTION" ? identityExceptionReason.trim() || null : null,
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
      setPhone("");
      setIdentityType("IR_NATIONAL_ID");
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
    phone,
    setPhone,
    identityType,
    setIdentityType,
    identityExceptionReason,
    setIdentityExceptionReason,
    registering,
    searchPatients,
    registerPatient,
  };
}
