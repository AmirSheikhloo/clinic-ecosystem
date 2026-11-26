"use client";

import { useRef, type KeyboardEvent } from "react";

export type SegmentedOption<T extends string> = { value: T; label: string; testId?: string };

type Props<T extends string> = {
  label: string;
  value: T;
  options: readonly SegmentedOption<T>[];
  onChange: (value: T) => void;
  testId?: string;
  disabled?: boolean;
};

/** Single-choice radio group with roving tabindex and arrow-key navigation (RTL-aware). */
export function SegmentedControl<T extends string>({ label, value, options, onChange, testId, disabled = false }: Props<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent, index: number) {
    const rtl = document.documentElement.dir === "rtl";
    const forward = event.key === (rtl ? "ArrowLeft" : "ArrowRight") || event.key === "ArrowDown";
    const backward = event.key === (rtl ? "ArrowRight" : "ArrowLeft") || event.key === "ArrowUp";
    if (!forward && !backward) return;
    event.preventDefault();
    const next = (index + (forward ? 1 : -1) + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  }

  return (
    <div role="radiogroup" aria-label={label} className="ds-segmented" data-testid={testId}>
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            disabled={disabled}
            data-testid={option.testId}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
