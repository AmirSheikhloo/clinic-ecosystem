"use client";

import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { DataTable } from "@/components/tables/DataTable";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useApiQuery } from "@/lib/use-api-query";
import {
  accountDisplayName,
  governanceLabel,
  type AccountRow,
  type EffectivePermission,
  type PermissionCatalog,
  type RoleRow,
  CATEGORY_LABEL,
} from "./types";

type Props = { account: AccountRow; onClose: () => void };

export function EffectivePermissionsDialog({ account, onClose }: Props) {
  const effective = useApiQuery<{ items: EffectivePermission[] }>(
    `/api/v1/access/accounts/${account.account_id}/effective-permissions`,
    "بارگذاری دسترسی مؤثر ناموفق بود",
  );
  const catalog = useApiQuery<PermissionCatalog>("/api/v1/access/permissions");
  const roles = useApiQuery<{ items: RoleRow[] }>("/api/v1/access/roles");
  const labels = new Map((catalog.data?.items ?? []).map((p) => [p.code, p.label_fa]));
  const categories = new Map((catalog.data?.items ?? []).map((p) => [p.code, CATEGORY_LABEL[p.category] ?? p.category]));
  const roleNames = new Map((roles.data?.items ?? []).map((r) => [r.role_code, r.role_name]));

  return (
    <Dialog open placement="drawer" size="lg" title={`دسترسی مؤثر — ${accountDisplayName(account)}`} onClose={onClose} testId="effective-dialog">
      <p className="mb-3 text-sm text-[var(--ds-text-muted)]">
        مجموع مجوزهای حاصل از نقش‌های تخصیص‌یافته. نقش حاکمیتی
        {account.governance_roles.length
          ? ` (${account.governance_roles.map(governanceLabel).join("، ")})`
          : " (ندارد)"}
        {" "}خودکار مجوز اضافه‌ای نمی‌دهد.
      </p>
      <QueryBoundary loading={effective.loading} error={effective.error} deniedWhat="مشاهدهٔ دسترسی مؤثر" onRetry={effective.reload}>
        {effective.data && (
          <DataTable
            rows={effective.data.items}
            rowKey={(r) => r.permission_code}
            rowTestId="effective-row"
            empty={<EmptyState title="این حساب هیچ مجوزی ندارد" description="برای فعال‌سازی دسترسی، نقش تخصیص دهید." />}
            columns={[
              { key: "perm", header: "مجوز", cell: (r) => <span title={r.permission_code}>{labels.get(r.permission_code) ?? "مجوز ناشناخته"}</span> },
              { key: "category", header: "بخش", cell: (r) => categories.get(r.permission_code) ?? "—" },
              { key: "via", header: "از طریق نقش", cell: (r) => <span className="flex flex-wrap gap-1">{r.via_roles.map((code) => <StatusBadge key={code}>{roleNames.get(code) ?? code}</StatusBadge>)}</span> },
            ]}
          />
        )}
      </QueryBoundary>
    </Dialog>
  );
}
