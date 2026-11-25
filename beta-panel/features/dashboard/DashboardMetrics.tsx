import { StatCard } from "@/components/ui/StatCard";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import type { Summary } from "./types";

type Props = { data: Summary | null; loading: boolean; can: (code: string) => boolean; today: string };

const show = (value: number | null | undefined) => (value === null || value === undefined ? "—" : formatCount(value));

/**
 * Metric cards. Which cards exist depends on the session's permissions, never on the response, so the
 * grid has the same shape while loading and after; the server still decides each value (null shows "—").
 */
export function DashboardMetrics({ data, loading, can, today }: Props) {
  const cards = [
    { show: can(P.appointmentsList), icon: "calendar", label: "نوبت‌های امروز", value: data?.appointments?.total, testId: "dashboard-count", href: `/appointments?date=${today}&view=day` },
    { show: can(P.patientsSearch), icon: "patients", label: "بیماران فعال", value: data?.patients_active, testId: "dashboard-patients", href: "/patients" },
    { show: can(P.staffView), icon: "staff", label: "کارکنان فعال", value: data?.staff_active, testId: "dashboard-staff", href: "/staff" },
    { show: can(P.catalogServicesRead), icon: "catalog", label: "خدمات فعال", value: data?.services_active, testId: "dashboard-services", href: "/catalog" },
    { show: can(P.resourcesRead), icon: "layers", label: "منابع فعال", value: data?.resources_active, testId: "dashboard-resources", href: "/catalog" },
  ] as const;
  const visible = cards.filter((card) => card.show);
  if (!visible.length) return null;
  return (
    <section className="ds-metric-grid" aria-label="شاخص‌ها">
      {visible.map((card) => (
        <StatCard
          key={card.testId}
          icon={card.icon}
          label={card.label}
          value={show(card.value)}
          loading={loading}
          testId={card.testId}
          href={card.href}
        />
      ))}
    </section>
  );
}
