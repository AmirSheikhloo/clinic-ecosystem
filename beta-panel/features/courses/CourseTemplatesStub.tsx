"use client";

/** Ops config stub: versioned course templates (pay-per-session only). */
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";

type TemplateList = {
  items: Array<{
    id: string;
    template_code: string;
    template_name: string;
    version_no: number;
    planned_sessions: number | null;
    interval_kind: string | null;
    interval_value: number | null;
    reminder_lead_days: number | null;
    billing_mode: string;
    is_active: boolean;
  }>;
  prepaid_entitlement_enabled: boolean;
};

export function CourseTemplatesStub() {
  const { can, status } = useSession();
  const allowed = can(P.coursesView);
  const query = useApiQuery<TemplateList>(
    status === "ready" && allowed ? "/api/v1/courses/templates" : null,
    "بارگذاری قالب دوره‌ها ناموفق بود",
  );

  if (!allowed) return null;

  return (
    <section data-testid="ops-course-templates" className="space-y-3">
      <h2 className="ds-section-title mb-1">قالب دوره‌های درمان</h2>
      <p className="ds-hint">
        فقط پرداخت هر جلسه. پیش‌پرداخت و تسویه اشتراکی تا تصویب مالک غیرفعال است.
      </p>
      {query.error ? <Alert>{query.error.message}</Alert> : null}
      {(query.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="قالبی تعریف نشده"
          description="پس از اعمال اسکیمای disposable، قالب نسخه‌دار از API قابل ثبت است."
        />
      ) : (
        <ul className="space-y-2">
          {(query.data?.items ?? []).map((t) => (
            <li key={t.id} className="ds-card px-4 py-3 text-sm">
              <span className="font-medium">{t.template_name}</span>
              <span className="ms-2 text-[var(--ds-text-muted)] tabular-nums">
                {t.template_code} · v{t.version_no}
              </span>
              <p className="mt-1 text-[var(--ds-text-muted)]">
                {t.planned_sessions ?? "—"} جلسه · {t.billing_mode}
                {t.is_active ? "" : " · غیرفعال"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
