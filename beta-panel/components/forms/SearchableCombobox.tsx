"use client";

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

export type ComboboxOption = {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
};

type Props = {
  label: string;
  options: ComboboxOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
  emptyLabel?: string;
  testId?: string;
  /** Cap local filter list for small authorized catalogs. */
  maxVisible?: number;
};

/**
 * APG-style combobox: text filter + listbox, arrow/enter/escape, aria-activedescendant.
 * Suitable for small authorized catalogs (local search only).
 */
export function SearchableCombobox({
  label,
  options,
  value,
  onChange,
  placeholder = "جستجو و انتخاب…",
  hint,
  disabled,
  required,
  emptyLabel = "موردی یافت نشد",
  testId,
  maxVisible = 40,
}: Props) {
  const listId = useId();
  const inputId = useId();
  const noteId = hint ? `${inputId}-note` : undefined;
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const selected = options.find((o) => o.value === value) ?? null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = q
      ? options.filter(
          (o) =>
            o.label.toLowerCase().includes(q) ||
            (o.description ?? "").toLowerCase().includes(q) ||
            o.value.toLowerCase().includes(q),
        )
      : options;
    return base.slice(0, maxVisible);
  }, [options, query, maxVisible]);

  useEffect(() => {
    if (!open) return;
    function onDoc(ev: MouseEvent) {
      if (!rootRef.current?.contains(ev.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query, open]);

  function pick(next: string) {
    onChange(next);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) setOpen(true);
      else if (filtered.length) setActive((i) => (i + 1) % filtered.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (filtered.length) setActive((i) => (i - 1 + filtered.length) % filtered.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const hit = filtered[active];
      if (open && hit && !hit.disabled) pick(hit.value);
      else setOpen(true);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      setQuery("");
    } else if (event.key === "Home" && open && filtered.length) {
      event.preventDefault();
      setActive(0);
    } else if (event.key === "End" && open && filtered.length) {
      event.preventDefault();
      setActive(filtered.length - 1);
    }
  }

  const display = open ? query : selected?.label ?? "";

  return (
    <div ref={rootRef} className="relative block space-y-1 text-sm">
      <label className="ds-field-label" htmlFor={inputId}>
        {label}
        {required ? <span className="text-[var(--ds-danger)]"> *</span> : null}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && filtered[active] ? `${listId}-${active}` : undefined}
          aria-required={required || undefined}
          aria-describedby={noteId}
          disabled={disabled}
          className="ds-input pe-9"
          placeholder={selected && !open ? selected.label : placeholder}
          value={display}
          data-testid={testId}
          onFocus={() => {
            setOpen(true);
            setQuery("");
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={onKeyDown}
        />
        {value ? (
          <button
            type="button"
            className="absolute inset-y-0 end-0 grid w-9 place-items-center text-[var(--ds-text-muted)]"
            aria-label="پاک کردن انتخاب"
            disabled={disabled}
            onClick={() => {
              onChange("");
              setQuery("");
              setOpen(false);
            }}
            data-testid={testId ? `${testId}-clear` : undefined}
          >
            ×
          </button>
        ) : null}
      </div>
      {hint ? (
        <span id={noteId} className="ds-hint block">
          {hint}
        </span>
      ) : null}
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-[var(--ds-z-popover)] mt-1 max-h-56 w-full overflow-auto rounded-[var(--ds-radius-md)] border border-[var(--ds-border-strong)] bg-[var(--ds-surface)] py-1 shadow-[var(--ds-shadow)]"
          data-testid={testId ? `${testId}-list` : undefined}
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-[var(--ds-text-muted)]">{emptyLabel}</li>
          ) : (
            filtered.map((opt, index) => {
              const activeRow = index === active;
              const selectedRow = opt.value === value;
              return (
                <li
                  key={opt.value}
                  id={`${listId}-${index}`}
                  role="option"
                  aria-selected={selectedRow}
                  aria-disabled={opt.disabled || undefined}
                  className={`cursor-pointer px-3 py-2 ${activeRow ? "bg-[var(--ds-primary-soft)]" : ""} ${
                    opt.disabled ? "opacity-40" : ""
                  }`}
                  onMouseEnter={() => setActive(index)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    if (!opt.disabled) pick(opt.value);
                  }}
                >
                  <span className="block font-medium">{opt.label}</span>
                  {opt.description ? (
                    <span className="block text-xs text-[var(--ds-text-muted)]">{opt.description}</span>
                  ) : null}
                </li>
              );
            })
          )}
        </ul>
      ) : null}
      {/* Native select kept for progressive enhancement / Playwright selectOption compatibility */}
      <select
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        value={value}
        disabled={disabled}
        required={required}
        data-testid={testId ? `${testId}-native` : undefined}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">—</option>
        {options.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
