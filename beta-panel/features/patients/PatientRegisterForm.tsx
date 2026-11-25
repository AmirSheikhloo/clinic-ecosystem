"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/forms/TextField";
import type { Patient } from "@/features/reception/types";

type Props = {
  firstName: string;
  lastName: string;
  birthDate: string;
  onFirstNameChange: (value: string) => void;
  onLastNameChange: (value: string) => void;
  onBirthDateChange: (value: string) => void;
  busy: boolean;
  onRegister: (event: FormEvent) => void;
  selected: Patient | null;
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
  selected,
}: Props) {
  return (
    <Card>
      <form onSubmit={onRegister} className="space-y-3">
        <h3 className="font-semibold">ثبت بیمار مصنوعی</h3>
        <div className="grid grid-cols-2 gap-2">
          <input
            className="ds-input"
            placeholder="نام"
            value={firstName}
            onChange={(e) => onFirstNameChange(e.target.value)}
            required
            data-testid="patients-first-name"
          />
          <input
            className="ds-input"
            placeholder="نام خانوادگی"
            value={lastName}
            onChange={(e) => onLastNameChange(e.target.value)}
            required
            data-testid="patients-last-name"
          />
        </div>
        <TextField
          type="date"
          label="تاریخ تولد (ورودی تقویمی استاندارد مرورگر)"
          value={birthDate}
          onChange={(e) => onBirthDateChange(e.target.value)}
          data-testid="patients-birth-date"
        />
        <Button type="submit" disabled={busy} data-testid="patients-register-submit">
          {busy ? "در حال ثبت…" : "ثبت بیمار"}
        </Button>
      </form>
      {selected && (
        <div className="mt-6 space-y-3 border-t border-[var(--ds-border)] pt-4">
          <p className="text-sm" data-testid="patients-selected">
            انتخاب‌شده: {selected.first_name} {selected.last_name}
          </p>
          <Link
            href="/desk"
            className="ds-btn ds-btn-primary"
            data-testid="patients-to-desk"
            onClick={() => {
              try {
                sessionStorage.setItem("ce_beta_selected_patient", JSON.stringify(selected));
              } catch {
                /* optional handoff only */
              }
            }}
          >
            ادامه در میز پذیرش
          </Link>
        </div>
      )}
    </Card>
  );
}
