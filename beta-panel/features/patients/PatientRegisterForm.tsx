"use client";

import type { FormEvent } from "react";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { tehranTodayYmd } from "@/lib/tehran";

type Props = {
  firstName: string;
  lastName: string;
  birthDate: string;
  onFirstNameChange: (value: string) => void;
  onLastNameChange: (value: string) => void;
  onBirthDateChange: (value: string) => void;
  busy: boolean;
  onRegister: (event: FormEvent) => void;
  onCancel: () => void;
};

export function PatientRegisterForm({
  firstName,
  lastName,
  birthDate,
  onFirstNameChange,
  onLastNameChange,
  onBirthDateChange,
  busy,
  onRegister,
  onCancel,
}: Props) {
  return (
    <form onSubmit={onRegister} className="space-y-4" aria-label="ثبت بیمار جدید" data-testid="patients-register-form">
      <TextField label="نام" value={firstName} onChange={(e) => onFirstNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-first-name" />
      <TextField label="نام خانوادگی" value={lastName} onChange={(e) => onLastNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-last-name" />
      <JalaliDateField label="تاریخ تولد (اختیاری)" value={birthDate} onChange={onBirthDateChange} max={tehranTodayYmd()} testId="patients-birth-date" allowClear />
      <p className="ds-hint">تلفن، شناسهٔ رسمی و اطلاعات بالینی در این نسخه ثبت نمی‌شود.</p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={busy} disabled={!firstName.trim() || !lastName.trim()} data-testid="patients-register-submit">
          {busy ? "در حال ثبت…" : "ثبت بیمار"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>انصراف</Button>
      </div>
    </form>
  );
}
