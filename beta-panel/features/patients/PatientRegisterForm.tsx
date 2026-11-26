"use client";

import type { FormEvent } from "react";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { SegmentedControl } from "@/components/forms/SegmentedControl";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { isValidNationalIdChecksum, normalizeNationalIdInput } from "@/lib/national-id";
import { tehranTodayYmd } from "@/lib/tehran";

export type IdentityType = "IR_NATIONAL_ID" | "FOREIGN_FIDA_CODE" | "FOREIGN_PASSPORT" | "EXCEPTION";

const IDENTITY_OPTIONS = [
  { value: "IR_NATIONAL_ID" as const, label: "کد ملی", testId: "identity-type-national" },
  { value: "FOREIGN_FIDA_CODE" as const, label: "فیدا", testId: "identity-type-fida" },
  { value: "FOREIGN_PASSPORT" as const, label: "گذرنامه", testId: "identity-type-passport" },
  { value: "EXCEPTION" as const, label: "بدون شناسه", testId: "identity-type-exception" },
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
  busy: boolean;
  onRegister: (event: FormEvent) => void;
  onCancel: () => void;
};

export function PatientRegisterForm({
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
  busy,
  onRegister,
  onCancel,
}: Props) {
  const digits = normalizeNationalIdInput(nationalId);
  const needsId = identityType !== "EXCEPTION";
  const idOk =
    !needsId ||
    (identityType === "IR_NATIONAL_ID"
      ? digits.length === 10 && isValidNationalIdChecksum(digits)
      : nationalId.trim().length >= 3);
  const exceptionOk = identityType !== "EXCEPTION" || identityExceptionReason.trim().length > 0;
  const ready = firstName.trim() && lastName.trim() && idOk && exceptionOk;

  return (
    <form onSubmit={onRegister} className="space-y-4" aria-label="ثبت بیمار جدید" data-testid="patients-register-form">
      <TextField label="نام" value={firstName} onChange={(e) => onFirstNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-first-name" />
      <TextField label="نام خانوادگی" value={lastName} onChange={(e) => onLastNameChange(e.target.value)} required maxLength={100} autoComplete="off" data-testid="patients-last-name" />
      <SegmentedControl
        label="نوع شناسه"
        value={identityType}
        options={IDENTITY_OPTIONS}
        onChange={onIdentityTypeChange}
        testId="patients-identity-type"
      />
      {identityType === "EXCEPTION" ? (
        <TextField
          label="دلیل ثبت بدون شناسهٔ رسمی"
          value={identityExceptionReason}
          onChange={(e) => onIdentityExceptionReasonChange(e.target.value)}
          maxLength={200}
          required
          autoComplete="off"
          data-testid="patients-identity-exception"
          hint="شناسه جعلی ساخته نمی‌شود؛ دلیل الزامی است."
        />
      ) : (
        <TextField
          label={identityType === "IR_NATIONAL_ID" ? "کد ملی" : identityType === "FOREIGN_FIDA_CODE" ? "کد فیدا" : "شماره گذرنامه"}
          value={nationalId}
          onChange={(e) =>
            onNationalIdChange(
              identityType === "IR_NATIONAL_ID" ? normalizeNationalIdInput(e.target.value) : e.target.value,
            )
          }
          inputMode={identityType === "IR_NATIONAL_ID" ? "numeric" : "text"}
          maxLength={identityType === "IR_NATIONAL_ID" ? 10 : 40}
          autoComplete="off"
          data-testid="patients-national-id"
          hint={
            identityType === "IR_NATIONAL_ID" && digits.length > 0 && !idOk
              ? "رقم کنترل کد ملی نامعتبر است"
              : "مقدار رمزنگاری‌شده ذخیره می‌شود؛ فقط نمایش پوشیده در پاسخ می‌آید."
          }
        />
      )}
      <TextField
        label="تلفن (اختیاری)"
        value={phone}
        onChange={(e) => onPhoneChange(e.target.value)}
        inputMode="tel"
        maxLength={20}
        autoComplete="off"
        data-testid="patients-phone"
        hint="مثال: ۰۹۱۲۱۲۳۴۵۶۷ — اعضای خانواده می‌توانند یک شماره مشترک داشته باشند."
      />
      <JalaliDateField label="تاریخ تولد (اختیاری)" value={birthDate} onChange={onBirthDateChange} max={tehranTodayYmd()} testId="patients-birth-date" allowClear />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={busy} disabled={!ready} data-testid="patients-register-submit">
          {busy ? "در حال ثبت…" : "ثبت بیمار"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>انصراف</Button>
      </div>
    </form>
  );
}
