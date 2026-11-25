"use client";

import { useId, useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Popover } from "@/components/ui/Popover";
import { normalizeInputDigits } from "@/lib/format/digits";
import { formatJalaliInput, parseJalaliInput } from "@/lib/calendar/jalali-input";
import { JalaliCalendarPicker } from "./JalaliCalendarPicker";

export type JalaliDateFieldProps = {
  label?: string;
  /** Gregorian `YYYY-MM-DD` (Asia/Tehran) or empty. */
  value: string;
  onChange: (ymd: string) => void;
  min?: string;
  max?: string;
  required?: boolean;
  disabled?: boolean;
  hint?: string;
  error?: string;
  testId: string;
  /** Accessible name when no visible label is rendered. */
  ariaLabel?: string;
  allowClear?: boolean;
  className?: string;
};

function autoSlash(text: string): string {
  return /^\d{8}$/.test(text) ? `${text.slice(0, 4)}/${text.slice(4, 6)}/${text.slice(6)}` : text;
}

/**
 * The single date control for the application: Jalali text entry (Latin digits) plus a calendar popover.
 * The API contract stays Gregorian; conversion happens only here.
 */
export function JalaliDateField({
  label,
  value,
  onChange,
  min,
  max,
  required,
  disabled,
  hint,
  error,
  testId,
  ariaLabel,
  allowClear = false,
  className = "",
}: JalaliDateFieldProps) {
  const inputId = useId();
  const noteId = `${inputId}-note`;
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const allowed = (ymd: string) => (!min || ymd >= min) && (!max || ymd <= max);
  const parsedDraft = draft === null ? null : parseJalaliInput(draft);
  const draftOutOfRange = parsedDraft !== null && !allowed(parsedDraft);
  let shown: string;
  if (draft === null) shown = formatJalaliInput(value);
  else if (draftOutOfRange) shown = draft;
  else if (parsedDraft !== null) shown = parsedDraft === value ? draft : formatJalaliInput(value);
  else shown = value ? formatJalaliInput(value) : draft;
  const rangeError = draftOutOfRange || (value && !allowed(value)) ? "تاریخ خارج از بازهٔ مجاز است" : undefined;
  const typedInvalid = draft !== null && draft.trim() !== "" && parsedDraft === null && !value;
  const message = error ?? rangeError ?? (typedInvalid ? "تاریخ شمسی معتبر نیست (نمونه: 1405/09/04)" : undefined);

  function commit(next: string) {
    onChange(next);
    setDraft(null);
    setOpen(false);
    inputRef.current?.focus();
  }

  function onInput(event: ChangeEvent<HTMLInputElement>) {
    const text = autoSlash(normalizeInputDigits(event.target.value));
    setDraft(text);
    const parsed = parseJalaliInput(text);
    onChange(parsed && allowed(parsed) ? parsed : "");
  }

  return (
    <div className={`space-y-1 text-sm ${className}`.trim()}>
      {label ? (
        <label className="ds-field-label" htmlFor={inputId}>
          {label}
        </label>
      ) : null}
      <div ref={wrapRef} className="relative flex items-center gap-1.5">
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          dir="ltr"
          inputMode="numeric"
          autoComplete="off"
          className="ds-input text-right"
          placeholder="1405/09/04"
          maxLength={10}
          value={shown}
          required={required}
          disabled={disabled}
          aria-label={label ? undefined : ariaLabel}
          aria-describedby={message || hint ? noteId : undefined}
          aria-invalid={message ? true : undefined}
          aria-haspopup="dialog"
          aria-expanded={open}
          data-testid={testId}
          onChange={onInput}
          onBlur={() => {
            if (draft !== null && parsedDraft !== null && !draftOutOfRange) setDraft(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" && !disabled) {
              event.preventDefault();
              setOpen(true);
            }
          }}
        />
        <Button
          variant="ghost"
          icon="calendar"
          disabled={disabled}
          aria-label={label ? `انتخاب ${label} از تقویم` : "انتخاب از تقویم"}
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
          data-testid={`${testId}-open`}
        />
        <Popover
          open={open}
          onClose={() => setOpen(false)}
          anchorRef={wrapRef}
          returnFocusRef={inputRef}
          label="انتخاب تاریخ شمسی"
          role="dialog"
          testId={`${testId}-popover`}
        >
          <JalaliCalendarPicker
            value={value}
            min={min}
            max={max}
            testId={testId}
            onSelect={commit}
            onClear={allowClear ? () => commit("") : undefined}
          />
        </Popover>
      </div>
      {message ? (
        <p id={noteId} className="ds-field-error" role="alert">
          {message}
        </p>
      ) : hint ? (
        <p id={noteId} className="ds-hint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
