"use client";

import { useEffect, useRef, type FormEvent } from "react";
import { JalaliDateTimeField } from "@/components/forms/jalali/JalaliDateTimeField";
import { SelectField } from "@/components/forms/SelectField";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehranTime } from "@/lib/format/jalali";
import { resourceTypeLabel, type Requirement, type Resource } from "@/lib/resources";
import { tehranLocalToUtcIso } from "@/lib/tehran";
import { BookingSummary } from "./BookingSummary";
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
  onAddToInvoice?: () => void;
  canAddToInvoice?: boolean;
  onSetWalkInNow?: () => void;
  queuedCount?: number;
  onSubmitGroup?: () => void;
  canSubmitGroup?: boolean;
};

function describeRequirements(items: Requirement[], resources: Resource[]): string[] {
  const names = new Map(resources.map((resource) => [resource.id, resource.resource_name]));
  return items.map((item) => {
    const specific = item.specific_resource_id ? names.get(item.specific_resource_id) : null;
    const base = `${item.quantity_required} × ${resourceTypeLabel(item.required_resource_type)}`;
    return specific ? `${base} (${specific})` : base;
  });
}

function endTimeLabel(localStart: string, minutes: number): string | null {
  if (!localStart) return null;
  try {
    const end = new Date(new Date(tehranLocalToUtcIso(localStart)).getTime() + minutes * 60_000);
    return formatTehranTime(end.toISOString());
  } catch {
    return null;
  }
}

function missingSteps(props: Props): string[] {
  const missing: string[] = [];
  if (!props.selectedPatient) missing.push("انتخاب بیمار");
  if (!props.serviceId) missing.push("انتخاب خدمت");
  else if (props.requirementsReady && !props.selectionCheck.ok) missing.push("انتخاب منابع مورد نیاز");
  if (!props.localStart) missing.push("تعیین تاریخ و ساعت");
  return missing;
}

export function BookingForm(props: Props) {
  const {
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
    onAddToInvoice,
    canAddToInvoice,
    onSetWalkInNow,
    queuedCount = 0,
    onSubmitGroup,
    canSubmitGroup,
  } = props;
  const requirements = requirementsState.status === "ready" ? requirementsState.items : [];
  const requirementLines = describeRequirements(requirements, eligibleResources);
  const missing = missingSteps(props);
  const endLabel = endTimeLabel(localStart, durationMinutes);
  const formRef = useRef<HTMLFormElement | null>(null);
  const resourceNames = eligibleResources.filter((r) => selectedResourceIds.includes(r.id)).map((r) => r.resource_name);

  // Keyboard progression: once the chosen service's requirements arrive, move to the first resource.
  useEffect(() => {
    const form = formRef.current;
    if (!requirementsReady || !form) return;
    if (document.activeElement?.getAttribute("data-testid") === "service-select") {
      form.querySelector<HTMLInputElement>("[data-testid='resource-option'] input")?.focus();
    }
  }, [requirementsReady, serviceId]);

  return (
    <form ref={formRef} onSubmit={onSubmit} className="space-y-4" aria-label="ثبت نوبت">
      <SelectField
        label="خدمت"
        data-testid="service-select"
        value={serviceId}
        onChange={(e) => onServiceChange(e.target.value)}
        required
        disabled={!!pendingConflicts}
      >
        <option value="">انتخاب کنید</option>
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.service_name}
          </option>
        ))}
      </SelectField>

      <fieldset className="space-y-2" data-testid="resource-fieldset" disabled={!requirementsReady || !!pendingConflicts}>
        <legend className="ds-field-label flex w-full items-center justify-between gap-2">
          <span>منابع مورد نیاز</span>
          {requirementsReady ? (
            <StatusBadge tone={selectionCheck.ok ? "ok" : "neutral"}>
              {selectedResourceIds.length} از {neededCount || "حداقل 1"} انتخاب شد
            </StatusBadge>
          ) : null}
        </legend>
        {!serviceId ? <p className="ds-hint">پس از انتخاب خدمت، منابع مورد نیاز نمایش داده می‌شود.</p> : null}
        {requirementsState.status === "loading" ? <p className="ds-hint">در حال بارگذاری الزامات…</p> : null}
        {requirementsState.status === "error" && requirementsState.serviceId === serviceId ? (
          <p className="text-sm text-[var(--ds-danger)]">{requirementsState.message}</p>
        ) : null}
        {requirementsReady && requirementLines.length ? (
          <p className="text-sm text-[var(--ds-text-muted)]" data-testid="requirements-summary">
            این خدمت نیاز دارد به: <span className="font-medium text-[var(--ds-text)]">{requirementLines.join("، ")}</span>
          </p>
        ) : null}
        {requirementsReady && !requirementLines.length ? (
          <p className="text-sm text-[var(--ds-text-muted)]">برای این خدمت الزام مشخصی تعریف نشده؛ حداقل یک منبع فعال انتخاب کنید.</p>
        ) : null}
        {requirementsReady && !eligibleResources.length ? (
          <p className="text-sm text-[var(--ds-danger)]">منبع معتبری برای الزامات این خدمت در دسترس نیست.</p>
        ) : null}
        <ul className="grid max-h-48 gap-2 overflow-auto sm:grid-cols-2">
          {eligibleResources.map((resource) => {
            const checked = selectedResourceIds.includes(resource.id);
            return (
              <li key={resource.id}>
                <label
                  data-testid="resource-option"
                  data-checked={checked}
                  className="flex cursor-pointer items-center gap-2.5 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2 transition-colors data-[checked=true]:border-[var(--ds-primary)] data-[checked=true]:bg-[var(--ds-primary-soft)]"
                >
                  <input type="checkbox" className="ds-check" checked={checked} onChange={() => onToggleResource(resource.id)} />
                  <span className="min-w-0">
                    <span className="block truncate text-sm">{resource.resource_name}</span>
                    <span className="block text-xs text-[var(--ds-text-muted)]">{resourceTypeLabel(resource.resource_type)}</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        {!selectionCheck.ok && selectedResourceIds.length > 0 && requirementsReady ? (
          <p className="text-xs text-[var(--ds-danger)]">{selectionCheck.message}</p>
        ) : null}
      </fieldset>

      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[12rem] flex-1">
          <JalaliDateTimeField
            label="زمان شروع"
            testId="appointment-start"
            value={localStart}
            onChange={onLocalStartChange}
            required
            disabled={!!pendingConflicts}
            hint="تاریخ شمسی، ساعت به وقت تهران"
          />
        </div>
        {onSetWalkInNow ? (
          <Button type="button" variant="ghost" disabled={!!pendingConflicts || submitting} onClick={onSetWalkInNow} data-testid="walk-in-now">
            پذیرش فوری (الان)
          </Button>
        ) : null}
      </div>
      {serviceId ? (
        <p className="text-sm text-[var(--ds-text-muted)] tabular-nums" data-testid="booking-duration">
          مدت خدمت: {durationMinutes} دقیقه{endLabel ? ` — پایان تقریبی: ${endLabel}` : ""}
        </p>
      ) : null}

      <BookingSummary
        patient={props.selectedPatient}
        service={services.find((service) => service.id === serviceId)}
        resourceNames={resourceNames}
        localStart={localStart}
        endLabel={endLabel}
        durationMinutes={durationMinutes}
      />

      <div className="space-y-2 border-t border-[var(--ds-border)] pt-4">
        {missing.length ? (
          <p className="ds-hint" data-testid="booking-missing">
            برای ثبت نوبت لازم است: {missing.join("، ")}
          </p>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          {onAddToInvoice ? (
            <Button type="button" variant="ghost" disabled={!canAddToInvoice || submitting} onClick={onAddToInvoice} data-testid="add-service-line">
              افزودن خدمت به پیش‌فاکتور
            </Button>
          ) : null}
          <Button type="submit" icon="check" loading={submitting && !pendingConflicts && queuedCount === 0} disabled={!canSubmit || queuedCount > 0} data-testid="appointment-submit" className="w-full">
            {submitting && !pendingConflicts && queuedCount === 0 ? "در حال ثبت…" : "ثبت تک‌نوبت"}
          </Button>
        </div>
        {queuedCount > 0 && onSubmitGroup ? (
          <Button type="button" icon="check" loading={submitting} disabled={!canSubmitGroup} onClick={onSubmitGroup} data-testid="group-submit" className="w-full">
            {submitting ? "در حال ثبت گروه…" : `ثبت اتمی ${queuedCount} نوبت`}
          </Button>
        ) : null}
      </div>
    </form>
  );
}
