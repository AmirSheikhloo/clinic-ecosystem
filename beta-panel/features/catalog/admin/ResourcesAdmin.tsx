"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Pagination } from "@/components/ui/Pagination";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery, type ApiFail } from "@/lib/api";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { ADMIN_PAGE_SIZE, RESOURCE_TYPES, RESOURCE_TYPE_LABEL, type ResourceAdminRow } from "./types";

function ResourceDialog({ resource, onClose, onSaved }: { resource: ResourceAdminRow | null; onClose: () => void; onSaved: (m: string) => void }) {
  const editing = resource !== null;
  const [name, setName] = useState(resource?.resource_name ?? "");
  const [type, setType] = useState(resource?.resource_type ?? "ROOM");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);
  const idem = useIdempotencyKey();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setFailure(null);
    const result = editing
      ? await apiJson(`/api/v1/catalog/admin/resources/${resource.resource_id}`, { method: "PATCH", body: { resource_name: name.trim() }, fallbackMessage: "ذخیرهٔ منبع ناموفق بود" })
      : await (() => {
          const body = { resource_type: type, resource_name: name.trim() };
          return apiJson("/api/v1/catalog/admin/resources", { method: "POST", body, idempotencyKey: idem.keyFor(body), fallbackMessage: "ایجاد منبع ناموفق بود" });
        })();
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    idem.reset();
    onSaved(editing ? "منبع به‌روزرسانی شد" : "منبع جدید ایجاد شد");
  }

  return (
    <Dialog open title={editing ? "ویرایش منبع" : "منبع جدید"} onClose={onClose} testId="resource-dialog">
      <form onSubmit={submit} className="space-y-3">
        <TextField label="نام منبع" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} data-testid="resource-name" />
        <SelectField label="نوع منبع" value={type} disabled={editing} onChange={(e) => setType(e.target.value)} data-testid="resource-type">
          {RESOURCE_TYPES.map((t) => <option key={t} value={t}>{RESOURCE_TYPE_LABEL[t]}</option>)}
        </SelectField>
        {editing && <p className="text-xs text-[var(--ds-text-muted)]">نوع منبع پس از ایجاد قابل تغییر نیست.</p>}
        {failure && <Alert testId="resource-error">{failure.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button type="submit" disabled={busy || !name.trim()} data-testid="resource-submit">{busy ? "در حال ذخیره…" : "ذخیره"}</Button>
        </div>
      </form>
    </Dialog>
  );
}

export function ResourcesAdmin() {
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const [filters, setFilters] = useState({ q: "", type: "", status: "all" });
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [modal, setModal] = useState<{ resource: ResourceAdminRow | null } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const query = useApiQuery<Page<ResourceAdminRow>>(
    `/api/v1/catalog/admin/resources${buildQuery({ q: filters.q, resource_type: filters.type, status: filters.status, limit: ADMIN_PAGE_SIZE, offset })}`,
    "بارگذاری منابع ناموفق بود",
    refresh,
  );

  async function toggle(row: ResourceAdminRow) {
    if (busyId) return;
    setBusyId(row.resource_id);
    const result = await apiJson(`/api/v1/catalog/admin/resources/${row.resource_id}`, { method: "PATCH", body: { is_active: !row.is_active }, fallbackMessage: "تغییر وضعیت منبع ناموفق بود" });
    setBusyId(null);
    if (!result.ok) {
      toast.failure(result.message);
      return;
    }
    toast.success(row.is_active ? "منبع غیرفعال شد" : "منبع فعال شد");
    setRefresh((v) => v + 1);
  }

  const data = query.data;
  return (
    <div className="space-y-4" role="tabpanel" id="panel-resources" aria-labelledby="tab-resources">
      <form onSubmit={(e) => { e.preventDefault(); setOffset(0); setFilters((c) => ({ ...c, q: draft.trim() })); }} className="flex flex-wrap items-end gap-2">
        <label className="block min-w-48 flex-1 space-y-1 text-sm">
          <span className="ds-field-label">نام منبع</span>
          <input className="ds-input" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={120} data-testid="resources-search" aria-label="جستجوی منابع" />
        </label>
        <SelectField label="نوع" value={filters.type} onChange={(e) => { setOffset(0); setFilters((c) => ({ ...c, type: e.target.value })); }}>
          <option value="">همه</option>
          {RESOURCE_TYPES.map((t) => <option key={t} value={t}>{RESOURCE_TYPE_LABEL[t]}</option>)}
        </SelectField>
        <SelectField label="وضعیت" value={filters.status} onChange={(e) => { setOffset(0); setFilters((c) => ({ ...c, status: e.target.value })); }}>
          <option value="all">همه</option>
          <option value="active">فعال</option>
          <option value="inactive">غیرفعال</option>
        </SelectField>
        <Button type="submit">اعمال</Button>
        <Button onClick={() => setModal({ resource: null })} data-testid="resource-add">منبع جدید</Button>
      </form>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مدیریت منابع" onRetry={query.reload}>
        {data && (
          <>
            <DataTable
              rows={data.items}
              rowKey={(r) => r.resource_id}
              rowTestId="resource-row"
              empty={<EmptyState title="منبعی یافت نشد" />}
              columns={[
                { key: "name", header: "منبع", cell: (r) => <span className="font-medium">{r.resource_name}</span> },
                { key: "type", header: "نوع", cell: (r) => RESOURCE_TYPE_LABEL[r.resource_type] ?? r.resource_type },
                { key: "status", header: "وضعیت", cell: (r) => <ActiveBadge active={r.is_active} /> },
                {
                  key: "actions",
                  header: "",
                  cell: (r) => (
                    <span className="flex gap-3 text-sm">
                      <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setModal({ resource: r })} data-testid="resource-edit">ویرایش</button>
                      <button type="button" className="text-[var(--ds-primary)] hover:underline disabled:opacity-50" disabled={busyId === r.resource_id} onClick={() => void toggle(r)} data-testid="resource-toggle">{r.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}</button>
                    </span>
                  ),
                },
              ]}
            />
            {data.total > 0 && <Pagination total={data.total} limit={ADMIN_PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />}
          </>
        )}
      </QueryBoundary>
      {modal && <ResourceDialog key={modal.resource?.resource_id ?? "new"} resource={modal.resource} onClose={() => setModal(null)} onSaved={(m) => { setModal(null); toast.success(m); setRefresh((v) => v + 1); }} />}
    </div>
  );
}
