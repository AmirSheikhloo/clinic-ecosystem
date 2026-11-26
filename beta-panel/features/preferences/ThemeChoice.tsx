"use client";

import { useRef, type KeyboardEvent } from "react";
import { THEME_LABELS, type ThemeId } from "@/config/theme";

const THEME_IDS = Object.keys(THEME_LABELS) as ThemeId[];

type Props = { value: ThemeId; onChange: (theme: ThemeId) => void };

/** Palette picker: each swatch is scoped with its own data-theme so it shows that palette's real tokens. */
export function ThemeChoice({ value, onChange }: Props) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent, index: number) {
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const rtl = document.documentElement.dir === "rtl";
    const forward = event.key === (rtl ? "ArrowLeft" : "ArrowRight") || event.key === "ArrowDown";
    const next = (index + (forward ? 1 : -1) + THEME_IDS.length) % THEME_IDS.length;
    onChange(THEME_IDS[next]);
    refs.current[next]?.focus();
  }

  return (
    <div role="radiogroup" aria-label="پالت رنگی" className="ds-theme-grid" data-testid="pref-theme">
      {THEME_IDS.map((id, index) => (
        <button
          key={id}
          ref={(node) => {
            refs.current[index] = node;
          }}
          type="button"
          role="radio"
          aria-checked={value === id}
          tabIndex={value === id ? 0 : -1}
          className="ds-theme-card"
          data-testid={`pref-theme-${id}`}
          onClick={() => onChange(id)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          <span className="ds-swatch" data-theme={id} aria-hidden="true">
            <span className="ds-swatch-side" />
            <span className="ds-swatch-body">
              <span className="ds-swatch-accent" />
              <span className="ds-swatch-line" />
              <span className="ds-swatch-line ds-swatch-line-short" />
            </span>
          </span>
          <span className="ds-theme-name">{THEME_LABELS[id]}</span>
        </button>
      ))}
    </div>
  );
}
