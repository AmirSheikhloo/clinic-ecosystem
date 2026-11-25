"use client";

import Link from "next/link";
import { useState } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SelectField } from "@/components/forms/SelectField";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useSearchParams } from "next/navigation";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { RESOURCE_TYPE_LABEL, resourceTypeLabel } from "@/lib/resources";
import { useApiQuery } from "@/lib/use-api-query";

type Service = { id: string; service_name: string; default_duration_minutes: number; is_active: boolean };
type Resource = { id: string; resource_name: string; resource_type: string; is_active?: boolean };

export function CatalogView() {
  const { can } = useSession();
  const [draft, setDraft] = useState(useSearchParams().get("q") ?? "");
  const [type, setType] = useState("");
  const [refresh, setRefresh] = useState(0);
  const services = useApiQuery<{ items: Service[] }>("/api/catalog/services", "بارگذاری خدمات ناموفق بود", refresh);
  const resources = useApiQuery<{ items: Resource[] }>("/api/catalog/resources", "بارگذاری منابع ناموفق بود", refresh);
  const canManage = can(P.servicesManage) || can(P.resourcesManage);
  const term = draft.trim().toLowerCase();
  const visibleServices = (services.data?.items ?? []).filter((item) => !term || item.service_name.toLowerCase().includes(term));
  const visibleResources = (resources.data?.items ?? []).filter(
    (item) => (!term || item.resource_name.toLowerCase().includes(term)) && (!type || item.resource_type === type),
  );
  const loading = (services.loading && !services.data) || (resources.loading && !resources.data);

  return (
    <main className="space-y-5" data-testid="catalog-page">
      <PageHeader
        title="خدمات و منابع"
        description="نمای مرجع خدمت‌ها و منابع فعال که در نوبت‌دهی استفاده می‌شود."
        meta={<StatusBadge tone={canManage ? "ok" : "neutral"}>{canManage ? "دسترسی مدیریت" : "فقط مشاهده"}</StatusBadge>}
        actions={
          <>
            <Button variant="ghost" icon="refresh" loading={services.loading || resources.loading} onClick={() => setRefresh((v) => v + 1)}>
              به‌روزرسانی
            </Button>
            {canManage ? (
              <Link href="/catalog/manage" className="ds-btn ds-btn-primary" data-testid="catalog-manage-link">
                مدیریت خدمات و منابع
              </Link>
            ) : null}
          </>
        }
      />

      <div className="ds-card flex flex-wrap items-end gap-3 p-3">
        <label className="block min-w-56 flex-1 space-y-1 text-sm">
          <span className="ds-field-label">جستجو</span>
          <span className="relative block">
            <Icon name="search" size="sm" className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-muted)]" />
            <input className="ds-input ps-9" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="نام خدمت یا منبع" aria-label="جستجوی خدمات و منابع" data-testid="catalog-search" />
          </span>
        </label>
        <SelectField label="نوع منبع" value={type} onChange={(e) => setType(e.target.value)} data-testid="catalog-type">
          <option value="">همه انواع</option>
          {Object.entries(RESOURCE_TYPE_LABEL).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </SelectField>
      </div>

      <QueryBoundary loading={loading} error={services.error ?? resources.error} deniedWhat="مشاهدهٔ خدمات و منابع" onRetry={() => setRefresh((v) => v + 1)}>
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="ds-card space-y-3 p-5" data-testid="catalog-services">
            <h2 className="ds-section-title">خدمات ({formatCount(visibleServices.length)})</h2>
            {!visibleServices.length ? <EmptyState icon="catalog" title="خدمتی یافت نشد" description="عبارت جستجو را تغییر دهید." /> : null}
            <ul className="space-y-2">
              {visibleServices.map((service) => (
                <li key={service.id} className="flex items-center justify-between gap-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2">
                  <span className="font-medium">{service.service_name}</span>
                  <StatusBadge>{formatCount(service.default_duration_minutes)} دقیقه</StatusBadge>
                </li>
              ))}
            </ul>
          </div>
          <div className="ds-card space-y-3 p-5" data-testid="catalog-resources">
            <h2 className="ds-section-title">منابع ({formatCount(visibleResources.length)})</h2>
            {!visibleResources.length ? <EmptyState icon="layers" title="منبعی یافت نشد" description="عبارت جستجو یا نوع منبع را تغییر دهید." /> : null}
            <ul className="space-y-2">
              {visibleResources.map((resource) => (
                <li key={resource.id} className="flex items-center justify-between gap-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2">
                  <span className="font-medium">{resource.resource_name}</span>
                  <StatusBadge tone="info">{resourceTypeLabel(resource.resource_type)}</StatusBadge>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </QueryBoundary>
    </main>
  );
}
