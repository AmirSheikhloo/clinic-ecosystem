"use client";

import type { FormEvent } from "react";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { SegmentedControl } from "@/components/forms/SegmentedControl";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import type { IdentityType } from "@/features/patients/PatientRegisterForm";
import { isValidNationalIdChecksum, normalizeNationalIdInput } from "@/lib/national-id";
import { tehranTodayYmd } from "@/lib/tehran";

const IDENTITY_OPTIONS = [
  { value: "IR_NATIONAL_ID" as const, label: "کد ملی", testId: "desk-identity-national" },
  { value: "FOREIGN_FIDA_CODE" as const, label: "فیدا", testId: "desk-identity-fida" },
  { value: "FOREIGN_PASSPORT" as const, label: "گذرنامه", testId: "desk-identity-passport" },
  { value: "EXCEPTION" as const, label: "بدون شناسه", testId: "desk-identity-exception" },
];

type Props = {
  firstName: string;
  lastName: string;
  birthDate: string;
  nationalId: string;
  phone: string;
  identityType: IdentityType;
  identityExceptionReason: string;
  onFirstNameChange: (value: string) => void;
  onLastNameChange: (value: string) => void;
  onBirthDateChange: (value: string) => void;
  onNationalIdChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onIdentityTypeChange: (value: IdentityType) => void;
  onIdentityExceptionReasonChange: (value: string) => void;
  registering: boolean;
  onRegister: (event: FormEvent) => void;
};

export function PatientQuickRegister({
  firstName,
  lastName,
  birthDate,
  nationalId,
  phone,
  identityType,
  identityExceptionReason,
  onFirstNameChange,
  onLastNameChange,
  onBirthDateChange,
  onNationalIdChange,
  onPhoneChange,
  onIdentityTypeChange,
  onIdentityExceptionReasonChange,
  registering,
  onRegister,
}: Props) {
  const digits = normalizeNationalIdInput(nationalId);
  const needsId = identityType !== "EXCEPTION";
  const idOk =
    !needsId ||
    (identityType === "IR_NATIONAL_ID"
      ? digits.length === 10 && isValidNationalIdChecksum(digits)
      : nationalId.trim().length >= 3);
  const exceptionOk = identityType !== "EXCEPTION" || identityExceptionReason.trim().length > 0;
  const ready = firstName.trim().length > 0 && lastName.trim().length > 0 && idOk && exceptionOk;

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
      <SegmentedControl
        label="نوع شناسه"
        value={identityType}
        options={IDENTITY_OPTIONS}
        onChange={onIdentityTypeChange}
        testId="desk-identity-type"
      />
      {identityType === "EXCEPTION" ? (
        <TextField
          label="دلیل ثبت بدون شناسهٔ رسمی"
          data-testid="patient-identity-exception"
          value={identityExceptionReason}
          onChange={(e) => onIdentityExceptionReasonChange(e.target.value)}
          maxLength={200}
          required
          autoComplete="off"
        />
      ) : (
        <TextField
          label={identityType === "IR_NATIONAL_ID" ? "کد ملی" : identityType === "FOREIGN_FIDA_CODE" ? "کد فیدا" : "شماره گذرنامه"}
          data-testid="patient-national-id"
          value={nationalId}
          onChange={(e) =>
            onNationalIdChange(
              identityType === "IR_NATIONAL_ID" ? normalizeNationalIdInput(e.target.value) : e.target.value,
            )
          }
          inputMode={identityType === "IR_NATIONAL_ID" ? "numeric" : "text"}
          maxLength={identityType === "IR_NATIONAL_ID" ? 10 : 40}
          autoComplete="off"
          hint={identityType === "IR_NATIONAL_ID" && digits.length > 0 && !idOk ? "رقم کنترل کد ملی نامعتبر است" : undefined}
        />
      )}
      <TextField
        label="تلفن (اختیاری)"
        data-testid="patient-phone"
        value={phone}
        onChange={(e) => onPhoneChange(e.target.value)}
        inputMode="tel"
        maxLength={20}
        autoComplete="off"
      />
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
