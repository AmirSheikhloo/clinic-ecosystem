"use client";

import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import { formatCount } from "@/lib/format/numbers";
import { formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { appointmentStatusLabel } from "@/lib/format/status";
import { shiftTehranYmd, tehranTodayYmd } from "@/lib/client";
import type { SortKey } from "./types";

type Props = {
  date: string;
  onDateChange: (date: string) => void;
  visibleCount: number;
  sortKey: SortKey;
  onSortKeyChange: (key: SortKey) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  statuses: string[];
};

export function DayToolbar({
  date,
  onDateChange,
  visibleCount,
  sortKey,
  onSortKeyChange,
  statusFilter,
  onStatusFilterChange,
  statuses,
}: Props) {
  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">نوبت‌های روز</h2>
          <p className="text-[var(--ds-text-muted)]">
            جلالی با ارقام لاتین — {formatJalaliFromTehranYmd(date)} · تعداد:{" "}
            <span className="tabular-nums" data-testid="appointments-count">
              {formatCount(visibleCount)}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Button variant="ghost" onClick={() => onDateChange(tehranTodayYmd())}>
            امروز
          </Button>
          <Button variant="ghost" onClick={() => onDateChange(shiftTehranYmd(date, -1))}>
            روز قبل
          </Button>
          <Button variant="ghost" onClick={() => onDateChange(shiftTehranYmd(date, 1))}>
            روز بعد
          </Button>
          <TextField
            type="date"
            data-testid="appointments-date"
            label="تاریخ (مرز تهران)"
            value={date}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </div>
      </header>

      <div className="flex flex-wrap gap-3">
        <SelectField
          label="مرتب‌سازی"
          value={sortKey}
          onChange={(e) => onSortKeyChange(e.target.value as SortKey)}
        >
          <option value="time">زمان</option>
          <option value="patient">بیمار</option>
          <option value="service">خدمت</option>
        </SelectField>
        <SelectField
          label="وضعیت"
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
        >
          <option value="ALL">همه</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {appointmentStatusLabel(status)}
            </option>
          ))}
        </SelectField>
      </div>
    </>
  );
}
