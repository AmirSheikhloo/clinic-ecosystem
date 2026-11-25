import Link from "next/link";
import { Alert } from "@/components/feedback/Alert";
import { formatCount } from "@/lib/format/numbers";
import type { CalendarResponse } from "@/features/appointments/types";
import type { Summary } from "./types";

type Props = {
  today: string;
  summary: Summary | null;
  calendar: CalendarResponse | null;
  canList: boolean;
};

/** Only real, permission-backed signals — never speculative BI warnings. */
export function DashboardAlerts({ today, summary, calendar, canList }: Props) {
  if (!canList) return null;
  const cancelled = summary?.appointments?.by_status?.CANCELLED ?? 0;
  const truncated = calendar?.truncated === true;
  if (!cancelled && !truncated) return null;

  return (
    <section className="space-y-2" aria-label="هشدارهای عملیاتی" data-testid="dashboard-alerts">
      {cancelled > 0 ? (
        <Alert tone="warn" testId="dashboard-alert-cancelled">
          امروز {formatCount(cancelled)} نوبت لغو شده است.{" "}
          <Link href={`/appointments?date=${today}&view=day&status=CANCELLED`} className="underline">
            مشاهده در تقویم
          </Link>
        </Alert>
      ) : null}
      {truncated ? (
        <Alert tone="danger" testId="dashboard-alert-truncated">
          فهرست امروز به سقف نمایش رسیده است؛ برای دیدن همه، فیلتر یا بازه را در تقویم محدود کنید.
        </Alert>
      ) : null}
    </section>
  );
}
