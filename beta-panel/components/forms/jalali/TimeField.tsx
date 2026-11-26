"use client";

import { useId, useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Popover } from "@/components/ui/Popover";
import { normalizeInputDigits } from "@/lib/format/digits";
import { parseTimeInput } from "@/lib/calendar/jalali-input";

type Props = {
  label?: string;
  ariaLabel?: string;
  /** `HH:mm` (24h, Asia/Tehran wall clock) or empty. */
  value: string;
  onChange: (time: string) => void;
  disabled?: boolean;
  required?: boolean;
  testId: string;
  className?: string;
};

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTES = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0"));

function autoColon(text: string): string {
  return /^\d{4}$/.test(text) ? `${text.slice(0, 2)}:${text.slice(2)}` : text;
}

/** 24-hour time entry with Latin digits; typed (`1430`) or picked from the clock popover. */
export function TimeField({ label, ariaLabel, value, onChange, disabled, required, testId, className = "" }: Props) {
  const inputId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const parsedDraft = draft === null ? null : parseTimeInput(draft);
  const shown =
    draft === null ? value : parsedDraft !== null ? (parsedDraft === value ? draft : value) : value ? value : draft;
  const invalid = draft !== null && draft.trim() !== "" && parsedDraft === null && !value;
  const [hour, minute] = value ? value.split(":") : ["", ""];

  function onInput(event: ChangeEvent<HTMLInputElement>) {
    const text = autoColon(normalizeInputDigits(event.target.value));
    setDraft(text);
    onChange(parseTimeInput(text) ?? "");
  }

  function pick(next: string, close: boolean) {
    onChange(next);
    setDraft(null);
    if (close) {
      setOpen(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className={`space-y-1 text-sm ${className}`.trim()}>
      {label ? (
        <label className="ds-field-label" htmlFor={inputId}>
          {label}
        </label>
      ) : null}
      <div ref={wrapRef} className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          dir="ltr"
          inputMode="numeric"
          autoComplete="off"
          className="ds-input text-right"
          placeholder="14:30"
          maxLength={5}
          value={shown}
          required={required}
          disabled={disabled}
          aria-label={label ? undefined : ariaLabel}
          aria-invalid={invalid ? true : undefined}
          data-testid={testId}
          onChange={onInput}
          onBlur={() => {
            if (draft !== null && parsedDraft !== null) setDraft(null);
          }}
        />
        <Button
          variant="ghost"
          icon="clock"
          disabled={disabled}
          aria-label="انتخاب ساعت"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
          data-testid={`${testId}-open`}
        />
        <Popover open={open} onClose={() => setOpen(false)} anchorRef={wrapRef} returnFocusRef={inputRef} label="انتخاب ساعت" role="dialog">
          <div className="w-60 space-y-3 p-3" data-testid={`${testId}-picker`}>
            <div>
              <p className="ds-hint mb-1">ساعت</p>
              <div className="grid grid-cols-6 gap-1">
                {HOURS.map((h) => (
                  <button
                    key={h}
                    type="button"
                    className="ds-cal-day !aspect-auto py-1"
                    aria-pressed={h === hour}
                    data-testid={`${testId}-hour-${h}`}
                    onClick={() => pick(`${h}:${minute || "00"}`, false)}
                  >
                    {h}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="ds-hint mb-1">دقیقه</p>
              <div className="grid grid-cols-6 gap-1">
                {MINUTES.map((m) => (
                  <button
                    key={m}
                    type="button"
                    className="ds-cal-day !aspect-auto py-1"
                    aria-pressed={m === minute}
                    data-testid={`${testId}-minute-${m}`}
                    onClick={() => pick(`${hour || "08"}:${m}`, true)}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Popover>
      </div>
      {invalid ? (
        <p className="ds-field-error" role="alert">
          ساعت معتبر نیست (نمونه: 14:30)
        </p>
      ) : null}
    </div>
  );
}
