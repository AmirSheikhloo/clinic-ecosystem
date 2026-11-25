"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/feedback/EmptyState";
import { formatJalaliDate } from "@/lib/format/jalali";
import type { Patient } from "@/features/reception/types";

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  patients: Patient[];
  selected: Patient | null;
  onSelect: (patient: Patient) => void;
};

export function PatientSearchList({
  query,
  onQueryChange,
  onSearch,
  patients,
  selected,
  onSelect,
}: Props) {
  return (
    <Card className="space-y-4">
      <h3 className="font-semibold">جستجو</h3>
      <div className="flex gap-2">
        <input
          className="ds-input"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="نام یا نام خانوادگی"
          data-testid="patients-search-query"
        />
        <Button onClick={onSearch}>جستجو</Button>
      </div>
      <ul className="max-h-72 space-y-2 overflow-auto">
        {patients.map((patient) => (
          <li key={patient.patient_profile_id}>
            <button
              type="button"
              data-testid="patients-result-row"
              className={`w-full rounded-[var(--ds-radius-md)] border px-3 py-2 text-right transition-colors duration-[var(--ds-motion-micro)] ${
                selected?.patient_profile_id === patient.patient_profile_id
                  ? "border-[var(--ds-primary)] bg-[var(--ds-surface-muted)]"
                  : "border-[var(--ds-border)] hover:bg-[var(--ds-surface-muted)]"
              }`}
              onClick={() => onSelect(patient)}
            >
              <span className="font-medium">
                {patient.first_name} {patient.last_name}
              </span>
              <span className="mt-1 block text-xs text-[var(--ds-text-muted)]">
                پروفایل: {patient.patient_profile_id}
              </span>
              {patient.birth_date && (
                <span className="mt-1 block text-xs text-[var(--ds-text-muted)] tabular-nums">
                  تولد (جلالی نمایشی): {formatJalaliDate(`${patient.birth_date}T12:00:00Z`)}
                </span>
              )}
            </button>
          </li>
        ))}
        {!patients.length && (
          <EmptyState
            title="نتیجه‌ای نیست"
            description="برای فهرست کامل، API جستجو با پارامتر q الزامی است."
          />
        )}
      </ul>
    </Card>
  );
}
