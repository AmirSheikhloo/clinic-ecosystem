import Link from "next/link";
import { Alert } from "@/components/feedback/Alert";
import { formatCount } from "@/lib/format/numbers";
import type { Summary } from "./types";

type Props = {
  today: string;
  summary: Summary | null;
  canList: boolean;
};

/** Only real, permission-backed signals — never speculative BI warnings. */
export function DashboardAlerts({ today, summary, canList }: Props) {
  if (!canList) return null;
  const cancelled = summary?.appointments?.by_status?.CANCELLED ?? 0;
  if (!cancelled) return null;

  return (
    <section className="space-y-2" aria-label="هشدارهای عملیاتی" data-testid="dashboard-alerts">
      <Alert tone="warn" testId="dashboard-alert-cancelled">
        امروز {formatCount(cancelled)} نوبت لغو شده است.{" "}
        <Link href={`/appointments?date=${today}&view=day&status=CANCELLED`} className="underline">
          مشاهده در تقویم
        </Link>
      </Alert>
    </section>
  );
}
