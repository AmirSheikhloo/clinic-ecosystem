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
  registering: boolean;
  onRegister: (event: FormEvent) => void;
};

export function PatientQuickRegister({
  firstName,
  lastName,
  birthDate,
  onFirstNameChange,
  onLastNameChange,
  onBirthDateChange,
  registering,
  onRegister,
}: Props) {
  const ready = firstName.trim().length > 0 && lastName.trim().length > 0;
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
