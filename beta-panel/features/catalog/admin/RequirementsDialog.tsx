"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { normalizeInputDigits } from "@/lib/format/digits";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { RESOURCE_TYPE_LABEL, RESOURCE_TYPES, parseWholeNumber, type RequirementRow, type ResourceAdminRow, type ServiceDetail } from "./types";

type Props = { serviceId: string; onClose: () => void; onSaved: (message: string) => void };

type Draft = { group: string; type: string; specific: string; quantity: string };

function toDraft(r: RequirementRow): Draft {
  return { group: r.requirement_group, type: r.required_resource_type, specific: r.specific_resource_id ?? "", quantity: String(r.quantity_required) };
}

export function RequirementsDialog({ serviceId, onClose, onSaved }: Props) {
  const detail = useApiQuery<ServiceDetail>(`/api/v1/catalog/admin/services/${serviceId}`, "بارگذاری الزامات ناموفق بود");
  const resources = useApiQuery<Page<ResourceAdminRow>>("/api/v1/catalog/admin/resources?status=active&limit=100");
  const [edited, setEdited] = useState<Draft[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);

  const rows = edited ?? detail.data?.requirements.map(toDraft) ?? [];
  const parsed = rows.map((r) => ({ ...r, qty: parseWholeNumber(r.quantity) }));
  const valid = parsed.every((r) => r.group.trim() && r.qty !== null && r.qty >= 1 && r.qty <= 20);

  function update(index: number, patch: Partial<Draft>) {
    setEdited(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  async function save() {
    if (!detail.data || busy || !valid) return;
    setBusy(true);
    setFailure(null);
    const result = await apiJson(`/api/v1/catalog/admin/services/${serviceId}/requirements`, {
      method: "PUT",
      version: detail.data.aggregate_version,
      body: {
        items: parsed.map((r) => ({
          requirement_group: r.group.trim(),
          required_resource_type: r.type,
          specific_resource_id: r.specific || null,
          quantity_required: r.qty,
        })),
      },
      fallbackMessage: "ذخیرهٔ الزامات ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    onSaved("الزامات منابع خدمت به‌روزرسانی شد");
  }

  return (
    <Dialog open size="lg" title={`الزامات منابع — ${detail.data?.service_name ?? ""}`} onClose={onClose} testId="requirements-dialog">
      <QueryBoundary loading={detail.loading} error={detail.error} deniedWhat="مدیریت خدمات" onRetry={detail.reload}>
        <div className="space-y-3">
          <p className="text-sm text-[var(--ds-text-muted)]">
            هر الزام یک گروه، نوع منبع و تعداد دارد. بدون الزام، رزرو دستی حداقل یک منبع فعال می‌خواهد.
          </p>
          {rows.length === 0 && <p className="text-sm" data-testid="requirements-empty">هنوز الزامی تعریف نشده است.</p>}
          {rows.map((row, index) => (
            <div key={index} className="grid items-end gap-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3 sm:grid-cols-5" data-testid="requirement-row">
              <TextField label="گروه" value={row.group} onChange={(e) => update(index, { group: e.target.value })} maxLength={64} dir="ltr" />
              <SelectField label="نوع منبع" value={row.type} onChange={(e) => update(index, { type: e.target.value })}>
                {RESOURCE_TYPES.map((t) => <option key={t} value={t}>{RESOURCE_TYPE_LABEL[t]}</option>)}
              </SelectField>
              <SelectField label="منبع مشخص (اختیاری)" value={row.specific} onChange={(e) => update(index, { specific: e.target.value })}>
                <option value="">هر منبع از این نوع</option>
                {(resources.data?.items ?? []).filter((r) => r.resource_type === row.type).map((r) => <option key={r.resource_id} value={r.resource_id}>{r.resource_name}</option>)}
              </SelectField>
              <TextField label="تعداد" inputMode="numeric" value={row.quantity} onChange={(e) => update(index, { quantity: normalizeInputDigits(e.target.value) })} />
              <Button variant="ghost" className="ds-btn-danger" onClick={() => setEdited(rows.filter((_, i) => i !== index))}>حذف</Button>
            </div>
          ))}
          <Button variant="ghost" onClick={() => setEdited([...rows, { group: `group${rows.length + 1}`, type: "ROOM", specific: "", quantity: "1" }])} data-testid="requirement-add">
            افزودن الزام
          </Button>
          {failure && <Alert testId="requirements-error">{failure.status === 412 ? "خدمت در این فاصله تغییر کرده است؛ پنجره را دوباره باز کنید." : failure.message}</Alert>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>انصراف</Button>
            <Button disabled={busy || !valid} onClick={() => void save()} data-testid="requirements-save">{busy ? "در حال ذخیره…" : "ذخیره الزامات"}</Button>
          </div>
        </div>
      </QueryBoundary>
    </Dialog>
  );
}
