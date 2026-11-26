"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { PermissionPicker } from "./PermissionPicker";
import type { PermissionDef, RoleRow } from "./types";

type Props = {
  role: RoleRow | null;
  catalog: PermissionDef[];
  ungrantable: ReadonlySet<string>;
  onClose: () => void;
  onSaved: (message: string) => void;
};

export function RoleFormDialog({ role, catalog, ungrantable, onClose, onSaved }: Props) {
  const editing = role !== null;
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [permissions, setPermissions] = useState<string[]>(role?.permissions ?? []);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);

  const needsConfirm = editing && role.member_count > 0;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (needsConfirm) setConfirming(true);
    else void submit();
  }

  async function submit() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    const result = editing
      ? await apiJson(`/api/v1/access/roles/${role.role_id}/permissions`, {
          method: "PUT",
          body: { permissions },
          fallbackMessage: "ذخیرهٔ مجوزها ناموفق بود",
        })
      : await apiJson("/api/v1/access/roles", {
          method: "POST",
          body: { role_code: code.trim().toUpperCase(), role_name: name.trim(), permissions },
          fallbackMessage: "ایجاد نقش ناموفق بود",
        });
    setBusy(false);
    setConfirming(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    onSaved(editing ? "مجوزهای نقش به‌روزرسانی شد" : "نقش جدید ایجاد شد");
  }

  return (
    <Dialog open placement="drawer" size="lg" title={editing ? `مجوزهای نقش — ${role.role_name}` : "نقش جدید"} onClose={onClose} testId="role-dialog">
      <form onSubmit={onSubmit} className="space-y-4">
        {!editing && (
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField label="کد نقش (حروف بزرگ انگلیسی، رقم و _)" value={code} onChange={(e) => setCode(e.target.value)} required maxLength={64} dir="ltr" data-testid="role-code" />
            <TextField label="عنوان نقش" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} data-testid="role-name" />
          </div>
        )}
        <PermissionPicker catalog={catalog} selected={permissions} onChange={setPermissions} disabledCodes={ungrantable} />
        {ungrantable.size > 0 && (
          <p className="ds-hint">
            مجوزهایی که خودتان ندارید قابل اعطا نیستند (جلوگیری از افزایش سطح دسترسی).
          </p>
        )}
        {failure && <Alert testId="role-error">{failure.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button type="submit" loading={busy} data-testid="role-submit">ذخیره</Button>
        </div>
      </form>
      <ConfirmDialog
        open={confirming}
        title="تأیید تغییر مجوزهای نقش"
        confirmLabel="تأیید و ذخیره"
        busy={busy}
        testId="role-apply-dialog"
        onCancel={() => setConfirming(false)}
        onConfirm={() => void submit()}
      >
        <p>این نقش به {role?.member_count} کاربر اختصاص دارد و تغییر مجوزها فوراً برای همه آن‌ها اعمال می‌شود.</p>
      </ConfirmDialog>
    </Dialog>
  );
}
