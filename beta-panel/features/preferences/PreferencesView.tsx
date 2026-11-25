"use client";

import type { ReactNode } from "react";
import { usePreferences } from "@/components/feedback/ThemeProvider";
import { Alert } from "@/components/feedback/Alert";
import { SegmentedControl, type SegmentedOption } from "@/components/forms/SegmentedControl";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  APPEARANCE_LABELS,
  DENSITY_LABELS,
  MOTION_LABELS,
  SIDEBAR_LABELS,
  type AppearancePreference,
  type Density,
  type MotionPreference,
  type SidebarPreference,
} from "@/config/preferences";
import { ThemeChoice } from "./ThemeChoice";

function options<T extends string>(prefix: string, labels: Record<T, string>): SegmentedOption<T>[] {
  return (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value], testId: `${prefix}-${value}` }));
}

function Setting({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="ds-setting">
      <div className="min-w-0">
        <h3 className="font-semibold text-[var(--ds-heading)]">{title}</h3>
        <p className="ds-hint mt-0.5">{description}</p>
      </div>
      <div className="ds-setting-control">{children}</div>
    </div>
  );
}

/** Browser-local display preferences. Nothing here is a clinic-wide or per-user server setting. */
export function PreferencesView() {
  const { preferences, appearance, setPreference, resetPreferences } = usePreferences();
  return (
    <main className="space-y-5" data-testid="preferences-page">
      <PageHeader
        title="ظاهر و ترجیحات"
        description="رنگ، تراکم نمایش و حرکت رابط کاربری را برای خودتان تنظیم کنید."
        actions={
          <Button variant="ghost" icon="refresh" onClick={resetPreferences} data-testid="preferences-reset">
            بازگشت به پیش‌فرض
          </Button>
        }
      />
      <Alert tone="info" testId="preferences-scope">
        این تنظیمات فقط در همین مرورگر ذخیره می‌شوند؛ بین دستگاه‌ها و کاربران همگام نمی‌شوند و روی دسترسی‌ها یا داده‌های کلینیک اثری ندارند.
      </Alert>

      <section className="ds-card ds-settings" aria-label="ظاهر">
        <Setting title="پالت رنگی" description="برای همهٔ صفحه‌ها اعمال می‌شود.">
          <ThemeChoice value={preferences.theme} onChange={(theme) => setPreference("theme", theme)} />
        </Setting>
        <Setting
          title="حالت نمایش"
          description={
            preferences.appearance === "system" ? `مطابق تنظیم سیستم‌عامل (اکنون: ${APPEARANCE_LABELS[appearance]})` : "روشن یا تیره"
          }
        >
          <SegmentedControl<AppearancePreference>
            label="حالت نمایش"
            value={preferences.appearance}
            options={options("pref-appearance", APPEARANCE_LABELS)}
            onChange={(value) => setPreference("appearance", value)}
            testId="pref-appearance"
          />
        </Setting>
        <Setting title="تراکم نمایش" description="در حالت فشرده، فاصلهٔ ردیف‌ها و ارتفاع کنترل‌ها کمتر است.">
          <SegmentedControl<Density>
            label="تراکم نمایش"
            value={preferences.density}
            options={options("pref-density", DENSITY_LABELS)}
            onChange={(value) => setPreference("density", value)}
            testId="pref-density"
          />
        </Setting>
        <Setting title="نوار کناری" description="وضعیت پیش‌فرض نوار کناری در دستگاه‌های بزرگ.">
          <SegmentedControl<SidebarPreference>
            label="نوار کناری"
            value={preferences.sidebar}
            options={options("pref-sidebar", SIDEBAR_LABELS)}
            onChange={(value) => setPreference("sidebar", value)}
            testId="pref-sidebar"
          />
        </Setting>
        <Setting title="حرکت و انیمیشن" description="کاهش حرکت، انتقال‌ها را تقریباً حذف می‌کند.">
          <SegmentedControl<MotionPreference>
            label="حرکت و انیمیشن"
            value={preferences.motion}
            options={options("pref-motion", MOTION_LABELS)}
            onChange={(value) => setPreference("motion", value)}
            testId="pref-motion"
          />
        </Setting>
      </section>
    </main>
  );
}
