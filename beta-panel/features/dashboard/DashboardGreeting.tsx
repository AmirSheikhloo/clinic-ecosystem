"use client";

import { formatJalaliFromTehranYmd, formatTehranTime } from "@/lib/format/jalali";
import { useNow } from "@/lib/use-now";

type Props = {
  todayYmd: string;
  firstName: string;
  roleLabel: string;
  composition: "operational" | "management";
};

/** Live Tehran clock (minute resolution) plus Jalali date — never invented clinic time. */
export function DashboardGreeting({ todayYmd, firstName, roleLabel, composition }: Props) {
  const now = useNow(30_000);
  const clock = now ? formatTehranTime(new Date(now).toISOString()) : "—:—";
  const purpose =
    composition === "management"
      ? "نمای مدیریتی — فقط دادهٔ مجاز برای حساب شما"
      : "مرکز عملیات روزانهٔ پذیرش — فقط دادهٔ مجاز برای حساب شما";

  return (
    <div className="space-y-1" data-testid="dashboard-greeting">
      <p className="text-sm text-[var(--ds-text-muted)]">
        {firstName ? `سلام ${firstName}` : "سلام"} · <span data-testid="dashboard-role">{roleLabel}</span>
      </p>
      <p className="text-sm text-[var(--ds-text)]">
        <span data-testid="dashboard-date">{formatJalaliFromTehranYmd(todayYmd)}</span>
        {" · "}
        <span className="tabular-nums" data-testid="dashboard-clock">
          {clock}
        </span>
        <span className="text-[var(--ds-text-muted)]"> به وقت تهران</span>
      </p>
      <p className="ds-hint">{purpose}</p>
    </div>
  );
}
