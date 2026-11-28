"use client";

import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { CourseTemplatesStub } from "@/features/courses/CourseTemplatesStub";
import { apiJson } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { useState } from "react";

type DeptList = { items: { id: string; department_code: string; department_name: string; is_active: boolean }[] };
type InvList = { items: { id: string; item_code: string; item_name: string; quantity_on_hand: number }[] };
type LotList = {
  items: Array<{
    id: string;
    item_id: string;
    item_code: string;
    lot_code: string;
    lot_status: string;
    quantity_on_hand: number;
    expires_on: string | null;
  }>;
};
type EligList = { items: { id: string; service_name: string; practitioner_mapping_id: string; is_active: boolean }[] };

export function OpsConfigView() {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
  const canAny =
    can(P.departmentsView) || can(P.eligibilityManage) || can(P.inventoryView) || can(P.coursesView);
  const depts = useApiQuery<DeptList>(
    status === "ready" && can(P.departmentsView) ? "/api/v1/ops/departments" : null,
    "بارگذاری بخش‌ها ناموفق بود",
    refresh,
  );
  const elig = useApiQuery<EligList>(
    status === "ready" && can(P.eligibilityManage) ? "/api/v1/ops/eligibility" : null,
    "بارگذاری صلاحیت‌ها ناموفق بود",
    refresh,
  );
  const inv = useApiQuery<InvList>(
    status === "ready" && can(P.inventoryView) ? "/api/v1/ops/inventory/items" : null,
    "بارگذاری انبار ناموفق بود",
    refresh,
  );
  const lots = useApiQuery<LotList>(
    status === "ready" && can(P.inventoryView) ? "/api/v1/ops/inventory/lots" : null,
    "بارگذاری لات‌ها ناموفق بود",
    refresh,
  );
  const [invError, setInvError] = useState<string | null>(null);

  if (status === "loading") return <PageSkeleton />;
  if (!canAny) {
    return (
      <main data-testid="ops-page">
        <PageHeader title="پیکربندی عملیات" description="دسترسی ندارید." />
        <EmptyState title="دسترسی ندارید" description="مجوز بخش‌ها، صلاحیت یا انبار لازم است." />
      </main>
    );
  }

  return (
    <main className="space-y-8" data-testid="ops-page">
      <PageHeader
        title="پیکربندی عملیات"
        description="حداقل پیکربندی لازم برای چهار فضای کاری: بخش‌ها، صلاحیت خدمت، و انبار."
        actions={
          <Button variant="ghost" icon="refresh" onClick={() => setRefresh((v) => v + 1)}>
            به‌روزرسانی
          </Button>
        }
      />
      {depts.error || elig.error || inv.error ? (
        <Alert>{depts.error?.message || elig.error?.message || inv.error?.message}</Alert>
      ) : null}

      {can(P.departmentsView) ? (
        <section data-testid="ops-departments">
          <h2 className="ds-section-title mb-3">بخش‌ها</h2>
          <ul className="space-y-2">
            {(depts.data?.items ?? []).map((d) => (
              <li key={d.id} className="ds-card px-4 py-3 text-sm">
                <span className="font-medium">{d.department_name}</span>
                <span className="ms-2 text-[var(--ds-text-muted)] tabular-nums">{d.department_code}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {can(P.eligibilityManage) ? (
        <section data-testid="ops-eligibility">
          <h2 className="ds-section-title mb-3">صلاحیت کارکنان به خدمت</h2>
          <p className="ds-hint mb-2">{formatCount(elig.data?.items.length ?? 0)} پیوند فعال</p>
          <ul className="max-h-64 space-y-1 overflow-auto text-sm">
            {(elig.data?.items ?? []).slice(0, 40).map((e) => (
              <li key={e.id} className="rounded border border-[var(--ds-border)] px-3 py-2">
                {e.service_name} · {e.is_active ? "فعال" : "غیرفعال"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <CourseTemplatesStub />

      {can(P.inventoryView) ? (
        <section data-testid="ops-inventory" className="space-y-3">
          <h2 className="ds-section-title mb-3">انبار و FEFO</h2>
          {invError ? <Alert>{invError}</Alert> : null}
          <ul className="space-y-2">
            {(inv.data?.items ?? []).map((item) => (
              <li key={item.id} className="ds-card flex justify-between px-4 py-3 text-sm">
                <span>
                  {item.item_name} <span className="text-[var(--ds-text-muted)]">({item.item_code})</span>
                </span>
                <span className="tabular-nums">{formatCount(item.quantity_on_hand)}</span>
              </li>
            ))}
          </ul>
          <ul className="space-y-2" data-testid="ops-lots">
            {(lots.data?.items ?? []).slice(0, 40).map((lot) => (
              <li key={lot.id} className="ds-card flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <span>
                  {lot.item_code} / {lot.lot_code} · {lot.lot_status}
                  {lot.expires_on ? ` · انقضا ${lot.expires_on}` : ""} · موجودی {formatCount(lot.quantity_on_hand)}
                </span>
                {can(P.inventoryAdjust) && lot.lot_status === "AVAILABLE" && lot.quantity_on_hand > 0 ? (
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={async () => {
                      setInvError(null);
                      const result = await apiJson("/api/v1/ops/inventory/write-off", {
                        method: "POST",
                        body: {
                          item_id: lot.item_id,
                          lot_id: lot.id,
                          quantity: 1,
                          reason_code: "DEMO_WO",
                        },
                      });
                      if (!result.ok) {
                        setInvError(result.message);
                        return;
                      }
                      setRefresh((v) => v + 1);
                    }}
                    data-testid="lot-write-off"
                  >
                    خروج از رده ۱ واحد
                  </Button>
                ) : null}
                {can(P.inventoryAdjust) && lot.lot_status === "AVAILABLE" ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={async () => {
                      setInvError(null);
                      const result = await apiJson("/api/v1/ops/inventory/quarantine", {
                        method: "POST",
                        body: { item_id: lot.item_id, lot_id: lot.id, reason_code: "DEMO_Q" },
                      });
                      if (!result.ok) {
                        setInvError(result.message);
                        return;
                      }
                      setRefresh((v) => v + 1);
                    }}
                    data-testid="lot-quarantine"
                  >
                    قرنطینه
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
