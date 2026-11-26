import { P } from "@/lib/permissions";
import type { DashboardAudience } from "./dashboard-role";
import type { MetricCardDef, Summary } from "./types";

/** Permission-stable card sets: which cards exist never depends on response values. */
export function buildMetricCards(
  audience: DashboardAudience,
  can: (code: string) => boolean,
  today: string,
  tomorrow: string,
  data: Summary | null,
): MetricCardDef[] {
  const cancelled = data?.appointments ? (data.appointments.by_status.CANCELLED ?? 0) : null;
  const confirmed = data?.appointments ? (data.appointments.by_status.CONFIRMED ?? 0) : null;

  if (audience.composition === "operational") {
    const checkedIn = data?.appointments ? (data.appointments.by_status.CHECKED_IN ?? 0) : null;
    const cards: MetricCardDef[] = [];
    if (can(P.appointmentsList)) {
      cards.push({
        key: "today",
        label: "نوبت‌های امروز",
        value: data?.appointments?.total,
        href: `/appointments?date=${today}&view=day`,
        icon: "calendar",
        testId: "dashboard-count",
      });
      cards.push({
        key: "tomorrow",
        label: "نوبت‌های فردا",
        value: data?.tomorrow_appointments?.total,
        href: `/appointments?date=${tomorrow}&view=day`,
        icon: "calendar",
        testId: "dashboard-tomorrow",
      });
      cards.push({
        key: "cancelled",
        label: "لغوشدهٔ امروز",
        value: cancelled,
        href: `/appointments?date=${today}&view=day&status=CANCELLED`,
        icon: "alert",
        testId: "dashboard-cancelled",
      });
      cards.push({
        key: "confirmed",
        label: "تأییدشدهٔ امروز",
        value: confirmed,
        href: `/appointments?date=${today}&view=day&status=CONFIRMED`,
        icon: "desk",
        testId: "dashboard-confirmed",
      });
      cards.push({
        key: "checked-in",
        label: "حاضر در کلینیک",
        value: checkedIn,
        href: `/appointments?view=list&status=CHECKED_IN&date=today`,
        icon: "desk",
        testId: "dashboard-checked-in",
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

  const cards: MetricCardDef[] = [];
  if (can(P.appointmentsList)) {
    cards.push({
      key: "today",
      label: "نوبت‌های امروز",
      value: data?.appointments?.total,
      href: `/appointments?date=${today}&view=day`,
      icon: "calendar",
      testId: "dashboard-count",
    });
    cards.push({
      key: "tomorrow",
      label: "نوبت‌های فردا",
      value: data?.tomorrow_appointments?.total,
      href: `/appointments?date=${tomorrow}&view=day`,
      icon: "calendar",
      testId: "dashboard-tomorrow",
    });
    cards.push({
      key: "cancelled",
      label: "لغوشدهٔ امروز",
      value: cancelled,
      href: `/appointments?date=${today}&view=day&status=CANCELLED`,
      icon: "alert",
      testId: "dashboard-cancelled",
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
  if (can(P.catalogServicesRead)) {
    cards.push({
      key: "services",
      label: "خدمات فعال",
      value: data?.services_active,
      href: "/catalog",
      icon: "catalog",
      testId: "dashboard-services",
    });
  }
  if (can(P.resourcesRead)) {
    cards.push({
      key: "resources",
      label: "منابع فعال",
      value: data?.resources_active,
      href: "/catalog",
      icon: "layers",
      testId: "dashboard-resources",
    });
  }
  return cards;
}
