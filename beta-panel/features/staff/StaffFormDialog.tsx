"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { CheckboxField } from "@/components/forms/CheckboxField";
import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Collapsible } from "@/components/ui/Collapsible";
import { Dialog } from "@/components/ui/Dialog";
import { apiJson, type ApiFail } from "@/lib/api";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { LoginFields } from "./LoginFields";
import { STAFF_KINDS, staffKindLabel, type StaffRow } from "./types";

type Props = {
  /** null creates a new staff profile. */
  staff: StaffRow | null;
  canProvisionLogin: boolean;
  onClose: () => void;
  onSaved: (message: string) => void;
};

export function StaffFormDialog({ staff, canProvisionLogin, onClose, onSaved }: Props) {
  const editing = staff !== null;
  const [firstName, setFirstName] = useState(staff?.first_name ?? "");
  const [lastName, setLastName] = useState(staff?.last_name ?? "");
  const [kind, setKind] = useState(staff?.staff_kind ?? "RECEPTIONIST");
  const [council, setCouncil] = useState(staff?.medical_council_code ?? "");
  const [withLogin, setWithLogin] = useState(false);
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
    const fields = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      staff_kind: kind,
      medical_council_code: council.trim() || null,
    };
    const result = editing
      ? await apiJson<StaffRow>(`/api/v1/staff/${staff.staff_profile_id}`, {
          method: "PATCH",
          version: staff.aggregate_version,
          body: fields,
          fallbackMessage: "ذخیرهٔ تغییرات ناموفق بود",
        })
      : await (() => {
          const body = {
            ...fields,
            create_login_account: withLogin,
            login: withLogin ? { login_identifier: login.trim(), password } : undefined,
          };
          return apiJson<StaffRow>("/api/v1/staff", {
            method: "POST",
            body,
            idempotencyKey: idem.keyFor(body),
            fallbackMessage: "ثبت عضو ناموفق بود",
          });
        })();
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    idem.reset();
    onSaved(editing ? "اطلاعات عضو به‌روزرسانی شد" : "عضو جدید ثبت شد");
  }

  const stale = failure?.status === 412;

  return (
    <Dialog open placement="drawer" title={editing ? "ویرایش عضو" : "افزودن عضو"} description="پروفایل کارمندی؛ حساب ورود اختیاری و جداست." onClose={onClose} testId="staff-form-dialog">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3">
          <TextField label="نام" value={firstName} onChange={(e) => setFirstName(e.target.value)} required maxLength={120} data-testid="staff-first-name" />
          <TextField label="نام خانوادگی" value={lastName} onChange={(e) => setLastName(e.target.value)} required maxLength={120} data-testid="staff-last-name" />
          <SelectField label="نوع" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="staff-kind">
            {STAFF_KINDS.map((k) => (
              <option key={k} value={k}>{staffKindLabel(k)}</option>
            ))}
          </SelectField>
          <TextField label="کد نظام پزشکی (اختیاری)" value={council} onChange={(e) => setCouncil(e.target.value)} maxLength={64} data-testid="staff-council" />
        </div>
        {!editing && canProvisionLogin ? (
          <div className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3">
            <CheckboxField
              label="ایجاد حساب ورود به نرم‌افزار برای این عضو"
              hint="به‌صورت پیش‌فرض خاموش است. حساب بدون نقش ساخته می‌شود و دسترسی را بعداً در «کاربران و دسترسی» تعیین می‌کنید."
              checked={withLogin}
              onChange={(e) => setWithLogin(e.target.checked)}
              data-testid="staff-create-login"
            />
            <Collapsible open={withLogin}>
              <LoginFields idPrefix="new" active={withLogin} login={login} password={password} onLoginChange={setLogin} onPasswordChange={setPassword} />
            </Collapsible>
          </div>
        ) : null}
        {failure && (
          <Alert testId="staff-form-error">
            {stale ? "این پروفایل در این فاصله تغییر کرده است؛ پنجره را بسته و دوباره باز کنید." : failure.message}
          </Alert>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button type="submit" loading={busy} data-testid="staff-submit">
            {busy ? "در حال ذخیره…" : editing ? "ذخیره" : "ثبت عضو"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
