"use client";

import type { FormEvent } from "react";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { isValidNationalIdChecksum, normalizeNationalIdInput } from "@/lib/national-id";
import { tehranTodayYmd } from "@/lib/tehran";

type Props = {
  firstName: string;
  lastName: string;
  birthDate: string;
  nationalId: string;
  identityExceptionReason: string;
  onFirstNameChange: (value: string) => void;
  onLastNameChange: (value: string) => void;
  onBirthDateChange: (value: string) => void;
  onNationalIdChange: (value: string) => void;
  onIdentityExceptionReasonChange: (value: string) => void;
  busy: boolean;
  onRegister: (event: FormEvent) => void;
  onCancel: () => void;
};

export function PatientRegisterForm({
  firstName,
  lastName,
  birthDate,
  nationalId,
  identityExceptionReason,
  onFirstNameChange,
  onLastNameChange,
  onBirthDateChange,
  onNationalIdChange,
  onIdentityExceptionReasonChange,
  busy,
  onRegister,
  onCancel,
}: Props) {
  const digits = normalizeNationalIdInput(nationalId);
  const hasId = digits.length > 0;
  const idOk = !hasId || (digits.length === 10 && isValidNationalIdChecksum(digits));
  // Clause 755: missing official ID alone must not block creation; reason is encouraged, not hard-gated.
  const ready = firstName.trim() && lastName.trim() && idOk;

  return (
    <form onSubmit={onRegister} className="space-y-4" aria-label="ثبت بیمار جدید" data-testid="patients-register-form">
      <TextField label="نام" value={firstName} onChange={(e) => onFirstNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-first-name" />
      <TextField label="نام خانوادگی" value={lastName} onChange={(e) => onLastNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-last-name" />
      <TextField
        label="کد ملی (اختیاری)"
        value={nationalId}
        onChange={(e) => onNationalIdChange(normalizeNationalIdInput(e.target.value))}
        inputMode="numeric"
        maxLength={10}
        autoComplete="off"
        data-testid="patients-national-id"
        hint={hasId && !idOk ? "رقم کنترل کد ملی نامعتبر است" : "۱۰ رقم؛ صفرهای ابتدایی حفظ می‌شوند. ذخیرهٔ رمزنگاری‌شده در این نسخه هنوز فعال نیست."}
      />
      {!hasId ? (
        <TextField
          label="دلیل ثبت بدون شناسهٔ رسمی"
          value={identityExceptionReason}
          onChange={(e) => onIdentityExceptionReasonChange(e.target.value)}
          maxLength={200}
          autoComplete="off"
          data-testid="patients-identity-exception"
          hint="طبق بند ۷۵۵، نبود شناسه به‌تنهایی مانع ایجاد پرونده نیست؛ دلیل را ثبت کنید."
        />
      ) : null}
      <JalaliDateField label="تاریخ تولد (اختیاری)" value={birthDate} onChange={onBirthDateChange} max={tehranTodayYmd()} testId="patients-birth-date" allowClear />
      <p className="ds-hint">تلفن و اطلاعات بالینی در این نسخه ثبت نمی‌شود. کد ملی در صورت ورود فقط از نظر نحوی بررسی می‌شود.</p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={busy} disabled={!ready} data-testid="patients-register-submit">
          {busy ? "در حال ثبت…" : "ثبت بیمار"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>انصراف</Button>
      </div>
    </form>
  );
}
