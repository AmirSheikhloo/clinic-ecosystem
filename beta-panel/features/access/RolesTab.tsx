"use client";

import { useState } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { RoleFormDialog } from "./RoleFormDialog";
import type { PermissionCatalog, RoleRow } from "./types";

export function RolesTab() {
  const { can, permissions } = useSession();
  const toast = useToast();
  const [refresh, setRefresh] = useState(0);
  const [editing, setEditing] = useState<RoleRow | "new" | null>(null);
  const [deleting, setDeleting] = useState<RoleRow | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const roles = useApiQuery<{ items: RoleRow[] }>("/api/v1/access/roles", "بارگذاری نقش‌ها ناموفق بود", refresh);
  const catalog = useApiQuery<PermissionCatalog>("/api/v1/access/permissions", "بارگذاری مجوزها ناموفق بود");
  const canManage = can(P.rolesManage);
  const ungrantable = new Set((catalog.data?.items ?? []).map((p) => p.code).filter((code) => !permissions.has(code)));

  async function confirmDelete() {
    if (!deleting) return;
    const result = await apiJson(`/api/v1/access/roles/${deleting.role_id}`, { method: "DELETE", fallbackMessage: "حذف نقش ناموفق بود" });
    if (!result.ok) {
      setDeleteError(result.message);
      return;
    }
    setDeleting(null);
    toast.success("نقش حذف شد");
    setRefresh((v) => v + 1);
  }

  return (
    <div className="space-y-4" role="tabpanel" id="panel-roles" aria-labelledby="tab-roles">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-[var(--ds-text-muted)]">نقش مجموعه‌ای از مجوزهاست. مالک و مدیر کلینیک فقط از بخش «مالک و مدیران» تعیین می‌شوند.</p>
        {canManage ? <Button icon="plus" onClick={() => setEditing("new")} data-testid="role-add">نقش جدید</Button> : null}
      </div>
      <QueryBoundary loading={(roles.loading && !roles.data) || (catalog.loading && !catalog.data)} error={roles.error ?? catalog.error} deniedWhat="مشاهدهٔ نقش‌ها" onRetry={roles.reload}>
        {roles.data && catalog.data && (
          <DataTable
            rows={roles.data.items}
            rowKey={(r) => r.role_id}
            rowTestId="role-row"
            empty={<EmptyState icon="access" title="نقشی تعریف نشده است" />}
            columns={[
              { key: "name", header: "نقش", cell: (r) => <span><span className="font-medium">{r.role_name}</span> <span className="text-xs text-[var(--ds-text-muted)]" dir="ltr" title="کد نقش">{r.role_code}</span></span> },
              { key: "type", header: "نوع", cell: (r) => <StatusBadge>{r.is_system_defined ? "سیستمی" : "سفارشی"}</StatusBadge> },
              { key: "perms", header: "مجوزها", cell: (r) => formatCount(r.permissions.length), className: "tabular-nums" },
              { key: "members", header: "اعضا", cell: (r) => formatCount(r.member_count), className: "tabular-nums" },
              {
                key: "actions",
                header: "",
                cell: (r) =>
                  canManage ? (
                    <span className="inline-flex justify-end gap-1">
                      <Button variant="subtle" size="sm" onClick={() => setEditing(r)} data-testid="role-edit">مجوزها</Button>
                      {!r.is_system_defined && r.member_count === 0 ? (
                        <Button variant="danger" size="sm" onClick={() => { setDeleteError(null); setDeleting(r); }} data-testid="role-delete">حذف</Button>
                      ) : null}
                    </span>
                  ) : null,
              },
            ]}
          />
        )}
      </QueryBoundary>
      {editing && catalog.data && (
        <RoleFormDialog
          role={editing === "new" ? null : editing}
          catalog={catalog.data.items}
          ungrantable={ungrantable}
          onClose={() => setEditing(null)}
          onSaved={(message) => { setEditing(null); toast.success(message); setRefresh((v) => v + 1); }}
        />
      )}
      {deleting ? (
        <ConfirmDialog
          open
          tone="danger"
          title="حذف نقش"
          confirmLabel="حذف نقش"
          testId="role-delete-dialog"
          onCancel={() => setDeleting(null)}
          onConfirm={() => void confirmDelete()}
        >
          <p>نقش «{deleting.role_name}» حذف شود؟ این کار برگشت‌پذیر نیست و در گزارش ممیزی ثبت می‌شود.</p>
          {deleteError ? <Alert>{deleteError}</Alert> : null}
        </ConfirmDialog>
      ) : null}
    </div>
  );
}
