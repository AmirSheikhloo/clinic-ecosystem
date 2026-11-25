"use client";

import type { FormEvent } from "react";
import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import type { Resource } from "@/lib/resources";
import type { Patient, RequirementsState, Service } from "./types";

type SelectionCheck = { ok: boolean; message?: string };

type Props = {
  selectedPatient: Patient | null;
  services: Service[];
  serviceId: string;
  onServiceChange: (serviceId: string) => void;
  requirementsState: RequirementsState;
  requirementsReady: boolean;
  eligibleResources: Resource[];
  selectedResourceIds: string[];
  onToggleResource: (id: string) => void;
  selectionCheck: SelectionCheck;
  neededCount: number;
  localStart: string;
  onLocalStartChange: (value: string) => void;
  durationMinutes: number;
  pendingConflicts: unknown;
  canSubmit: boolean;
  submitting: boolean;
  onSubmit: (event: FormEvent) => void;
};

export function BookingForm({
  selectedPatient,
  services,
  serviceId,
  onServiceChange,
  requirementsState,
  requirementsReady,
  eligibleResources,
  selectedResourceIds,
  onToggleResource,
  selectionCheck,
  neededCount,
  localStart,
  onLocalStartChange,
  durationMinutes,
  pendingConflicts,
  canSubmit,
  submitting,
  onSubmit,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="ds-card space-y-4 p-5">
      <h2 className="font-semibold">ثبت نوبت دستی</h2>
      <p
        className="rounded-[var(--ds-radius-md)] bg-[var(--ds-surface-muted)] px-3 py-2 text-sm"
        data-testid="selected-patient"
      >
        بیمار انتخاب‌شده:{" "}
        {selectedPatient
          ? `${selectedPatient.first_name} ${selectedPatient.last_name}`
          : "انتخاب نشده"}
      </p>
      <SelectField
        label="خدمت"
        data-testid="service-select"
        value={serviceId}
        onChange={(e) => onServiceChange(e.target.value)}
        required
      >
        <option value="">انتخاب کنید</option>
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.service_name}
          </option>
        ))}
      </SelectField>

      <fieldset
        className="space-y-2"
        data-testid="resource-fieldset"
        disabled={!requirementsReady || !!pendingConflicts}
      >
        <legend className="text-sm">
          منابع معتبر ({selectedResourceIds.length}/{neededCount})
        </legend>
        {requirementsState.status === "loading" && (
          <p className="text-sm text-[var(--ds-text-muted)]">در حال بارگذاری الزامات…</p>
        )}
        {requirementsState.status === "error" && requirementsState.serviceId === serviceId && (
          <p className="text-sm text-[var(--ds-danger)]">{requirementsState.message}</p>
        )}
        {requirementsReady && !eligibleResources.length && (
          <p className="text-sm text-[var(--ds-danger)]">
            منبع معتبری برای الزامات این خدمت در دسترس نیست
          </p>
        )}
        <ul className="max-h-40 space-y-2 overflow-auto">
          {eligibleResources.map((resource) => {
            const checked = selectedResourceIds.includes(resource.id);
            return (
              <li key={resource.id}>
                <label
                  data-testid="resource-option"
                  className="flex cursor-pointer items-center gap-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggleResource(resource.id)}
                  />
                  <span>
                    {resource.resource_name}
                    <span className="mr-2 text-xs text-[var(--ds-text-muted)]">
                      ({resource.resource_type})
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        {!selectionCheck.ok && selectedResourceIds.length > 0 && requirementsReady && (
          <p className="text-xs text-[var(--ds-danger)]">{selectionCheck.message}</p>
        )}
      </fieldset>

      <TextField
        type="datetime-local"
        data-testid="appointment-start"
        label="زمان شروع (Asia/Tehran)"
        value={localStart}
        onChange={(e) => onLocalStartChange(e.target.value)}
        required
        disabled={!!pendingConflicts}
      />
      <p className="text-xs text-[var(--ds-text-muted)] tabular-nums">
        مدت خدمت: {durationMinutes} دقیقه — کلید ایدمپوتنسی برای همان اثر انگشت پایدار است
      </p>
      <button
        type="submit"
        data-testid="appointment-submit"
        disabled={!canSubmit}
        className="ds-btn ds-btn-primary w-full"
      >
        {submitting && !pendingConflicts ? "در حال ثبت…" : "ثبت نوبت"}
      </button>
    </form>
  );
}
