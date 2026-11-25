"use client";

import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { DataTable } from "@/components/tables/DataTable";
import { Dialog } from "@/components/ui/Dialog";
import { useApiQuery } from "@/lib/use-api-query";
import {
  accountDisplayName,
  governanceLabel,
  type AccountRow,
  type EffectivePermission,
  type PermissionCatalog,
} from "./types";

type Props = { account: AccountRow; onClose: () => void };

export function EffectivePermissionsDialog({ account, onClose }: Props) {
  const effective = useApiQuery<{ items: EffectivePermission[] }>(
    `/api/v1/access/accounts/${account.account_id}/effective-permissions`,
    "بارگذاری دسترسی مؤثر ناموفق بود",
  );
  const catalog = useApiQuery<PermissionCatalog>("/api/v1/access/permissions");
  const labels = new Map((catalog.data?.items ?? []).map((p) => [p.code, p.label_fa]));

  return (
    <Dialog open size="lg" title={`دسترسی مؤثر — ${accountDisplayName(account)}`} onClose={onClose} testId="effective-dialog">
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
              { key: "perm", header: "مجوز", cell: (r) => labels.get(r.permission_code) ?? r.permission_code },
              { key: "code", header: "کد", cell: (r) => <span dir="ltr" className="text-xs">{r.permission_code}</span> },
              { key: "via", header: "از طریق نقش", cell: (r) => r.via_roles.join("، ") },
            ]}
          />
        )}
      </QueryBoundary>
    </Dialog>
  );
}
