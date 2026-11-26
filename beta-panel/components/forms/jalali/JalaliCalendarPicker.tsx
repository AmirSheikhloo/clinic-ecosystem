"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import {
  JALALI_MONTHS,
  fromJalali,
  jalaliMonthLength,
  jalaliMonthStart,
  jalaliParts,
  shiftJalaliMonth,
} from "@/lib/calendar/jalali-grid";
import { JALALI_YEAR_MAX, JALALI_YEAR_MIN, clampToJalaliRange, monthCells } from "@/lib/calendar/jalali-input";
import { shiftTehranYmd, tehranTodayYmd } from "@/lib/tehran";

const WEEKDAY_LETTERS = ["ش", "ی", "د", "س", "چ", "پ", "ج"] as const;
const YEARS = Array.from({ length: JALALI_YEAR_MAX - JALALI_YEAR_MIN + 1 }, (_, i) => JALALI_YEAR_MIN + i);

type Props = {
  value: string;
  min?: string;
  max?: string;
  testId: string;
  onSelect: (ymd: string) => void;
  onClear?: () => void;
};

function inRange(ymd: string, min?: string, max?: string): boolean {
  return (!min || ymd >= min) && (!max || ymd <= max);
}

function dayLabel(ymd: string): string {
  const { jy, jm, jd } = jalaliParts(ymd);
  return `${jd} ${JALALI_MONTHS[jm - 1]} ${jy}`;
}

/** Keyboard-operable Jalali month grid (Saturday first). Values are Gregorian Tehran dates. */
export function JalaliCalendarPicker({ value, min, max, testId, onSelect, onClear }: Props) {
  const today = tehranTodayYmd();
  const [focusYmd, setFocusYmd] = useState(() => clampToJalaliRange(value || today));
  const needsFocus = useRef(true);
  const buttons = useRef<Map<string, HTMLButtonElement>>(new Map());
  const monthKey = jalaliMonthStart(focusYmd);
  const cells = useMemo(() => monthCells(monthKey), [monthKey]);
  const { jy, jm } = jalaliParts(focusYmd);

  useEffect(() => {
    if (!needsFocus.current) return;
    needsFocus.current = false;
    buttons.current.get(focusYmd)?.focus();
  }, [focusYmd]);

  function move(next: string) {
    needsFocus.current = true;
    setFocusYmd(clampToJalaliRange(next));
  }

  function onKeyDown(event: KeyboardEvent) {
    const steps: Record<string, number> = { ArrowRight: -1, ArrowLeft: 1, ArrowUp: -7, ArrowDown: 7 };
    if (event.key in steps) {
      event.preventDefault();
      move(shiftTehranYmd(focusYmd, steps[event.key]));
    } else if (event.key === "PageUp" || event.key === "PageDown") {
      event.preventDefault();
      move(shiftJalaliMonth(focusYmd, event.key === "PageUp" ? -1 : 1));
    }
  }

  function jumpTo(year: number, month: number) {
    const target = fromJalali(year, month, 1);
    const day = Math.min(jalaliParts(focusYmd).jd, jalaliMonthLength(target));
    setFocusYmd(fromJalali(year, month, day));
  }

  return (
    <div className="ds-cal" data-testid={`${testId}-picker`} onKeyDown={onKeyDown}>
      <div className="mb-2 flex items-center gap-1">
        <Button
          variant="subtle"
          size="sm"
          icon="chevronRight"
          aria-label="ماه قبل"
          onClick={() => setFocusYmd(shiftJalaliMonth(focusYmd, -1))}
          data-testid={`${testId}-prev`}
        />
        <select
          className="ds-input !min-h-[var(--ds-control-height-sm)] flex-1 !py-0 text-sm"
          aria-label="ماه"
          value={jm}
          onChange={(e) => jumpTo(jy, Number(e.target.value))}
          data-testid={`${testId}-month`}
        >
          {JALALI_MONTHS.map((name, index) => (
            <option key={name} value={index + 1}>
              {name}
            </option>
          ))}
        </select>
        <select
          className="ds-input !min-h-[var(--ds-control-height-sm)] !w-24 !py-0 text-sm"
          aria-label="سال"
          value={jy}
          onChange={(e) => jumpTo(Number(e.target.value), jm)}
          data-testid={`${testId}-year`}
        >
          {YEARS.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
        <Button
          variant="subtle"
          size="sm"
          icon="chevronLeft"
          aria-label="ماه بعد"
          onClick={() => setFocusYmd(shiftJalaliMonth(focusYmd, 1))}
          data-testid={`${testId}-next`}
        />
      </div>
      <div className="ds-cal-grid" aria-hidden="true">
        {WEEKDAY_LETTERS.map((letter) => (
          <span key={letter} className="ds-cal-weekday">
            {letter}
          </span>
        ))}
      </div>
      <div className="ds-cal-grid" role="group" aria-label={`${JALALI_MONTHS[jm - 1]} ${jy}`}>
        {cells.map((cell) => {
          const disabled = !inRange(cell.ymd, min, max);
          return (
            <button
              key={cell.ymd}
              ref={(node) => {
                if (node) buttons.current.set(cell.ymd, node);
                else buttons.current.delete(cell.ymd);
              }}
              type="button"
              className="ds-cal-day"
              data-ymd={cell.ymd}
              data-outside={!cell.inMonth}
              data-today={cell.ymd === today}
              data-testid={`${testId}-day-${cell.ymd}`}
              aria-label={dayLabel(cell.ymd)}
              aria-pressed={cell.ymd === value}
              aria-current={cell.ymd === today ? "date" : undefined}
              tabIndex={cell.ymd === focusYmd ? 0 : -1}
              disabled={disabled}
              onClick={() => onSelect(cell.ymd)}
            >
              {cell.jd}
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-[var(--ds-border)] pt-2">
        <Button
          variant="subtle"
          size="sm"
          disabled={!inRange(today, min, max)}
          onClick={() => onSelect(today)}
          data-testid={`${testId}-today`}
        >
          <Icon name="calendar" size="sm" />
          امروز
        </Button>
        {onClear ? (
          <Button variant="subtle" size="sm" onClick={onClear} data-testid={`${testId}-clear`}>
            پاک کردن
          </Button>
        ) : null}
      </div>
    </div>
  );
}
