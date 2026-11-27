import { P } from "@/lib/permissions";
import type { DashboardAudience } from "./dashboard-role";
import type { MetricCardDef, Summary } from "./types";

/** Filter the dashboard schedule table in-place (not navigate away). */
export type MetricFilterKey = "all" | "today" | "upcoming" | "needs_status" | "cancelled";

function dashFilter(key: MetricFilterKey): string {
  return `#dash-${key}`;
}

/**
 * Exactly four operational metric cards for receptionists (Task 34 §8 / DASH-02).
 * Management audience retains a broader set.
 */
export function buildMetricCards(
  audience: DashboardAudience,
  can: (code: string) => boolean,
  today: string,
  _tomorrow: string,
  data: Summary | null,
): MetricCardDef[] {
  const cancelled = data?.appointments ? (data.appointments.by_status.CANCELLED ?? 0) : null;
  const confirmed = data?.appointments ? (data.appointments.by_status.CONFIRMED ?? 0) : null;
  const total = data?.appointments?.total ?? null;

  // Heuristic for "needs status": confirmed appointments that are due for resolution.
  // Exact predicate must match table filter; server-side field preferred when available.
  const needsStatus =
    data?.appointments?.needs_status_count ??
    (data?.appointments
      ? Math.max(
          0,
          (data.appointments.by_status.CONFIRMED ?? 0) -
            (data.appointments.by_status.CHECKED_IN ?? 0),
        )
      : null);

  if (audience.composition === "operational") {
    if (!can(P.appointmentsList)) return [];
    return [
      {
        key: "today",
        label: "نوبت‌های امروز",
        value: total,
        href: dashFilter("today"),
        icon: "calendar",
        testId: "dashboard-count",
        accent: "blue",
      },
      {
        key: "upcoming",
        label: "نوبت‌های پیش رو",
        value: confirmed,
        href: dashFilter("upcoming"),
        icon: "calendar",
        testId: "dashboard-upcoming",
        accent: "purple",
      },
      {
        key: "needs-status",
        label: "نیازمند تعیین وضعیت",
        value: needsStatus,
        href: dashFilter("needs_status"),
        icon: "alert",
        testId: "dashboard-needs-status",
        accent: "amber",
      },
      {
        key: "cancelled",
        label: "نوبت‌های لغوشده",
        value: cancelled,
        href: dashFilter("cancelled"),
        icon: "alert",
        testId: "dashboard-cancelled",
        accent: "rose",
      },
    ];
  }

  // Management: keep supervisory breadth but still lead with today/cancelled.
  const cards: MetricCardDef[] = [];
  if (can(P.appointmentsList)) {
    cards.push({
      key: "today",
      label: "نوبت‌های امروز",
      value: total,
      href: `/appointments?view=list&date=${today}`,
      icon: "calendar",
      testId: "dashboard-count",
    });
    cards.push({
      key: "cancelled",
      label: "لغوشدهٔ امروز",
      value: cancelled,
      href: `/appointments?view=list&date=${today}&status=CANCELLED`,
      icon: "alert",
      testId: "dashboard-cancelled",
    });
  }
  if (can(P.financeSummary)) {
    cards.push({
      key: "finance-net",
      label: "خالص دریافتی امروز",
      value: data?.finance?.net_collected_irr,
      href: "/finance",
      icon: "desk",
      testId: "dashboard-finance-net",
    });
  }
  if (can(P.staffView)) {
    cards.push({
      key: "staff",
      label: "کارکنان فعال",
      value: data?.staff_active,
      href: "/staff",
      icon: "staff",
      testId: "dashboard-staff",
    });
  }
  if (can(P.patientsSearch)) {
    cards.push({
      key: "patients",
      label: "بیماران فعال",
      value: data?.patients_active,
      href: "/patients",
      icon: "patients",
      testId: "dashboard-patients",
    });
  }
  return cards;
}
