"use client";

import { useState, type FormEvent } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { SearchField } from "@/components/forms/SearchField";
import { DataTable, type DataTableColumn } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { useDebouncedValue } from "@/lib/use-debounced";
import { staffKindLabel } from "@/features/staff/types";
import { AccountRolesDialog } from "./AccountRolesDialog";
import { EffectivePermissionsDialog } from "./EffectivePermissionsDialog";
import { ACCOUNT_PAGE_SIZE, accountDisplayName, governanceLabel, type AccountRow, type RoleRow } from "./types";

type Modal = { kind: "roles" | "effective" | "status"; account: AccountRow } | null;

export function AccountsTab() {
  const { can, me } = useSession();
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const debounced = useDebouncedValue(draft.trim(), 350);
  const q = submitted ?? debounced;
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [modal, setModal] = useState<Modal>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const query = useApiQuery<Page<AccountRow>>(
    `/api/v1/access/accounts${buildQuery({ q, limit: ACCOUNT_PAGE_SIZE, offset })}`,
    "بارگذاری حساب‌ها ناموفق بود",
    refresh,
    { keepPrevious: true },
  );

  const roleCatalog = useApiQuery<{ items: RoleRow[] }>(can(P.rolesView) ? "/api/v1/access/roles" : null);
  const roleNames = new Map((roleCatalog.data?.items ?? []).map((r) => [r.role_code, r.role_name]));

  async function confirmStatus(account: AccountRow) {
    if (busy) return;
    setBusy(true);
    setStatusError(null);
    const result = await apiJson(`/api/v1/access/accounts/${account.account_id}/status`, {
      method: "PUT",
      version: account.aggregate_version,
      body: { is_active: !account.is_active },
      fallbackMessage: "تغییر وضعیت حساب ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setStatusError(result.status === 412 ? "حساب در این فاصله تغییر کرده است؛ فهرست تازه می‌شود." : result.message);
      if (result.status === 412) setRefresh((v) => v + 1);
      return;
    }
    setModal(null);
    toast.success(account.is_active ? "حساب معلق شد؛ نشست‌های جاری بلافاصله نامعتبر می‌شوند" : "حساب دوباره فعال شد");
    setRefresh((v) => v + 1);
  }

  function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setSubmitted(draft.trim());
  }

  const columns: DataTableColumn<AccountRow>[] = [
    { key: "name", header: "کاربر", cell: (r) => <span><span className="font-medium">{accountDisplayName(r)}</span>{r.account_id === me?.account_id && <StatusBadge tone="info">شما</StatusBadge>}</span> },
    { key: "login", header: "شناسهٔ ورود", cell: (r) => <span dir="ltr" className="text-xs">{r.login_identifier}</span> },
    { key: "kind", header: "نوع", cell: (r) => (r.staff_kind ? staffKindLabel(r.staff_kind) : "—") },
    {
      key: "roles",
      header: "نقش‌ها",
      cell: (r) => (
        <span className="flex flex-wrap gap-1">
          {r.governance_roles.map((g) => <StatusBadge key={g} tone="warn">{governanceLabel(g)}</StatusBadge>)}
          {r.roles.map((c) => <StatusBadge key={c}>{roleNames.get(c) ?? c}</StatusBadge>)}
          {!r.roles.length && !r.governance_roles.length && <span className="text-[var(--ds-text-muted)]">بدون نقش</span>}
        </span>
      ),
    },
    { key: "status", header: "وضعیت", cell: (r) => (r.is_locked ? <StatusBadge tone="danger">قفل موقت</StatusBadge> : <StatusBadge tone={r.is_active ? "ok" : "warn"}>{r.is_active ? "فعال" : "معلق"}</StatusBadge>) },
    {
      key: "actions",
      header: "",
      className: "text-end whitespace-nowrap",
      cell: (r) => (
        <span className="inline-flex flex-wrap justify-end gap-1">
          {can(P.rolesView) ? <Button variant="subtle" size="sm" onClick={() => setModal({ kind: "effective", account: r })} data-testid="account-effective">دسترسی مؤثر</Button> : null}
          {can(P.userRolesAssign) ? <Button variant="subtle" size="sm" onClick={() => setModal({ kind: "roles", account: r })} data-testid="account-roles">نقش‌ها</Button> : null}
          {can(P.accountsSetActive) && r.account_id !== me?.account_id ? (
            <Button variant={r.is_active ? "danger" : "ghost"} size="sm" onClick={() => { setStatusError(null); setModal({ kind: "status", account: r }); }} data-testid="account-status">
              {r.is_active ? "تعلیق" : "فعال‌سازی"}
            </Button>
          ) : null}
        </span>
      ),
    },
  ];

  const data = query.data;
  return (
    <div className="space-y-4" role="tabpanel" id="panel-accounts" aria-labelledby="tab-accounts">
      <form onSubmit={search} className="ds-card ds-filter-grid p-3">
        <div className="ds-filter-wide">
          <SearchField
            label="جستجو"
            value={draft}
            onValueChange={(value) => { setSubmitted(null); setOffset(0); setDraft(value); }}
            maxLength={120}
            busy={query.loading || query.refreshing}
            placeholder="نام یا شناسهٔ ورود"
            data-testid="accounts-search"
            aria-label="جستجوی حساب‌ها"
          />
        </div>
        <Button type="submit" variant="ghost" data-testid="accounts-search-submit">اعمال</Button>
      </form>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مشاهدهٔ حساب‌ها" onRetry={query.reload}>
        {data && (
          <>
            <DataTable columns={columns} rows={data.items} rowKey={(r) => r.account_id} rowTestId="account-row" busy={query.refreshing} minWidth="48rem" empty={<EmptyState icon="access" title="حسابی یافت نشد" description="عبارت جستجو را تغییر دهید." />} />
            {data.total > 0 && <Pagination total={data.total} limit={ACCOUNT_PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />}
          </>
        )}
      </QueryBoundary>
      {modal?.kind === "effective" && <EffectivePermissionsDialog account={modal.account} onClose={() => setModal(null)} />}
      {modal?.kind === "roles" && (
        <AccountRolesDialog account={modal.account} onClose={() => setModal(null)} onSaved={(m) => { setModal(null); toast.success(m); setRefresh((v) => v + 1); }} />
      )}
      {modal?.kind === "status" ? (
        <ConfirmDialog
          open
          tone={modal.account.is_active ? "danger" : "primary"}
          title={modal.account.is_active ? "تعلیق حساب" : "فعال‌سازی حساب"}
          confirmLabel={modal.account.is_active ? "تعلیق حساب" : "فعال‌سازی"}
          busy={busy}
          testId="account-status-dialog"
          onCancel={() => setModal(null)}
          onConfirm={() => void confirmStatus(modal.account)}
        >
          <p>
            {modal.account.is_active
              ? `حساب «${accountDisplayName(modal.account)}» معلق شود؟ هویت و سوابق حذف نمی‌شود و ورود او فوراً متوقف می‌شود.`
              : `حساب «${accountDisplayName(modal.account)}» دوباره فعال شود؟`}
          </p>
          {statusError ? <Alert testId="account-status-error">{statusError}</Alert> : null}
        </ConfirmDialog>
      ) : null}
    </div>
  );
}
