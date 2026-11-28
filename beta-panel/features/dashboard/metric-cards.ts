import { P } from "@/lib/permissions";
import type { DashboardAudience } from "./dashboard-role";
import type { MetricCardDef, Summary } from "./types";

/** Filter the dashboard schedule table in-place (not navigate away). */
export type MetricFilterKey = "today" | "upcoming" | "needs_status" | "cancelled" | "online";

function dashFilter(key: MetricFilterKey): string {
  return `#dash-${key}`;
}

/**
 * Five operational metric cards (Task 34 R2 dashboard PO).
 * Today's Appointments is the default dataset and must not be interactive.
 */
export function buildMetricCards(
  audience: DashboardAudience,
  can: (code: string) => boolean,
  today: string,
  _tomorrow: string,
  data: Summary | null,
): MetricCardDef[] {
  const total = data?.appointments?.total ?? null;
  const upcoming = data?.appointments?.upcoming_count ?? null;
  const needsStatus = data?.appointments?.needs_status_count ?? null;
  const cancelled =
    data?.appointments?.cancelled_count ??
    (data?.appointments ? (data.appointments.by_status.CANCELLED ?? 0) : null);
  const online = data?.appointments?.online_bookings_today ?? null;
  const onlineUnreviewed = data?.appointments?.online_unreviewed_count ?? null;

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
        accent: "today",
        interactive: false,
      },
      {
        key: "upcoming",
        label: "نوبت‌های پیش رو",
        value: upcoming,
        href: dashFilter("upcoming"),
        icon: "calendarClock",
        testId: "dashboard-upcoming",
        accent: "upcoming",
        interactive: true,
      },
      {
        key: "needs-status",
        label: "نیازمند تعیین وضعیت",
        value: needsStatus,
        href: dashFilter("needs_status"),
        icon: "alert",
        testId: "dashboard-needs-status",
        accent: "needs",
        interactive: true,
      },
      {
        key: "cancelled",
        label: "نوبت‌های لغوشده",
        value: cancelled,
        href: dashFilter("cancelled"),
        icon: "calendarX",
        testId: "dashboard-cancelled",
        accent: "cancelled",
        interactive: true,
      },
      {
        key: "online",
        label: "رزروهای آنلاین امروز",
        value: online,
        href: dashFilter("online"),
        icon: "globe",
        testId: "dashboard-online",
        accent: "online",
        interactive: true,
        badge: onlineUnreviewed && onlineUnreviewed > 0 ? onlineUnreviewed : undefined,
      },
    ];
  }

  const cards: MetricCardDef[] = [];
  if (can(P.appointmentsList)) {
    cards.push({
      key: "today",
      label: "نوبت‌های امروز",
      value: total,
      href: `/appointments?view=list&date=${today}`,
      icon: "calendar",
      testId: "dashboard-count",
      accent: "today",
      interactive: true,
    });
    cards.push({
      key: "cancelled",
      label: "لغوشدهٔ امروز",
      value: cancelled,
      href: `/appointments?view=list&date=${today}&status=CANCELLED`,
      icon: "calendarX",
      testId: "dashboard-cancelled",
      accent: "cancelled",
      interactive: true,
    });
  }
  if (can(P.financeSummary)) {
    cards.push({
      key: "finance-net",
      label: "خالص دریافتی امروز",
      value: data?.finance?.net_collected_irr,
      href: "/finance",
      icon: "wallet",
      testId: "dashboard-finance-net",
      accent: "online",
      interactive: true,
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
      interactive: true,
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
      interactive: true,
    });
  }
  return cards;
}
