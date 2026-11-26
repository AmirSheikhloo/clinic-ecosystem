"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { normalizeInputDigits } from "@/lib/format/digits";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { parseWholeNumber, type ServiceAdminRow } from "./types";

type Props = { service: ServiceAdminRow | null; onClose: () => void; onSaved: (message: string) => void };

export function ServiceFormDialog({ service, onClose, onSaved }: Props) {
  const editing = service !== null;
  const [name, setName] = useState(service?.service_name ?? "");
  const [code, setCode] = useState(service?.service_code ?? "");
  const [duration, setDuration] = useState(String(service?.default_duration_minutes ?? 30));
  const [price, setPrice] = useState(String(service?.default_price_irr ?? 0));
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);
  const idem = useIdempotencyKey();

  const minutes = parseWholeNumber(duration);
  const irr = parseWholeNumber(price);
  const valid = name.trim().length > 0 && minutes !== null && minutes > 0 && minutes <= 1440 && irr !== null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !valid || minutes === null || irr === null) return;
    setBusy(true);
    setFailure(null);
    const fields = {
      service_name: name.trim(),
      service_code: code.trim() || null,
      default_duration_minutes: minutes,
      default_price_irr: irr,
    };
    const result = editing
      ? await apiJson(`/api/v1/catalog/admin/services/${service.service_id}`, {
          method: "PATCH",
          version: service.aggregate_version,
          body: fields,
          fallbackMessage: "ذخیرهٔ خدمت ناموفق بود",
        })
      : await apiJson("/api/v1/catalog/admin/services", {
          method: "POST",
          body: fields,
          idempotencyKey: idem.keyFor(fields),
          fallbackMessage: "ایجاد خدمت ناموفق بود",
        });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    idem.reset();
    onSaved(editing ? "خدمت به‌روزرسانی شد" : "خدمت جدید ایجاد شد");
  }

  return (
    <Dialog open title={editing ? "ویرایش خدمت" : "خدمت جدید"} onClose={onClose} testId="service-dialog">
      <form onSubmit={submit} className="space-y-3">
        <TextField label="نام خدمت" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} data-testid="service-name" />
        <TextField label="کد خدمت (اختیاری)" value={code} onChange={(e) => setCode(e.target.value)} maxLength={64} dir="ltr" data-testid="service-code" />
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="مدت پیش‌فرض (دقیقه)" inputMode="numeric" value={duration} onChange={(e) => setDuration(normalizeInputDigits(e.target.value))} required data-testid="service-duration" />
          <TextField label="تعرفهٔ پیش‌فرض (ریال)" inputMode="numeric" value={price} onChange={(e) => setPrice(normalizeInputDigits(e.target.value))} required data-testid="service-price" />
        </div>
        {!valid && <p className="text-xs text-[var(--ds-text-muted)]">نام، مدت (۱ تا ۱۴۴۰ دقیقه) و تعرفهٔ عددی الزامی است.</p>}
        {failure && <Alert testId="service-error">{failure.status === 412 ? "این خدمت در این فاصله تغییر کرده است؛ پنجره را ببندید و دوباره باز کنید." : failure.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button type="submit" disabled={busy || !valid} data-testid="service-submit">{busy ? "در حال ذخیره…" : "ذخیره"}</Button>
        </div>
      </form>
    </Dialog>
  );
}
