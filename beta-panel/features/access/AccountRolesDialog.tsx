"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { CheckboxField } from "@/components/forms/CheckboxField";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api-query";
import { accountDisplayName, toggleInSet, type AccountRow, type RoleRow } from "./types";

type Props = { account: AccountRow; onClose: () => void; onSaved: (message: string) => void };

export function AccountRolesDialog({ account, onClose, onSaved }: Props) {
  const roles = useApiQuery<{ items: RoleRow[] }>("/api/v1/access/roles", "بارگذاری نقش‌ها ناموفق بود");
  const [selected, setSelected] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);

  const items = roles.data?.items ?? [];
  const current = selected ?? items.filter((r) => account.roles.includes(r.role_code)).map((r) => r.role_id);

  async function save() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    const result = await apiJson(`/api/v1/access/accounts/${account.account_id}/roles`, {
      method: "PUT",
      body: { role_ids: current },
      fallbackMessage: "تخصیص نقش ناموفق بود",
    });
    setBusy(false);
    setConfirming(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    onSaved("نقش‌های کاربر به‌روزرسانی شد");
  }

  return (
    <Dialog open placement="drawer" title={`نقش‌های ${accountDisplayName(account)}`} description="مجوزهای کاربر مجموع مجوزهای نقش‌های انتخاب‌شده است." onClose={onClose} testId="account-roles-dialog">
      <QueryBoundary loading={roles.loading} error={roles.error} deniedWhat="مشاهدهٔ فهرست نقش‌ها" onRetry={roles.reload}>
        <div className="space-y-3">
          {items.length === 0 && <p className="text-sm text-[var(--ds-text-muted)]">نقشی تعریف نشده است.</p>}
          {items.map((role) => (
            <CheckboxField
              key={role.role_id}
              id={`role-${role.role_id}`}
              label={role.role_name}
              hint={`${role.permissions.length} مجوز${role.is_system_defined ? " — نقش سیستمی" : ""}`}
              checked={current.includes(role.role_id)}
              onChange={(e) => setSelected(toggleInSet(current, role.role_id, e.target.checked))}
              data-testid={`assign-role-${role.role_code}`}
            />
          ))}
          <p className="text-xs text-[var(--ds-text-muted)]">
            نقش‌های دارای مجوز فراتر از سطح شما یا نقش‌های حاکمیتی قابل تخصیص نیستند؛ سرور این محدودیت را اعمال می‌کند.
          </p>
          {failure && <Alert testId="account-roles-error">{failure.message}</Alert>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>انصراف</Button>
            <Button loading={busy} onClick={() => setConfirming(true)} data-testid="account-roles-save">ذخیره نقش‌ها</Button>
          </div>
        </div>
      </QueryBoundary>
      <ConfirmDialog
        open={confirming}
        title="تأیید تغییر نقش‌ها"
        confirmLabel="تأیید و ذخیره"
        busy={busy}
        testId="account-roles-apply-dialog"
        onCancel={() => setConfirming(false)}
        onConfirm={() => void save()}
      >
        <p>دسترسی «{accountDisplayName(account)}» بلافاصله پس از ذخیره تغییر می‌کند. نقش‌های انتخاب‌شده: {items.filter((r) => current.includes(r.role_id)).map((r) => r.role_name).join("، ") || "هیچ"}.</p>
      </ConfirmDialog>
    </Dialog>
  );
}
