"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { useSession } from "@/components/session/SessionProvider";
import { PageHeader } from "@/components/ui/PageHeader";
import { Tabs, type TabDef } from "@/components/ui/Tabs";
import { P } from "@/lib/permissions";
import { ResourcesAdmin } from "./ResourcesAdmin";
import { ServicesAdmin } from "./ServicesAdmin";

export function CatalogAdminView() {
  const { can, status } = useSession();
  const params = useSearchParams();
  const tabs: TabDef[] = [
    ...(can(P.servicesManage) ? [{ id: "services", label: "خدمات" }] : []),
    ...(can(P.resourcesManage) ? [{ id: "resources", label: "منابع" }] : []),
  ];
  const [chosen, setChosen] = useState<string | null>(null);

  if (status === "loading") return <p className="text-[var(--ds-text-muted)]">در حال آماده‌سازی…</p>;
  if (!tabs.length) return <AccessDenied what="مدیریت خدمات و منابع" />;
  const active = tabs.some((t) => t.id === chosen) ? (chosen as string) : tabs[0].id;

  return (
    <main className="space-y-6 animate-rise" data-testid="catalog-admin-page">
      <PageHeader title="مدیریت خدمات و منابع" description="ایجاد و ویرایش با نسخه‌بندی، ممیزی و کلید ایدمپوتنسی؛ فقط مدیر" />
      <Tabs tabs={tabs} active={active} onChange={setChosen} label="بخش‌های مدیریت کاتالوگ" />
      {active === "services" && <ServicesAdmin initialQuery={params.get("q") ?? ""} />}
      {active === "resources" && <ResourcesAdmin />}
    </main>
  );
}
