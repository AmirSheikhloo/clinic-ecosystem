"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { useSession } from "@/components/session/SessionProvider";
import { Skeleton } from "@/components/ui/Skeleton";
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

  if (status === "loading") return <Skeleton className="h-64" />;
  if (!tabs.length) return <AccessDenied what="مدیریت خدمات و منابع" />;
  const active = tabs.some((t) => t.id === chosen) ? (chosen as string) : tabs[0].id;

  return (
    <main className="space-y-5" data-testid="catalog-admin-page">
      <PageHeader
        title="مدیریت خدمات و منابع"
        description="ایجاد و ویرایش خدمت‌ها، تعرفه، مدت و الزامات منابع. این بخش فقط برای کاربران دارای مجوز مدیریت در دسترس است."
        actions={<Link href="/catalog" className="ds-btn ds-btn-ghost" data-testid="catalog-back">نمای مرجع</Link>}
      />
      <Tabs tabs={tabs} active={active} onChange={setChosen} label="بخش‌های مدیریت کاتالوگ" />
      {active === "services" && <ServicesAdmin initialQuery={params.get("q") ?? ""} />}
      {active === "resources" && <ResourcesAdmin />}
    </main>
  );
}
