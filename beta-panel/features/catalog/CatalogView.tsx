"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";

type Service = {
  id: string;
  service_name: string;
  default_duration_minutes: number;
  is_active: boolean;
};

type Resource = {
  id: string;
  resource_name: string;
  resource_type: string;
  is_active?: boolean;
};

export function CatalogView() {
  const router = useRouter();
  const [services, setServices] = useState<Service[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const me = await apiFetch("/api/auth/me");
        if (cancelled) return;
        if (me.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        const [svcRes, resRes] = await Promise.all([
          apiFetch("/api/catalog/services"),
          apiFetch("/api/catalog/resources"),
        ]);
        if (cancelled) return;
        if (svcRes.status === 401 || resRes.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!svcRes.ok || !resRes.ok) {
          const data = (await (svcRes.ok ? resRes : svcRes).json().catch(() => ({}))) as ApiErrorBody;
          if (cancelled) return;
          setError(formatApiError(data, "بارگذاری فهرست ناموفق بود"));
          setLoading(false);
          return;
        }
        const svcData = await svcRes.json();
        const resData = await resRes.json();
        if (cancelled) return;
        setServices(svcData.items || []);
        setResources(resData.items || []);
        setError(null);
        setLoading(false);
      } catch {
        if (!cancelled) {
          setError("ارتباط برای بارگذاری فهرست برقرار نشد");
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [router, refreshKey]);

  return (
    <main className="space-y-6 animate-rise" data-testid="catalog-page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">فهرست خدمات و منابع</h2>
          <p className="text-[var(--ds-text-muted)]">نمای فقط‌خواندنی از APIهای مجاز — بدون CRUD مدیریتی</p>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            setLoading(true);
            setRefreshKey((value) => value + 1);
          }}
        >
          تازه‌سازی
        </Button>
      </header>

      {loading && <p className="text-[var(--ds-text-muted)]">در حال بارگذاری…</p>}
      {error && <Alert>{error}</Alert>}

      {!loading && !error && (
        <section className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-3">
            <h3 className="font-semibold">خدمات ({formatCount(services.length)})</h3>
            {!services.length && <EmptyState title="خدمتی موجود نیست" />}
            <ul className="space-y-2">
              {services.map((service) => (
                <li
                  key={service.id}
                  className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2"
                >
                  <p className="font-medium">{service.service_name}</p>
                  <p className="text-xs text-[var(--ds-text-muted)] tabular-nums">
                    مدت پیش‌فرض: {formatCount(service.default_duration_minutes)} دقیقه
                  </p>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="space-y-3">
            <h3 className="font-semibold">منابع ({formatCount(resources.length)})</h3>
            {!resources.length && <EmptyState title="منبعی موجود نیست" />}
            <ul className="space-y-2">
              {resources.map((resource) => (
                <li
                  key={resource.id}
                  className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2"
                >
                  <p className="font-medium">{resource.resource_name}</p>
                  <p className="text-xs text-[var(--ds-text-muted)]">{resource.resource_type}</p>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}
    </main>
  );
}
