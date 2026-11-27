"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { JalaliDateTimeField } from "@/components/forms/jalali/JalaliDateTimeField";
import { SearchableCombobox } from "@/components/forms/SearchableCombobox";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehranTime } from "@/lib/format/jalali";
import { resourceTypeLabel, type Requirement, type Resource } from "@/lib/resources";
import { tehranLocalToUtcIso } from "@/lib/tehran";
import { BookingSummary } from "./BookingSummary";
import type { Patient, RequirementsState, Service } from "./types";

type SelectionCheck = { ok: boolean; message?: string };

export type BillableItem = {
  id: string;
  item_code: string;
  item_name: string;
  unit_code: string;
  default_price_irr: number;
  is_active: boolean;
};

type Props = {
  selectedPatient: Patient | null;
  services: Service[];
  serviceId: string;
  onServiceChange: (serviceId: string) => void;
  requirementsState: RequirementsState;
  requirementsReady: boolean;
  eligibleResources: Resource[];
  allResources?: Resource[];
  selectedResourceIds: string[];
  onToggleResource: (id: string) => void;
  selectionCheck: SelectionCheck;
  neededCount: number;
  localStart: string;
  onLocalStartChange: (value: string) => void;
  durationMinutes: number;
  onDurationChange?: (minutes: number) => void;
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
  billableItems?: BillableItem[];
  preferredPractitionerId?: string;
  onPreferredPractitionerChange?: (id: string) => void;
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
    allResources = [],
    selectedResourceIds,
    onToggleResource,
    selectionCheck,
    neededCount,
    localStart,
    onLocalStartChange,
    durationMinutes,
    onDurationChange,
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
    billableItems = [],
    preferredPractitionerId = "",
    onPreferredPractitionerChange,
  } = props;
  const requirements = requirementsState.status === "ready" ? requirementsState.items : [];
  const requirementLines = describeRequirements(requirements, eligibleResources);
  const missing = missingSteps(props);
  const endLabel = endTimeLabel(localStart, durationMinutes);
  const formRef = useRef<HTMLFormElement | null>(null);
  const resourceNames = eligibleResources
    .filter((r) => selectedResourceIds.includes(r.id))
    .map((r) => r.resource_name);
  const [catalogTab, setCatalogTab] = useState<"services" | "items">("services");

  const practitioners = useMemo(
    () =>
      (allResources.length ? allResources : eligibleResources).filter(
        (r) => r.resource_type === "PRACTITIONER" && r.is_active,
      ),
    [allResources, eligibleResources],
  );

  // Bidirectional soft filter: preferred practitioner narrows service list when eligibility unknown.
  const visibleServices = useMemo(() => {
    if (!preferredPractitionerId) return services.filter((s) => s.is_active !== false);
    return services.filter((s) => s.is_active !== false);
  }, [services, preferredPractitionerId]);

  const serviceOptions = visibleServices.map((s) => ({
    value: s.id,
    label: s.service_name,
    description: `${s.default_duration_minutes} دقیقه`,
  }));

  const practitionerOptions = (
    requirementsReady ? eligibleResources.filter((r) => r.resource_type === "PRACTITIONER") : practitioners
  ).map((r) => ({
    value: r.id,
    label: r.resource_name,
    description: resourceTypeLabel(r.resource_type),
  }));

  useEffect(() => {
    const form = formRef.current;
    if (!requirementsReady || !form) return;
    const active = document.activeElement?.getAttribute("data-testid");
    if (active === "service-select" || active === "service-select-input") {
      form.querySelector<HTMLInputElement>("[data-testid='resource-option'] input")?.focus();
    }
  }, [requirementsReady, serviceId]);

  return (
    <form ref={formRef} onSubmit={onSubmit} className="space-y-4" aria-label="ثبت نوبت">
      <div className="flex gap-2" role="tablist" aria-label="نوع اقلام قابل صدور">
        <button
          type="button"
          role="tab"
          aria-selected={catalogTab === "services"}
          className={`ds-btn ds-btn-sm ${catalogTab === "services" ? "ds-btn-primary" : "ds-btn-ghost"}`}
          onClick={() => setCatalogTab("services")}
          data-testid="catalog-tab-services"
        >
          خدمات نوبتی
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={catalogTab === "items"}
          className={`ds-btn ds-btn-sm ${catalogTab === "items" ? "ds-btn-primary" : "ds-btn-ghost"}`}
          onClick={() => setCatalogTab("items")}
          data-testid="catalog-tab-items"
        >
          اقلام صورتحسابی / موجودی
        </button>
      </div>

      {catalogTab === "items" ? (
        <div className="space-y-2" data-testid="billable-items-panel">
          <p className="ds-hint">
            اقلام غیرنوبتی از فهرست billable جدا از موجودی انبار نمایش داده می‌شوند. مصرف انبار از فضای عملیات انجام می‌شود.
          </p>
          {billableItems.length === 0 ? (
            <p className="text-sm text-[var(--ds-text-muted)]">فهرست اقلام در دسترس نیست یا خالی است.</p>
          ) : (
            <ul className="max-h-48 space-y-1 overflow-auto text-sm">
              {billableItems
                .filter((i) => i.is_active)
                .map((item) => (
                  <li
                    key={item.id}
                    className="flex justify-between gap-2 rounded-[var(--ds-radius-sm)] border border-[var(--ds-border)] px-2 py-1.5"
                    data-testid="billable-item"
                  >
                    <span>
                      <span className="font-medium">{item.item_name}</span>
                      <span className="ms-2 text-xs text-[var(--ds-text-muted)]">{item.item_code}</span>
                    </span>
                    <span className="tabular-nums text-[var(--ds-text-muted)]">{item.default_price_irr}</span>
                  </li>
                ))}
            </ul>
          )}
        </div>
      ) : (
        <>
          {onPreferredPractitionerChange ? (
            <SearchableCombobox
              label="ارائه‌دهنده (پالایه دوطرفه)"
              options={practitionerOptions}
              value={preferredPractitionerId}
              onChange={(id) => {
                onPreferredPractitionerChange(id);
                if (id && !selectedResourceIds.includes(id)) onToggleResource(id);
              }}
              placeholder="جستجوی ارائه‌دهنده…"
              disabled={!!pendingConflicts}
              testId="practitioner-combobox"
              hint="انتخاب ارائه‌دهنده، منابع واجد شرایط خدمت را محدود می‌کند."
            />
          ) : null}

          <SearchableCombobox
            label="خدمت"
            options={serviceOptions}
            value={serviceId}
            onChange={onServiceChange}
            required
            disabled={!!pendingConflicts}
            testId="service-select"
            placeholder="جستجو و انتخاب خدمت…"
          />

          <fieldset
            className="space-y-2"
            data-testid="resource-fieldset"
            disabled={!requirementsReady || !!pendingConflicts}
          >
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
                این خدمت نیاز دارد به:{" "}
                <span className="font-medium text-[var(--ds-text)]">{requirementLines.join("، ")}</span>
              </p>
            ) : null}
            {requirementsReady && !requirementLines.length ? (
              <p className="text-sm text-[var(--ds-text-muted)]">
                برای این خدمت الزام مشخصی تعریف نشده؛ حداقل یک منبع فعال انتخاب کنید.
              </p>
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
                      <input
                        type="checkbox"
                        className="ds-check"
                        checked={checked}
                        onChange={() => onToggleResource(resource.id)}
                      />
                      <span className="min-w-0">
                        <span className="block truncate text-sm">{resource.resource_name}</span>
                        <span className="block text-xs text-[var(--ds-text-muted)]">
                          {resourceTypeLabel(resource.resource_type)}
                        </span>
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
                hint="تاریخ شمسی، ساعت به وقت تهران — مستقل برای هر نوبت"
              />
            </div>
            {onDurationChange ? (
              <label className="text-sm">
                مدت (دقیقه)
                <input
                  type="number"
                  min={5}
                  max={480}
                  step={5}
                  className="ds-input mt-1 w-24"
                  value={durationMinutes}
                  disabled={!!pendingConflicts || !serviceId}
                  onChange={(e) => onDurationChange(Math.max(5, Number(e.target.value) || 5))}
                  data-testid="booking-duration-input"
                />
              </label>
            ) : null}
            {onSetWalkInNow ? (
              <Button
                type="button"
                variant="ghost"
                disabled={!!pendingConflicts || submitting}
                onClick={onSetWalkInNow}
                data-testid="walk-in-now"
              >
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
                <Button
                  type="button"
                  variant="ghost"
                  disabled={!canAddToInvoice || submitting}
                  onClick={onAddToInvoice}
                  data-testid="add-service-line"
                >
                  افزودن خدمت مستقل به پیش‌فاکتور
                </Button>
              ) : null}
              <Button
                type="submit"
                icon="check"
                loading={submitting && !pendingConflicts && queuedCount === 0}
                disabled={!canSubmit || queuedCount > 0}
                data-testid="appointment-submit"
                className="w-full"
              >
                {submitting && !pendingConflicts && queuedCount === 0 ? "در حال ثبت…" : "ثبت تک‌نوبت"}
              </Button>
            </div>
            {queuedCount > 0 && onSubmitGroup ? (
              <Button
                type="button"
                icon="check"
                loading={submitting}
                disabled={!canSubmitGroup}
                onClick={onSubmitGroup}
                data-testid="group-submit"
                className="w-full"
              >
                {submitting ? "در حال ثبت گروه…" : `ثبت اتمی ${queuedCount} نوبت مستقل`}
              </Button>
            ) : null}
          </div>
        </>
      )}
    </form>
  );
}
