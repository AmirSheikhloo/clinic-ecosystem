"use client";

import { useId, useState } from "react";
import { joinLocalDateTime, splitLocalDateTime } from "@/lib/calendar/jalali-input";
import { JalaliDateField } from "./JalaliDateField";
import { TimeField } from "./TimeField";

type Props = {
  label: string;
  /** `YYYY-MM-DDTHH:mm` Asia/Tehran wall clock, or empty until both parts are valid. */
  value: string;
  onChange: (local: string) => void;
  min?: string;
  max?: string;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
  testId: string;
};

/**
 * Appointment-style date and time. The emitted value keeps the former `datetime-local` shape so
 * existing Tehran-to-UTC conversion is unchanged; it is empty while either half is missing/invalid.
 */
export function JalaliDateTimeField({ label, value, onChange, min, max, hint, disabled, required, testId }: Props) {
  const groupId = useId();
  const [partial, setPartial] = useState({ date: "", time: "" });
  const current = splitLocalDateTime(value);
  const date = value ? current.date : partial.date;
  const time = value ? current.time : partial.time;

  function update(nextDate: string, nextTime: string) {
    const joined = joinLocalDateTime(nextDate, nextTime);
    setPartial(joined ? { date: "", time: "" } : { date: nextDate, time: nextTime });
    onChange(joined);
  }

  return (
    <div role="group" aria-labelledby={groupId} className="space-y-1">
      <span id={groupId} className="ds-field-label">
        {label}
      </span>
      <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-2">
        <JalaliDateField
          ariaLabel={`تاریخ ${label}`}
          value={date}
          min={min}
          max={max}
          disabled={disabled}
          required={required}
          testId={testId}
          onChange={(next) => update(next, time)}
        />
        <TimeField
          ariaLabel={`ساعت ${label}`}
          value={time}
          disabled={disabled}
          required={required}
          testId={`${testId}-time`}
          onChange={(next) => update(date, next)}
        />
      </div>
      {hint ? <p className="ds-hint">{hint}</p> : null}
    </div>
  );
}
