"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { CheckboxField } from "@/components/forms/CheckboxField";
import { SelectField } from "@/components/forms/SelectField";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, type ApiFail } from "@/lib/api";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { accountDisplayName, governanceLabel, toggleInSet, type AccountRow, type GovernanceRow } from "./types";

type Target = { person_id: string; name: string; roles: string[] };

function GovernanceDialog({ target, roles, onClose, onSaved }: { target: Target; roles: string[]; onClose: () => void; onSaved: () => void }) {
  const [selected, setSelected] = useState(target.roles);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);

  async function save() {
    setBusy(true);
    setFailure(null);
    const result = await apiJson(`/api/v1/access/governance/${target.person_id}`, {
      method: "PUT",
      body: { roles: selected },
      fallbackMessage: "تغییر نقش حاکمیتی ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    onSaved();
  }

  return (
    <Dialog open title={`نقش‌های حاکمیتی — ${target.name}`} onClose={onClose} testId="governance-dialog">
      <div className="space-y-3">
        {roles.map((role) => (
          <CheckboxField
            key={role}
            id={`gov-${role}`}
            label={governanceLabel(role)}
            hint={role === "CLINIC_OWNER" || role === "CLINIC_MANAGER" ? "فقط مالک می‌تواند این نقش را تغییر دهد" : undefined}
            checked={selected.includes(role)}
            onChange={(e) => setSelected(toggleInSet(selected, role, e.target.checked))}
            data-testid={`gov-${role}`}
          />
        ))}
        <p className="text-xs text-[var(--ds-text-muted)]">نقش حاکمیتی به‌تنهایی مجوزی اعطا نمی‌کند؛ تغییر نقش خودتان و حذف آخرین مالک مجاز نیست.</p>
        {failure && <Alert testId="governance-error">{failure.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button disabled={busy} onClick={() => void save()} data-testid="governance-save">{busy ? "در حال ذخیره…" : "ذخیره"}</Button>
        </div>
      </div>
    </Dialog>
  );
}

export function GovernanceTab() {
  const { can } = useSession();
  const toast = useToast();
  const [refresh, setRefresh] = useState(0);
  const [target, setTarget] = useState<Target | null>(null);
  const [pick, setPick] = useState("");
  const canManage = can(P.governanceManage);
  const list = useApiQuery<{ items: GovernanceRow[] }>("/api/v1/access/governance", "بارگذاری نقش‌های حاکمیتی ناموفق بود", refresh);
  const catalog = useApiQuery<{ governance_roles: string[] }>(can(P.rolesView) ? "/api/v1/access/permissions" : null);
  const accounts = useApiQuery<Page<AccountRow>>(canManage && can(P.accountsView) ? "/api/v1/access/accounts?limit=100" : null);
  const roles = catalog.data?.governance_roles ?? ["CLINIC_OWNER", "CLINIC_MANAGER", "DEPUTY_ADMIN", "RECEPTIONIST"];

  return (
    <div className="space-y-4" role="tabpanel" id="panel-governance" aria-labelledby="tab-governance">
      <p className="text-sm text-[var(--ds-text-muted)]">
        مالک و مدیر کلینیک فقط توسط مالک تغییر می‌کنند؛ معاون مدیر و پذیرش را مدیر نیز می‌تواند تعیین کند.
      </p>
      {canManage && accounts.data && (
        <div className="flex flex-wrap items-end gap-2">
          <SelectField label="افزودن نقش حاکمیتی به کاربر" value={pick} onChange={(e) => setPick(e.target.value)} data-testid="governance-pick">
            <option value="">انتخاب کاربر…</option>
            {accounts.data.items.map((a) => <option key={a.account_id} value={a.person_id}>{accountDisplayName(a)}</option>)}
          </SelectField>
          <Button
            variant="ghost"
            disabled={!pick}
            onClick={() => {
              const account = accounts.data?.items.find((a) => a.person_id === pick);
              if (account) setTarget({ person_id: account.person_id, name: accountDisplayName(account), roles: account.governance_roles });
            }}
            data-testid="governance-pick-open"
          >
            ویرایش نقش‌ها
          </Button>
        </div>
      )}
      <QueryBoundary loading={list.loading && !list.data} error={list.error} deniedWhat="مشاهدهٔ نقش‌های حاکمیتی" onRetry={list.reload}>
        {list.data && (
          <DataTable
            rows={list.data.items}
            rowKey={(r) => r.person_id}
            rowTestId="governance-row"
            empty={<EmptyState title="هنوز نقش حاکمیتی تعریف نشده است" />}
            columns={[
              { key: "name", header: "شخص", cell: (r) => `${r.first_name} ${r.last_name}` },
              { key: "roles", header: "نقش‌ها", cell: (r) => <span className="flex flex-wrap gap-1">{r.roles.map((g) => <StatusBadge key={g} tone="warn">{governanceLabel(g)}</StatusBadge>)}</span> },
              {
                key: "actions",
                header: "",
                cell: (r) =>
                  canManage ? (
                    <button type="button" className="text-[var(--ds-primary)] hover:underline" onClick={() => setTarget({ person_id: r.person_id, name: `${r.first_name} ${r.last_name}`, roles: r.roles })} data-testid="governance-edit">ویرایش</button>
                  ) : null,
              },
            ]}
          />
        )}
      </QueryBoundary>
      {target && (
        <GovernanceDialog
          key={target.person_id}
          target={target}
          roles={roles}
          onClose={() => setTarget(null)}
          onSaved={() => { setTarget(null); setPick(""); toast.success("نقش‌های حاکمیتی به‌روزرسانی شد"); setRefresh((v) => v + 1); }}
        />
      )}
    </div>
  );
}
