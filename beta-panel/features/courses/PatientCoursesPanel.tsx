"use client";

/**
 * Patient dossier hook for pay-per-session treatment courses (Task 34 R2 §9).
 * Prepaid entitlement remains disabled; UI never offers package redemption.
 */
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { apiJson } from "@/lib/api";
import { formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { useState } from "react";

type CourseRow = {
  id: string;
  service_id: string;
  planned_sessions: number;
  completed_session_count: number;
  status: string;
  billing_mode: string;
  next_suggested_date_tehran: string | null;
  last_completion_date_tehran: string | null;
  interval_kind: string;
  interval_value: number;
  reminder_lead_days: number;
  aggregate_version: number;
  prepaid_enabled: boolean;
};

type CourseList = {
  items: CourseRow[];
  prepaid_entitlement_enabled: boolean;
};

const STATUS_FA: Record<string, string> = {
  ACTIVE: "فعال",
  PAUSED: "متوقف",
  REASSESSMENT_REQUIRED: "نیاز به بازنگری",
  COMPLETED: "تمام‌شده",
  TERMINATED: "خاتمه‌یافته",
};

export function PatientCoursesPanel({ patientId }: { patientId: string }) {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allowed = can(P.coursesView);
  const query = useApiQuery<CourseList>(
    status === "ready" && allowed ? `/api/v1/courses/patients/${patientId}` : null,
    "بارگذاری دوره‌های درمان ناموفق بود",
    refresh,
  );

  if (!allowed) return null;

  async function pauseOrResume(course: CourseRow, next: "PAUSED" | "ACTIVE") {
    if (!can(P.coursesManage) || busyId) return;
    setBusyId(course.id);
    setError(null);
    const result = await apiJson(`/api/v1/courses/${course.id}/lifecycle`, {
      method: "POST",
      version: course.aggregate_version,
      body: { status: next },
      fallbackMessage: "تغییر وضعیت دوره ناموفق بود",
    });
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setRefresh((v) => v + 1);
  }

  return (
    <section className="space-y-3" data-testid="patient-courses-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="ds-section-title">دوره‌های درمان (پرداخت هر جلسه)</h2>
        <Button variant="ghost" icon="refresh" onClick={() => setRefresh((v) => v + 1)}>
          به‌روزرسانی
        </Button>
      </div>
      <p className="ds-hint">
        یادآوری نوبت بعدی از تاریخ اتمام واقعی محاسبه می‌شود — نه از نوبت‌دهی یا پرداخت.
        بسته پیش‌پرداخت غیرفعال است.
      </p>
      {error ? <Alert>{error}</Alert> : null}
      {query.error ? <Alert>{query.error.message}</Alert> : null}
      {!query.loading && (query.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="دوره‌ای ثبت نشده"
          description="ثبت دورهٔ پرداخت-هر-جلسه از پیکربندی عملیات یا میز پذیرش (به‌زودی)."
        />
      ) : (
        <ul className="space-y-2">
          {(query.data?.items ?? []).map((c) => (
            <li key={c.id} className="ds-card px-4 py-3 text-sm" data-testid="patient-course-row">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium tabular-nums">
                  {c.completed_session_count}/{c.planned_sessions} جلسه · {STATUS_FA[c.status] ?? c.status}
                </span>
                <span className="text-[var(--ds-text-muted)]">PAY_PER_SESSION</span>
              </div>
              <p className="mt-1 text-[var(--ds-text-muted)]">
                فاصله: {c.interval_value}{" "}
                {c.interval_kind === "FIXED_DAYS" ? "روز" : "ماه جلالی"} · یادآوری{" "}
                {c.reminder_lead_days} روز قبل
              </p>
              {c.last_completion_date_tehran ? (
                <p className="tabular-nums">
                  آخرین اتمام: {formatJalaliFromTehranYmd(c.last_completion_date_tehran)}
                </p>
              ) : null}
              {c.next_suggested_date_tehran ? (
                <p className="tabular-nums" data-testid="course-next-suggested">
                  پیشنهاد مراجعه بعدی: {formatJalaliFromTehranYmd(c.next_suggested_date_tehran)}
                </p>
              ) : null}
              {can(P.coursesManage) && (c.status === "ACTIVE" || c.status === "PAUSED") ? (
                <div className="mt-2 flex gap-2">
                  {c.status === "ACTIVE" ? (
                    <Button
                      variant="ghost"
                      disabled={busyId === c.id}
                      onClick={() => void pauseOrResume(c, "PAUSED")}
                    >
                      توقف
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      disabled={busyId === c.id}
                      onClick={() => void pauseOrResume(c, "ACTIVE")}
                    >
                      ادامه
                    </Button>
                  )}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
