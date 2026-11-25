"use client";

import { useRef, useState } from "react";
import { useTheme } from "@/components/feedback/ThemeProvider";
import { Button } from "@/components/ui/Button";
import { Popover } from "@/components/ui/Popover";
import { SelectField } from "@/components/forms/SelectField";
import { THEME_LABELS, type ThemeId } from "@/config/theme";

/** Palette and light/dark controls; preferences only, never patient data. */
export function ThemeMenu() {
  const { theme, appearance, setTheme, toggleAppearance } = useTheme();
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLButtonElement>(null);
  return (
    <>
      <Button
        ref={anchorRef}
        variant="ghost"
        icon="palette"
        aria-label="ظاهر برنامه"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        data-testid="theme-menu-button"
      />
      <Popover open={open} onClose={() => setOpen(false)} anchorRef={anchorRef} label="ظاهر برنامه" role="dialog" align="end">
        <div className="w-64 space-y-3 p-3">
          <SelectField
            label="پالت رنگی"
            value={theme}
            onChange={(event) => setTheme(event.target.value as ThemeId)}
            aria-label="انتخاب تم"
            data-testid="theme-select"
            data-autofocus
          >
            {(Object.keys(THEME_LABELS) as ThemeId[]).map((id) => (
              <option key={id} value={id}>
                {THEME_LABELS[id]}
              </option>
            ))}
          </SelectField>
          <Button
            variant="ghost"
            className="w-full"
            icon={appearance === "light" ? "moon" : "sun"}
            onClick={toggleAppearance}
            data-testid="appearance-toggle"
          >
            {appearance === "light" ? "حالت تیره" : "حالت روشن"}
          </Button>
        </div>
      </Popover>
    </>
  );
}
