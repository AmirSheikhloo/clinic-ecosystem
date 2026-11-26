import { P } from "@/lib/permissions";
import type { DashboardAudience } from "./dashboard-role";
import type { MetricCardDef, Summary } from "./types";

function listHref(date: string, status?: string): string {
  const params = new URLSearchParams({ view: "list", date });
  if (status) params.set("status", status);
  return `/appointments?${params.toString()}`;
}

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
  const uniquePatients = data?.appointments?.unique_patients ?? null;
  const checkedIn =
    data?.appointments?.waiting_checked_in ??
    (data?.appointments ? (data.appointments.by_status.CHECKED_IN ?? 0) : null);

  if (audience.composition === "operational") {
    const cards: MetricCardDef[] = [];
    if (can(P.appointmentsList)) {
      cards.push({
        key: "today",
        label: "نوبت‌های امروز",
        value: data?.appointments?.total,
        href: listHref(today),
        icon: "calendar",
        testId: "dashboard-count",
      });
      cards.push({
        key: "tomorrow",
        label: "نوبت‌های فردا",
        value: data?.tomorrow_appointments?.total,
        href: listHref(tomorrow),
        icon: "calendar",
        testId: "dashboard-tomorrow",
      });
      cards.push({
        key: "unique-patients",
        label: "بیماران یکتای امروز",
        value: uniquePatients,
        href: listHref(today),
        icon: "patients",
        testId: "dashboard-unique-patients",
        hint: "تعداد نوبت با تعداد بیمار یکتا متفاوت است",
      });
      cards.push({
        key: "cancelled",
        label: "لغوشدهٔ امروز",
        value: cancelled,
        href: listHref(today, "CANCELLED"),
        icon: "alert",
        testId: "dashboard-cancelled",
      });
      cards.push({
        key: "confirmed",
        label: "تأییدشدهٔ امروز",
        value: confirmed,
        href: listHref(today, "CONFIRMED"),
        icon: "desk",
        testId: "dashboard-confirmed",
      });
      cards.push({
        key: "checked-in",
        label: "حاضر در کلینیک",
        value: checkedIn,
        href: listHref(today, "CHECKED_IN"),
        icon: "desk",
        testId: "dashboard-checked-in",
        hint: "نوبت‌های با وضعیت حضور ثبت‌شده",
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
      href: listHref(today),
      icon: "calendar",
      testId: "dashboard-count",
    });
    cards.push({
      key: "tomorrow",
      label: "نوبت‌های فردا",
      value: data?.tomorrow_appointments?.total,
      href: listHref(tomorrow),
      icon: "calendar",
      testId: "dashboard-tomorrow",
    });
    cards.push({
      key: "unique-patients",
      label: "بیماران یکتای امروز",
      value: uniquePatients,
      href: listHref(today),
      icon: "patients",
      testId: "dashboard-unique-patients",
    });
    cards.push({
      key: "cancelled",
      label: "لغوشدهٔ امروز",
      value: cancelled,
      href: listHref(today, "CANCELLED"),
      icon: "alert",
      testId: "dashboard-cancelled",
    });
    cards.push({
      key: "confirmed",
      label: "تأییدشدهٔ امروز",
      value: confirmed,
      href: listHref(today, "CONFIRMED"),
      icon: "desk",
      testId: "dashboard-confirmed",
    });
    cards.push({
      key: "checked-in",
      label: "حاضر در کلینیک",
      value: checkedIn,
      href: listHref(today, "CHECKED_IN"),
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
