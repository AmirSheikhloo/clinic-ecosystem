"use client";

import { useEffect, useState } from "react";
import { formatTehranClock, tehranTodayJalaliLabel } from "@/lib/tehran";

/** Compact live Jalali date + Tehran 24h clock for the top bar. */
export function LiveTehranClock() {
  const [label, setLabel] = useState(() => `${tehranTodayJalaliLabel()} · ${formatTehranClock(new Date())}`);

  useEffect(() => {
    const tick = () => setLabel(`${tehranTodayJalaliLabel()} · ${formatTehranClock(new Date())}`);
    tick();
    const id = window.setInterval(tick, 15_000);
    const onFocus = () => tick();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  return (
    <time className="ds-tehran-clock ltr-isolate text-xs tabular-nums text-[var(--ds-text-muted)]" data-testid="tehran-clock" dateTime={new Date().toISOString()}>
      {label}
    </time>
  );
}
