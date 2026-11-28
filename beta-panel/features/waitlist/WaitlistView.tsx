"use client";

import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { useState } from "react";

type WaitlistItem = {
  id: string;
  patient_id: string;
  patient_name: string;
  service_id: string;
  service_name: string;
  priority: number;
  status: string;
  contact_state: string;
  notes: string | null;
  aggregate_version: number;
};

type WaitlistResponse = { items: WaitlistItem[] };

export function WaitlistView() {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const allowed = can(P.waitlistView);
  const query = useApiQuery<WaitlistResponse>(
    status === "ready" && allowed ? "/api/v1/waitlist/entries?limit=50&status=OPEN" : null,
    "بارگذاری لیست انتظار ناموفق بود",
    refresh,
  );

  if (status === "loading") return <PageSkeleton />;
  if (!allowed) {
    return (
      <main data-testid="waitlist-page">
        <PageHeader title="لیست انتظار" description="مشاهدهٔ این بخش نیازمند مجوز است." />
        <EmptyState title="دسترسی ندارید" description="مجوز WAITLIST_VIEW لازم است." />
      </main>
    );
  }

  async function markContacted(item: WaitlistItem) {
    if (!can(P.waitlistManage)) return;
    setBusyId(item.id);
    setActionError(null);
    const result = await apiJson(`/api/v1/waitlist/entries/${item.id}`, {
      method: "PATCH",
      body: {
        status: "CONTACTED",
        contact_state: "CONTACTED",
        expected_version: item.aggregate_version,
      },
    });
    setBusyId(null);
    if (!result.ok) {
      setActionError(result.message);
      return;
    }
    setRefresh((v) => v + 1);
  }

  return (
    <main className="space-y-6" data-testid="waitlist-page">
      <PageHeader
        title="لیست انتظار آینده"
        description="بیماران در صف انتظار برای نوبت آینده؛ اتاق انتظار فیزیکی از نوبت‌های CHECKED_IN است."
        actions={
          <Button variant="ghost" icon="refresh" onClick={() => setRefresh((v) => v + 1)} data-testid="waitlist-refresh">
            به‌روزرسانی
          </Button>
        }
      />
      {query.error ? <Alert testId="waitlist-error">{query.error.message}</Alert> : null}
      {actionError ? <Alert testId="waitlist-action-error">{actionError}</Alert> : null}
      {!query.loading && (query.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="موردی نیست" description="در حال حاضر ورودی OPEN در لیست انتظار وجود ندارد." />
      ) : (
        <ul className="space-y-3" data-testid="waitlist-items">
          {(query.data?.items ?? []).map((item) => (
            <li key={item.id} className="ds-card flex flex-wrap items-center justify-between gap-3 p-4" data-testid="waitlist-item">
              <div className="min-w-0">
                <p className="font-semibold text-[var(--ds-heading)]">{item.patient_name}</p>
                <p className="text-sm text-[var(--ds-text-muted)]">
                  {item.service_name} · اولویت {formatCount(item.priority)}
                </p>
                {item.notes ? <p className="mt-1 text-xs text-[var(--ds-text-muted)]">{item.notes}</p> : null}
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge tone="info">{item.status}</StatusBadge>
                {can(P.waitlistManage) ? (
                  <Button
                    size="sm"
                    loading={busyId === item.id}
                    onClick={() => void markContacted(item)}
                    data-testid="waitlist-contact"
                  >
                    تماس گرفته شد
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
