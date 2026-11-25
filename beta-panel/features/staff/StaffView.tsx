"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { SelectField } from "@/components/forms/SelectField";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable, type DataTableColumn } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { ActiveBadge, StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { useDebouncedValue } from "@/lib/use-debounced";
import { ProvisionLoginDialog } from "./ProvisionLoginDialog";
import { StaffFormDialog } from "./StaffFormDialog";
import { STAFF_KINDS, STAFF_PAGE_SIZE, staffKindLabel, type StaffRow } from "./types";

type Dialog = { type: "form"; staff: StaffRow | null } | { type: "login"; staff: StaffRow } | null;

export function StaffView() {
  const { can, status } = useSession();
  const toast = useToast();
  const params = useSearchParams();
  const [draft, setDraft] = useState(params.get("q") ?? "");
  const [filters, setFilters] = useState({ q: params.get("q") ?? "", kind: "", status: "all" });
  const [offset, setOffset] = useState(0);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [refresh, setRefresh] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<StaffRow | null>(null);
  const debouncedDraft = useDebouncedValue(draft.trim(), 350);
  const [appliedDraft, setAppliedDraft] = useState(debouncedDraft);
  if (appliedDraft !== debouncedDraft) {
    setAppliedDraft(debouncedDraft);
    if (debouncedDraft !== filters.q) {
      setFilters((current) => ({ ...current, q: debouncedDraft }));
      setOffset(0);
    }
  }
  const allowed = can(P.staffView);

  const urlQuery = params.get("q") ?? "";
  const [seenUrlQuery, setSeenUrlQuery] = useState(urlQuery);
  if (seenUrlQuery !== urlQuery) {
    setSeenUrlQuery(urlQuery);
    setDraft(urlQuery);
    setAppliedDraft(urlQuery);
    setFilters((current) => ({ ...current, q: urlQuery }));
    setOffset(0);
  }

  const query = useApiQuery<Page<StaffRow>>(
    allowed
      ? `/api/v1/staff${buildQuery({ q: filters.q, kind: filters.kind, status: filters.status, limit: STAFF_PAGE_SIZE, offset })}`
      : null,
    "بارگذاری فهرست کارکنان ناموفق بود",
    refresh,
  );

  if (status === "loading") return <Skeleton className="h-64" />;
  if (!allowed) return <AccessDenied what="مشاهدهٔ کارکنان" />;

  const canManage = can(P.staffManage);
  const showLogin = can(P.accountsView);

  async function toggleActive(row: StaffRow) {
    if (busyId) return;
    setBusyId(row.staff_profile_id);
    const result = await apiJson<StaffRow>(`/api/v1/staff/${row.staff_profile_id}`, {
      method: "PATCH",
      version: row.aggregate_version,
      body: { is_active: !row.is_active },
      fallbackMessage: "تغییر وضعیت ناموفق بود",
    });
    setBusyId(null);
    setConfirming(null);
    if (!result.ok) {
      toast.failure(result.status === 412 ? "این پروفایل تغییر کرده است؛ فهرست تازه می‌شود" : result.message);
      if (result.status === 412) setRefresh((v) => v + 1);
      return;
    }
    toast.success(result.data.is_active ? "عضو فعال شد" : "عضو غیرفعال شد");
    setRefresh((v) => v + 1);
  }

  function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setFilters((current) => ({ ...current, q: draft.trim() }));
  }

  function requestToggle(row: StaffRow) {
    if (row.is_active) setConfirming(row);
    else void toggleActive(row);
  }

  const columns: DataTableColumn<StaffRow>[] = [
    { key: "name", header: "نام", cell: (r) => <span className="font-medium">{r.first_name} {r.last_name}</span> },
    { key: "kind", header: "نوع", cell: (r) => <StatusBadge tone={r.staff_kind === "DOCTOR" || r.staff_kind === "SPECIALIST" ? "info" : "neutral"}>{staffKindLabel(r.staff_kind)}</StatusBadge> },
    { key: "council", header: "کد نظام پزشکی", cell: (r) => r.medical_council_code ?? "—", className: "tabular-nums" },
    { key: "status", header: "وضعیت پروفایل", cell: (r) => <ActiveBadge active={r.is_active} /> },
    {
      key: "account",
      header: "حساب ورود به نرم‌افزار",
      cell: (r) =>
        r.account ? (
          <span className="inline-flex flex-wrap items-center gap-1.5">
            <StatusBadge tone={r.account.is_active ? "ok" : "warn"}>{r.account.is_active ? "حساب فعال" : "حساب معلق"}</StatusBadge>
            {showLogin && r.account.login_identifier ? <span dir="ltr" className="text-xs text-[var(--ds-text-muted)]">{r.account.login_identifier}</span> : null}
          </span>
        ) : (
          <span className="text-[var(--ds-text-muted)]">بدون حساب</span>
        ),
    },
    {
      key: "actions",
      header: "",
      className: "text-end whitespace-nowrap",
      cell: (r) =>
        canManage || (can(P.staffProvisionLogin) && !r.account) ? (
          <span className="inline-flex flex-wrap justify-end gap-1">
            {canManage ? (
              <>
                <Button variant="subtle" size="sm" icon="edit" onClick={() => setDialog({ type: "form", staff: r })} data-testid="staff-edit">ویرایش</Button>
                <Button variant="ghost" size="sm" disabled={busyId === r.staff_profile_id} onClick={() => requestToggle(r)} data-testid="staff-toggle">
                  {r.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                </Button>
              </>
            ) : null}
            {can(P.staffProvisionLogin) && !r.account ? (
              <Button variant="ghost" size="sm" icon="lock" onClick={() => setDialog({ type: "login", staff: r })} data-testid="staff-provision">ایجاد حساب ورود</Button>
            ) : null}
          </span>
        ) : null,
    },
  ];

  function saved(message: string) {
    setDialog(null);
    toast.success(message);
    setRefresh((v) => v + 1);
  }

  const data = query.data;
  return (
    <main className="space-y-5" data-testid="staff-page">
      <PageHeader
        title="کارکنان"
        description="پروفایل کارمندی با حساب ورود به نرم‌افزار یکی نیست: داشتن پروفایل یا پزشک بودن به‌تنهایی دسترسی نمی‌دهد."
        actions={canManage ? <Button icon="plus" onClick={() => setDialog({ type: "form", staff: null })} data-testid="staff-add">افزودن عضو</Button> : undefined}
      />
      <form onSubmit={search} className="ds-card flex flex-wrap items-end gap-3 p-3">
        <label className="block min-w-56 flex-1 space-y-1 text-sm">
          <span className="ds-field-label">جستجو</span>
          <span className="relative block">
            <Icon name="search" size="sm" className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-muted)]" />
            <input className="ds-input ps-9" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={120} data-testid="staff-search" placeholder="نام یا نام خانوادگی" aria-label="جستجوی کارکنان" />
          </span>
        </label>
        <SelectField label="نوع" value={filters.kind} onChange={(e) => { setOffset(0); setFilters((c) => ({ ...c, kind: e.target.value })); }} data-testid="staff-filter-kind">
          <option value="">همه</option>
          {STAFF_KINDS.map((k) => <option key={k} value={k}>{staffKindLabel(k)}</option>)}
        </SelectField>
        <SelectField label="وضعیت" value={filters.status} onChange={(e) => { setOffset(0); setFilters((c) => ({ ...c, status: e.target.value })); }} data-testid="staff-filter-status">
          <option value="all">همه</option>
          <option value="active">فعال</option>
          <option value="inactive">غیرفعال</option>
        </SelectField>
        <Button type="submit" variant="ghost" data-testid="staff-search-submit">اعمال</Button>
      </form>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مشاهدهٔ کارکنان" onRetry={query.reload}>
        {data ? (
          <>
            <DataTable columns={columns} rows={data.items} rowKey={(r) => r.staff_profile_id} rowTestId="staff-row" empty={<EmptyState icon="staff" title="عضوی یافت نشد" description="فیلترها را تغییر دهید یا عضو جدید اضافه کنید." />} />
            {data.total > 0 ? <Pagination total={data.total} limit={STAFF_PAGE_SIZE} offset={offset} onOffsetChange={setOffset} /> : null}
          </>
        ) : null}
      </QueryBoundary>
      {dialog?.type === "form" ? (
        <StaffFormDialog key={dialog.staff?.staff_profile_id ?? "new"} staff={dialog.staff} canProvisionLogin={can(P.staffProvisionLogin)} onClose={() => setDialog(null)} onSaved={saved} />
      ) : null}
      {dialog?.type === "login" ? <ProvisionLoginDialog staff={dialog.staff} onClose={() => setDialog(null)} onSaved={saved} /> : null}
      <ConfirmDialog
        open={!!confirming}
        title="غیرفعال‌سازی عضو"
        confirmLabel="غیرفعال‌سازی"
        tone="danger"
        busy={!!busyId}
        testId="staff-toggle-dialog"
        onCancel={() => setConfirming(null)}
        onConfirm={() => confirming && void toggleActive(confirming)}
      >
        <p>«{confirming?.first_name} {confirming?.last_name}» از فهرست انتخاب فعال کنار گذاشته می‌شود. حساب ورود او (در صورت وجود) جداگانه مدیریت می‌شود.</p>
      </ConfirmDialog>
    </main>
  );
}
