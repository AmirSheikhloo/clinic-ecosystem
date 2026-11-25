"use client";

import type { FormEvent } from "react";
import { TextField } from "@/components/forms/TextField";
import type { Patient } from "./types";

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  patients: Patient[];
  selectedPatient: Patient | null;
  onSelectPatient: (patient: Patient) => void;
  firstName: string;
  lastName: string;
  birthDate: string;
  onFirstNameChange: (value: string) => void;
  onLastNameChange: (value: string) => void;
  onBirthDateChange: (value: string) => void;
  registering: boolean;
  onRegister: (event: FormEvent) => void;
};

export function PatientSearchPanel({
  query,
  onQueryChange,
  onSearch,
  patients,
  selectedPatient,
  onSelectPatient,
  firstName,
  lastName,
  birthDate,
  onFirstNameChange,
  onLastNameChange,
  onBirthDateChange,
  registering,
  onRegister,
}: Props) {
  return (
    <div className="ds-card space-y-4 p-5">
      <h2 className="font-semibold">جستجوی بیمار</h2>
      <div className="flex gap-2">
        <input
          data-testid="patient-search-query"
          className="ds-input flex-1"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="نام یا نام خانوادگی"
        />
        <button
          type="button"
          data-testid="patient-search-submit"
          onClick={onSearch}
          className="ds-btn ds-btn-primary"
        >
          جستجو
        </button>
      </div>
      <ul className="max-h-48 space-y-2 overflow-auto">
        {patients.map((patient) => (
          <li key={patient.patient_profile_id}>
            <button
              type="button"
              onClick={() => onSelectPatient(patient)}
              className={`w-full rounded-[var(--ds-radius-md)] border px-3 py-2 text-right ${
                selectedPatient?.patient_profile_id === patient.patient_profile_id
                  ? "border-[var(--ds-primary)] bg-[var(--ds-surface-muted)]"
                  : "border-[var(--ds-border)] hover:bg-[var(--ds-surface-muted)]"
              }`}
            >
              {patient.first_name} {patient.last_name}
              <span className="mt-1 block text-xs text-[var(--ds-text-muted)]">
                پروفایل: {patient.patient_profile_id}
              </span>
            </button>
          </li>
        ))}
        {!patients.length && (
          <li className="text-sm text-[var(--ds-text-muted)]">نتیجه‌ای نیست</li>
        )}
      </ul>

      <form
        onSubmit={onRegister}
        className="space-y-3 border-t border-[var(--ds-border)] pt-4"
      >
        <h3 className="font-medium">ثبت بیمار مصنوعی</h3>
        <div className="grid grid-cols-2 gap-2">
          <input
            data-testid="patient-first-name"
            className="ds-input"
            placeholder="نام"
            value={firstName}
            onChange={(e) => onFirstNameChange(e.target.value)}
            required
          />
          <input
            data-testid="patient-last-name"
            className="ds-input"
            placeholder="نام خانوادگی"
            value={lastName}
            onChange={(e) => onLastNameChange(e.target.value)}
            required
          />
        </div>
        <TextField
          type="date"
          data-testid="patient-birth-date"
          label="تاریخ تولد"
          value={birthDate}
          onChange={(e) => onBirthDateChange(e.target.value)}
        />
        <button
          type="submit"
          data-testid="patient-register-submit"
          disabled={registering}
          className="ds-btn ds-btn-ghost"
        >
          {registering ? "در حال ثبت…" : "ثبت بیمار"}
        </button>
      </form>
    </div>
  );
}
