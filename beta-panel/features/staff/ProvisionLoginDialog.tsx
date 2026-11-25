"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { LoginFields } from "./LoginFields";
import type { StaffRow } from "./types";

type Props = { staff: StaffRow; onClose: () => void; onSaved: (message: string) => void };

export function ProvisionLoginDialog({ staff, onClose, onSaved }: Props) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);
  const idem = useIdempotencyKey();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setFailure(null);
    const body = { login_identifier: login.trim(), password };
    const result = await apiJson(`/api/v1/staff/${staff.staff_profile_id}/login-account`, {
      method: "POST",
      body,
      idempotencyKey: idem.keyFor(body),
      fallbackMessage: "ایجاد حساب ورود ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    idem.reset();
    onSaved("حساب ورود بدون نقش ایجاد شد؛ نقش را از «کاربران و دسترسی» تخصیص دهید");
  }

  return (
    <Dialog open placement="drawer" title={`ایجاد حساب ورود — ${staff.first_name} ${staff.last_name}`} onClose={onClose} testId="provision-dialog">
      <form onSubmit={submit} className="space-y-4">
        <LoginFields idPrefix="prov" login={login} password={password} onLoginChange={setLogin} onPasswordChange={setPassword} />
        {failure && <Alert testId="provision-error">{failure.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button type="submit" loading={busy} data-testid="provision-submit">
            {busy ? "در حال ایجاد…" : "ایجاد حساب"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
