"use client";

import { useState, type FormEvent } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { SelectField } from "@/components/forms/SelectField";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { RequirementsDialog } from "./RequirementsDialog";
import { ServiceFormDialog } from "./ServiceFormDialog";
import { ADMIN_PAGE_SIZE, type ServiceAdminRow } from "./types";

type Modal = { kind: "form"; service: ServiceAdminRow | null } | { kind: "requirements"; id: string } | null;

export function ServicesAdmin({ initialQuery = "" }: { initialQuery?: string }) {
  const { can } = useSession();
  const toast = useToast();
  const [draft, setDraft] = useState(initialQuery);
  const [filters, setFilters] = useState({ q: initialQuery, status: "all" });
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [modal, setModal] = useState<Modal>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const query = useApiQuery<Page<ServiceAdminRow>>(
    `/api/v1/catalog/admin/services${buildQuery({ q: filters.q, status: filters.status, limit: ADMIN_PAGE_SIZE, offset })}`,
    "بارگذاری خدمات ناموفق بود",
    refresh,
  );

  async function toggle(row: ServiceAdminRow) {
    if (busyId) return;
    setBusyId(row.service_id);
    const result = await apiJson(`/api/v1/catalog/admin/services/${row.service_id}`, {
      method: "PATCH",
      version: row.aggregate_version,
      body: { is_active: !row.is_active },
      fallbackMessage: "تغییر وضعیت خدمت ناموفق بود",
    });
    setBusyId(null);
    if (!result.ok) {
      toast.failure(result.status === 412 ? "این خدمت تغییر کرده است؛ فهرست تازه می‌شود" : result.message);
      if (result.status === 412) setRefresh((v) => v + 1);
      return;
    }
    toast.success(row.is_active ? "خدمت غیرفعال شد" : "خدمت فعال شد");
    setRefresh((v) => v + 1);
  }

  function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setFilters((c) => ({ ...c, q: draft.trim() }));
  }

  const data = query.data;
  const saved = (message: string) => {
    setModal(null);
    toast.success(message);
    setRefresh((v) => v + 1);
  };

  return (
    <div className="space-y-4" role="tabpanel" id="panel-services" aria-labelledby="tab-services">
      <form onSubmit={search} className="flex flex-wrap items-end gap-2">
        <label className="block min-w-48 flex-1 space-y-1 text-sm">
          <span className="ds-field-label">نام یا کد خدمت</span>
          <input className="ds-input" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={120} data-testid="services-search" aria-label="جستجوی خدمات" />
        </label>
        <SelectField label="وضعیت" value={filters.status} onChange={(e) => { setOffset(0); setFilters((c) => ({ ...c, status: e.target.value })); }} data-testid="services-status">
          <option value="all">همه</option>
          <option value="active">فعال</option>
          <option value="inactive">غیرفعال</option>
        </SelectField>
        <Button type="submit">اعمال</Button>
        <Button onClick={() => setModal({ kind: "form", service: null })} data-testid="service-add">خدمت جدید</Button>
      </form>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مدیریت خدمات" onRetry={query.reload}>
        {data && (
          <>
            <DataTable
              rows={data.items}
              rowKey={(r) => r.service_id}
              rowTestId="service-row"
              empty={<EmptyState title="خدمتی یافت نشد" />}
              columns={[
                { key: "name", header: "خدمت", cell: (r) => <span><span className="font-medium">{r.service_name}</span>{r.service_code && <span className="ms-2 text-xs text-[var(--ds-text-muted)]" dir="ltr">{r.service_code}</span>}</span> },
                { key: "dur", header: "مدت (دقیقه)", cell: (r) => formatCount(r.default_duration_minutes), className: "tabular-nums" },
                { key: "price", header: "تعرفه (ریال)", cell: (r) => formatCount(r.default_price_irr), className: "tabular-nums" },
                { key: "req", header: "الزامات", cell: (r) => formatCount(r.requirement_count ?? 0), className: "tabular-nums" },
                { key: "status", header: "وضعیت", cell: (r) => <ActiveBadge active={r.is_active} /> },
                {
                  key: "actions",
                  header: "",
                  cell: (r) => (
                    <span className="flex flex-wrap gap-3 text-sm">
                      <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setModal({ kind: "form", service: r })} data-testid="service-edit">ویرایش</button>
                      <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setModal({ kind: "requirements", id: r.service_id })} data-testid="service-requirements">الزامات</button>
                      <button type="button" className="text-[var(--ds-primary)] hover:underline disabled:opacity-50" disabled={busyId === r.service_id} onClick={() => void toggle(r)} data-testid="service-toggle">{r.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}</button>
                    </span>
                  ),
                },
              ]}
            />
            {data.total > 0 && <Pagination total={data.total} limit={ADMIN_PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />}
          </>
        )}
      </QueryBoundary>
      {modal?.kind === "form" && <ServiceFormDialog key={modal.service?.service_id ?? "new"} service={modal.service} onClose={() => setModal(null)} onSaved={saved} />}
      {modal?.kind === "requirements" && can(P.servicesManage) && <RequirementsDialog serviceId={modal.id} onClose={() => setModal(null)} onSaved={saved} />}
    </div>
  );
}
