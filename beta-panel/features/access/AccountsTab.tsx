"use client";

import { useState, type FormEvent } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable, type DataTableColumn } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { staffKindLabel } from "@/features/staff/types";
import { AccountRolesDialog } from "./AccountRolesDialog";
import { EffectivePermissionsDialog } from "./EffectivePermissionsDialog";
import { ACCOUNT_PAGE_SIZE, accountDisplayName, governanceLabel, type AccountRow } from "./types";

type Modal = { kind: "roles" | "effective" | "status"; account: AccountRow } | null;

export function AccountsTab() {
  const { can, me } = useSession();
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [modal, setModal] = useState<Modal>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const query = useApiQuery<Page<AccountRow>>(
    `/api/v1/access/accounts${buildQuery({ q, limit: ACCOUNT_PAGE_SIZE, offset })}`,
    "بارگذاری حساب‌ها ناموفق بود",
    refresh,
  );

  async function confirmStatus(account: AccountRow) {
    setStatusError(null);
    const result = await apiJson(`/api/v1/access/accounts/${account.account_id}/status`, {
      method: "PUT",
      version: account.aggregate_version,
      body: { is_active: !account.is_active },
      fallbackMessage: "تغییر وضعیت حساب ناموفق بود",
    });
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
    setQ(draft.trim());
  }

  const columns: DataTableColumn<AccountRow>[] = [
    { key: "name", header: "کاربر", cell: (r) => <span><span className="font-medium">{accountDisplayName(r)}</span>{r.account_id === me?.account_id && <span className="ms-2 text-xs text-[var(--ds-text-muted)]">(شما)</span>}</span> },
    { key: "login", header: "شناسهٔ ورود", cell: (r) => <span dir="ltr" className="text-xs">{r.login_identifier}</span> },
    { key: "kind", header: "نوع", cell: (r) => (r.staff_kind ? staffKindLabel(r.staff_kind) : "—") },
    {
      key: "roles",
      header: "نقش‌ها",
      cell: (r) => (
        <span className="flex flex-wrap gap-1">
          {r.governance_roles.map((g) => <StatusBadge key={g} tone="warn">{governanceLabel(g)}</StatusBadge>)}
          {r.roles.map((c) => <StatusBadge key={c}>{c}</StatusBadge>)}
          {!r.roles.length && !r.governance_roles.length && <span className="text-[var(--ds-text-muted)]">بدون نقش</span>}
        </span>
      ),
    },
    { key: "status", header: "وضعیت", cell: (r) => (r.is_locked ? <StatusBadge tone="danger">قفل موقت</StatusBadge> : <StatusBadge tone={r.is_active ? "ok" : "warn"}>{r.is_active ? "فعال" : "معلق"}</StatusBadge>) },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <span className="flex flex-wrap gap-3 text-sm">
          {can(P.rolesView) && <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setModal({ kind: "effective", account: r })} data-testid="account-effective">دسترسی مؤثر</button>}
          {can(P.userRolesAssign) && <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setModal({ kind: "roles", account: r })} data-testid="account-roles">نقش‌ها</button>}
          {can(P.accountsSetActive) && r.account_id !== me?.account_id && (
            <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => { setStatusError(null); setModal({ kind: "status", account: r }); }} data-testid="account-status">
              {r.is_active ? "تعلیق" : "فعال‌سازی"}
            </button>
          )}
        </span>
      ),
    },
  ];

  const data = query.data;
  return (
    <div className="space-y-4" role="tabpanel" id="panel-accounts" aria-labelledby="tab-accounts">
      <form onSubmit={search} className="flex flex-wrap items-end gap-2">
        <label className="block min-w-48 flex-1 space-y-1 text-sm">
          <span className="ds-field-label">نام یا شناسهٔ ورود</span>
          <input className="ds-input" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={120} data-testid="accounts-search" aria-label="جستجوی حساب‌ها" />
        </label>
        <Button type="submit" data-testid="accounts-search-submit">اعمال</Button>
      </form>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مشاهدهٔ حساب‌ها" onRetry={query.reload}>
        {data && (
          <>
            <DataTable columns={columns} rows={data.items} rowKey={(r) => r.account_id} rowTestId="account-row" empty={<EmptyState title="حسابی یافت نشد" />} />
            {data.total > 0 && <Pagination total={data.total} limit={ACCOUNT_PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />}
          </>
        )}
      </QueryBoundary>
      {modal?.kind === "effective" && <EffectivePermissionsDialog account={modal.account} onClose={() => setModal(null)} />}
      {modal?.kind === "roles" && (
        <AccountRolesDialog account={modal.account} onClose={() => setModal(null)} onSaved={(m) => { setModal(null); toast.success(m); setRefresh((v) => v + 1); }} />
      )}
      {modal?.kind === "status" && (
        <Dialog open title={modal.account.is_active ? "تعلیق حساب" : "فعال‌سازی حساب"} onClose={() => setModal(null)} testId="account-status-dialog">
          <p className="mb-4 text-sm">
            {modal.account.is_active
              ? `حساب «${accountDisplayName(modal.account)}» معلق شود؟ هویت و سوابق حذف نمی‌شود و ورود فوراً متوقف می‌شود.`
              : `حساب «${accountDisplayName(modal.account)}» دوباره فعال شود؟`}
          </p>
          {statusError && <p className="ds-alert-danger mb-3" role="alert" data-testid="account-status-error">{statusError}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setModal(null)}>انصراف</Button>
            <Button onClick={() => void confirmStatus(modal.account)} data-testid="account-status-confirm">تأیید</Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
