"use client";

import Link from "next/link";
import { useId, useState, type KeyboardEvent, type RefObject } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { PATIENT_SEARCH_MIN } from "./useDeskPatients";
import type { Patient } from "./types";

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  patients: Patient[];
  searching: boolean;
  searched: boolean;
  selectedPatient: Patient | null;
  onSelect: (patient: Patient) => void;
  onClear: () => void;
  inputRef: RefObject<HTMLInputElement | null>;
};

export function patientInitials(patient: Pick<Patient, "first_name" | "last_name">): string {
  return `${patient.first_name.charAt(0)}${patient.last_name.charAt(0)}`.trim();
}

export function birthDateLabel(birthDate: string | null): string {
  return birthDate ? formatJalaliFromTehranYmd(birthDate) : "ثبت نشده";
}

function SelectedSummary({ patient, onClear }: { patient: Patient; onClear: () => void }) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-primary)] bg-[var(--ds-primary-soft)] p-3"
      data-testid="selected-patient"
    >
      <span className="ds-avatar" aria-hidden="true">
        {patientInitials(patient)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-[var(--ds-text-muted)]">بیمار انتخاب‌شده</p>
        <p className="truncate font-semibold text-[var(--ds-heading)]">
          {patient.first_name} {patient.last_name}
        </p>
        <p className="text-xs text-[var(--ds-text-muted)] tabular-nums">تاریخ تولد: {birthDateLabel(patient.birth_date)}</p>
      </div>
      <div className="flex items-center gap-1">
        <Link
          href={`/patients/${patient.patient_profile_id}`}
          className="ds-btn ds-btn-ghost ds-btn-sm"
          data-testid="selected-patient-profile"
        >
          پرونده
        </Link>
        <Button variant="subtle" size="sm" icon="close" onClick={onClear} data-testid="selected-patient-clear">
          تغییر بیمار
        </Button>
      </div>
    </div>
  );
}

export function PatientPicker({
  query,
  onQueryChange,
  onSearch,
  patients,
  searching,
  searched,
  selectedPatient,
  onSelect,
  onClear,
  inputRef,
}: Props) {
  const listId = useId();
  const [activeIndex, setActiveIndex] = useState(0);
  const active = patients.length ? Math.min(activeIndex, patients.length - 1) : -1;
  const term = query.trim();

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && patients.length) {
      event.preventDefault();
      setActiveIndex((active + 1) % patients.length);
    } else if (event.key === "ArrowUp" && patients.length) {
      event.preventDefault();
      setActiveIndex((active - 1 + patients.length) % patients.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (active >= 0) onSelect(patients[active]);
      else onSearch();
    }
  }

  return (
    <div className="space-y-3">
      {selectedPatient ? <SelectedSummary patient={selectedPatient} onClear={onClear} /> : null}
      <div className="space-y-1.5">
        <label className="ds-field-label" htmlFor={`${listId}-input`}>
          جستجوی بیمار
        </label>
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <Icon name="search" size="sm" className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-muted)]" />
            <input
              id={`${listId}-input`}
              ref={inputRef}
              data-testid="patient-search-query"
              className="ds-input ps-9"
              role="combobox"
              aria-expanded={patients.length > 0}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
              autoComplete="off"
              placeholder="نام یا نام خانوادگی"
              value={query}
              onChange={(e) => {
                setActiveIndex(0);
                onQueryChange(e.target.value);
              }}
              onKeyDown={onKeyDown}
            />
          </div>
          <Button variant="ghost" data-testid="patient-search-submit" onClick={onSearch}>
            جستجو
          </Button>
        </div>
        <p className="ds-hint">
          با تایپ، نتایج خودکار نمایش داده می‌شود؛ با کلیدهای جهت‌نما انتخاب و با Enter تأیید کنید.
        </p>
      </div>

      <div aria-live="polite" className="sr-only">
        {searched ? `${patients.length} نتیجه` : ""}
      </div>

      {searching ? (
        <p className="text-sm text-[var(--ds-text-muted)]" data-testid="patient-search-loading">در حال جستجو…</p>
      ) : null}
      {term.length > 0 && term.length < PATIENT_SEARCH_MIN ? (
        <p className="text-sm text-[var(--ds-text-muted)]">حداقل {PATIENT_SEARCH_MIN} حرف وارد کنید.</p>
      ) : null}
      {searched && !patients.length ? (
        <p className="rounded-[var(--ds-radius-md)] bg-[var(--ds-surface-muted)] px-3 py-2 text-sm text-[var(--ds-text-muted)]" data-testid="patient-search-empty">
          بیماری با این مشخصات پیدا نشد. می‌توانید در بخش پایین بیمار جدید ثبت کنید.
        </p>
      ) : null}
      {patients.length ? (
        <ul id={listId} role="listbox" aria-label="نتایج جستجوی بیمار" className="max-h-64 space-y-1 overflow-auto" data-testid="patient-results">
          {patients.map((patient, index) => (
            <li
              key={patient.patient_profile_id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              data-testid="patient-result"
              data-active={index === active}
              className="flex cursor-pointer items-center gap-3 rounded-[var(--ds-radius-md)] border border-transparent px-3 py-2 data-[active=true]:border-[var(--ds-primary)] data-[active=true]:bg-[var(--ds-primary-soft)] hover:bg-[var(--ds-surface-muted)]"
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => onSelect(patient)}
            >
              <span className="ds-avatar" aria-hidden="true">
                {patientInitials(patient)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">
                  {patient.first_name} {patient.last_name}
                </span>
                <span className="block text-xs text-[var(--ds-text-muted)] tabular-nums">
                  تاریخ تولد: {birthDateLabel(patient.birth_date)}
                </span>
              </span>
              <span className="text-xs text-[var(--ds-primary)]">انتخاب</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
