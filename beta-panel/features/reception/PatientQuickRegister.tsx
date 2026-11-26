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
  registering: boolean;
  onRegister: (event: FormEvent) => void;
};

export function PatientQuickRegister({
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
  registering,
  onRegister,
}: Props) {
  const digits = normalizeNationalIdInput(nationalId);
  const hasId = digits.length > 0;
  const idOk = !hasId || (digits.length === 10 && isValidNationalIdChecksum(digits));
  // Clause 755: missing official ID alone must not block creation; reason is encouraged, not hard-gated.
  const ready = firstName.trim().length > 0 && lastName.trim().length > 0 && idOk;
  return (
    <form onSubmit={onRegister} className="space-y-3 border-t border-[var(--ds-border)] pt-4" aria-label="ثبت بیمار جدید">
      <div>
        <h3 className="ds-section-title">ثبت بیمار جدید</h3>
        <p className="ds-hint">فقط اطلاعات هویتی اولیه ثبت می‌شود؛ پس از ثبت، بیمار خودکار انتخاب می‌شود.</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TextField label="نام" data-testid="patient-first-name" value={firstName} onChange={(e) => onFirstNameChange(e.target.value)} required maxLength={100} autoComplete="off" />
        <TextField label="نام خانوادگی" data-testid="patient-last-name" value={lastName} onChange={(e) => onLastNameChange(e.target.value)} required maxLength={100} autoComplete="off" />
      </div>
      <TextField
        label="کد ملی (اختیاری)"
        data-testid="patient-national-id"
        value={nationalId}
        onChange={(e) => onNationalIdChange(normalizeNationalIdInput(e.target.value))}
        inputMode="numeric"
        maxLength={10}
        autoComplete="off"
        hint={hasId && !idOk ? "رقم کنترل کد ملی نامعتبر است" : undefined}
      />
      {!hasId ? (
        <TextField
          label="دلیل ثبت بدون شناسهٔ رسمی"
          data-testid="patient-identity-exception"
          value={identityExceptionReason}
          onChange={(e) => onIdentityExceptionReasonChange(e.target.value)}
          maxLength={200}
          autoComplete="off"
        />
      ) : null}
      <JalaliDateField
        label="تاریخ تولد (اختیاری)"
        value={birthDate}
        onChange={onBirthDateChange}
        max={tehranTodayYmd()}
        testId="patient-birth-date"
        allowClear
      />
      <Button type="submit" variant="ghost" icon="plus" loading={registering} disabled={!ready} data-testid="patient-register-submit" className="w-full">
        ثبت و انتخاب بیمار
      </Button>
    </form>
  );
}
