"use client";

import { useEffect, useState } from "react";
import { formatJalaliDate } from "@/lib/format/jalali";
import { formatTehranClock } from "@/lib/tehran";

/** Full Persian Jalali date + Tehran 24h clock for the top bar (Latin digits). */
export function LiveTehranClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = window.setInterval(tick, 15_000);
    const onFocus = () => tick();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  const datePart = formatJalaliDate(now.toISOString());
  const timePart = formatTehranClock(now);
  const label = `${datePart} · ${timePart} به وقت تهران`;

  return (
    <time
      className="ds-tehran-clock ltr-isolate text-xs tabular-nums text-[var(--ds-text-muted)]"
      data-testid="tehran-clock"
      dateTime={now.toISOString()}
      title={label}
    >
      {label}
    </time>
  );
}
