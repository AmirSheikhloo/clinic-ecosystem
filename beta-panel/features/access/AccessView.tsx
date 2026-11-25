"use client";

import { useState } from "react";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { useSession } from "@/components/session/SessionProvider";
import { PageHeader } from "@/components/ui/PageHeader";
import { Tabs, type TabDef } from "@/components/ui/Tabs";
import { P } from "@/lib/permissions";
import { AccountsTab } from "./AccountsTab";
import { GovernanceTab } from "./GovernanceTab";
import { RolesTab } from "./RolesTab";

export function AccessView() {
  const { can, status } = useSession();
  const tabs: TabDef[] = [
    ...(can(P.accountsView) ? [{ id: "accounts", label: "حساب‌های کاربری" }] : []),
    ...(can(P.rolesView) ? [{ id: "roles", label: "نقش‌ها و مجوزها" }] : []),
    ...(can(P.governanceView) ? [{ id: "governance", label: "حاکمیت (مالک / مدیر)" }] : []),
  ];
  const [chosen, setChosen] = useState<string | null>(null);

  if (status === "loading") return <p className="text-[var(--ds-text-muted)]">در حال آماده‌سازی…</p>;
  if (!tabs.length) return <AccessDenied what="مدیریت کاربران و دسترسی" />;
  const active = tabs.some((t) => t.id === chosen) ? (chosen as string) : tabs[0].id;

  return (
    <main className="space-y-6 animate-rise" data-testid="access-page">
      <PageHeader
        title="کاربران، نقش‌ها و دسترسی‌ها"
        description="تمام تصمیم‌های مجوز در سرور اعمال می‌شود؛ این صفحه فقط وضعیت را نمایش و درخواست را ارسال می‌کند."
      />
      <Tabs tabs={tabs} active={active} onChange={setChosen} label="بخش‌های مدیریت دسترسی" />
      {active === "accounts" && <AccountsTab />}
      {active === "roles" && <RolesTab />}
      {active === "governance" && <GovernanceTab />}
    </main>
  );
}
