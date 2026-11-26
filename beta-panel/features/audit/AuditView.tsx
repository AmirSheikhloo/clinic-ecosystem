"use client";

import { useState } from "react";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SelectField } from "@/components/forms/SelectField";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Pagination } from "@/components/ui/Pagination";
import { buildQuery } from "@/lib/api";
import { formatTehran } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import {
  AUDIT_PAGE_SIZE,
  operationLabel,
  targetTypeLabel,
  type AuditEntry,
} from "./types";

const TARGET_FILTERS = [
  { value: "", label: "همهٔ انواع هدف" },
  { value: "appointment", label: "نوبت" },
  { value: "patient_profile", label: "بیمار" },
  { value: "staff", label: "کارمند" },
  { value: "account", label: "حساب" },
  { value: "demo_dataset", label: "دادهٔ نمونه" },
];

export function AuditView() {
  const { can, status } = useSession();
  const [targetType, setTargetType] = useState("");
  const [offset, setOffset] = useState(0);
  const allowed = can(P.auditView);

  const query = useApiQuery<Page<AuditEntry>>(
    allowed
      ? `/api/v1/audit/entries${buildQuery({
          limit: AUDIT_PAGE_SIZE,
          offset,
          target_type: targetType || undefined,
        })}`
      : null,
    "بارگذاری گزارش حسابرسی ناموفق بود",
    0,
    { keepPrevious: true },
  );

  if (status === "loading") return <PageSkeleton />;
  if (!allowed) return <AccessDenied what="مشاهدهٔ گزارش حسابرسی" />;

  return (
    <main className="space-y-6" data-testid="audit-page">
      <PageHeader
        title="گزارش حسابرسی"
        description="فهرست فقط‌خواندنی رویدادهای ثبت‌شده در audit_entries؛ بدون امکان ویرایش یا حذف."
      />
      <div className="flex flex-wrap items-end gap-3">
        <SelectField
          label="نوع هدف"
          data-testid="audit-target-filter"
          value={targetType}
          onChange={(event) => {
            setTargetType(event.target.value);
            setOffset(0);
          }}
        >
          {TARGET_FILTERS.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectField>
      </div>
      <QueryBoundary
        loading={query.loading && !query.data}
        error={query.error}
        deniedWhat="مشاهدهٔ گزارش حسابرسی"
        onRetry={query.reload}
      >
        {query.data && (
          <>
            <DataTable
              rowTestId="audit-row"
              rows={query.data.items}
              rowKey={(row) => row.id}
              empty={<EmptyState icon="list" title="رویدادی برای نمایش نیست" />}
              columns={[
                {
                  key: "when",
                  header: "زمان",
                  className: "tabular-nums whitespace-nowrap",
                  cell: (r) => formatTehran(r.created_at_utc),
                },
                {
                  key: "operation",
                  header: "عملیات",
                  cell: (r) => (
                    <span title={r.operation}>{operationLabel(r.operation)}</span>
                  ),
                },
                {
                  key: "actor",
                  header: "عامل",
                  cell: (r) => r.actor_login ?? r.actor_type,
                },
                {
                  key: "target",
                  header: "هدف",
                  cell: (r) => (
                    <span className="tabular-nums">
                      {targetTypeLabel(r.target_type)}
                      {r.target_id ? ` · ${r.target_id.slice(0, 8)}…` : ""}
                    </span>
                  ),
                },
              ]}
            />
            {query.data.total > AUDIT_PAGE_SIZE && (
              <Pagination
                total={query.data.total}
                limit={AUDIT_PAGE_SIZE}
                offset={offset}
                onOffsetChange={setOffset}
              />
            )}
            <p className="text-sm tabular-nums text-[color:var(--ds-text-muted)]" data-testid="audit-total">
              مجموع رویدادها: {formatCount(query.data.total)}
            </p>
          </>
        )}
      </QueryBoundary>
    </main>
  );
}
