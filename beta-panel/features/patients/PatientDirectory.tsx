"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SearchField } from "@/components/forms/SearchField";
import { SelectField } from "@/components/forms/SelectField";
import { DataTable, type DataTableColumn } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { useSession } from "@/components/session/SessionProvider";
import { buildQuery } from "@/lib/api";
import { formatJalaliDate, formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { P } from "@/lib/permissions";
import { clampOffset } from "@/lib/pagination";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { useDebouncedValue } from "@/lib/use-debounced";
import { PATIENT_PAGE_SIZE, type PatientRow, type PatientStatusFilter } from "./types";

type Props = { refreshToken: number };

export function PatientDirectory({ refreshToken }: Props) {
  const { can } = useSession();
  const canProfile = can(P.patientsViewProfile);
  const canBook = can(P.appointmentsSchedule);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<PatientStatusFilter>("active");
  const [offset, setOffset] = useState(0);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const debounced = useDebouncedValue(draft.trim(), 350);
  const q = submitted ?? debounced;

  const path = `/api/v1/patients/directory${buildQuery({ q, status, limit: PATIENT_PAGE_SIZE, offset })}`;
  const query = useApiQuery<Page<PatientRow>>(path, "جستجوی بیمار ناموفق بود", refreshToken, { keepPrevious: true });

  function submit(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setSubmitted(draft.trim());
  }

  const columns: DataTableColumn<PatientRow>[] = [
    {
      key: "name",
      header: "بیمار",
      cell: (row) => (
        <span className="block truncate font-medium">
          {canProfile ? (
            <Link href={`/patients/${row.patient_profile_id}`} className="hover:underline" title={`${row.first_name} ${row.last_name}`}>
              {row.first_name} {row.last_name}
            </Link>
          ) : (
            `${row.first_name} ${row.last_name}`
          )}
        </span>
      ),
    },
    { key: "dossier", header: "شماره پرونده", width: "9rem", cell: (row) => row.dossier_number ?? "—", className: "tabular-nums" },
    {
      key: "birth",
      header: "تاریخ تولد",
      width: "9rem",
      cell: (row) => (row.birth_date ? formatJalaliFromTehranYmd(row.birth_date) : "—"),
      className: "tabular-nums",
    },
    { key: "created", header: "تاریخ ثبت", width: "9rem", cell: (row) => formatJalaliDate(row.created_at_utc), className: "tabular-nums" },
    { key: "status", header: "وضعیت", width: "6.5rem", cell: (row) => <ActiveBadge active={row.is_active} /> },
    {
      key: "actions",
      header: "",
      width: "11rem",
      className: "text-end whitespace-nowrap",
      cell: (row) => (
        <span className="inline-flex items-center gap-1">
          {canProfile ? (
            <Link href={`/patients/${row.patient_profile_id}`} className="ds-btn ds-btn-subtle ds-btn-sm" data-testid="patients-open-profile">
              پرونده
            </Link>
          ) : null}
          {canBook && row.is_active ? (
            <Link href={`/desk?patient=${row.patient_profile_id}`} className="ds-btn ds-btn-ghost ds-btn-sm" data-testid="patients-book">
              نوبت‌دهی
            </Link>
          ) : null}
        </span>
      ),
    },
  ];

  const data = query.data;
  const safeOffset = data ? clampOffset(data.total, PATIENT_PAGE_SIZE, offset) : offset;

  return (
    <section className="space-y-4" aria-label="فهرست بیماران">
      <form onSubmit={submit} className="ds-card ds-filter-grid p-3">
        <div className="ds-filter-wide">
          <SearchField
            label="جستجو"
            value={draft}
            maxLength={120}
            busy={query.loading || query.refreshing}
            onValueChange={(value) => {
              setSubmitted(null);
              setOffset(0);
              setDraft(value);
            }}
            placeholder="نام، نام خانوادگی یا شماره پرونده"
            aria-label="جستجو در بیماران"
            data-testid="patients-search-query"
          />
        </div>
        {canProfile ? (
          <SelectField
            label="وضعیت"
            value={status}
            data-testid="patients-status-filter"
            onChange={(e) => {
              setOffset(0);
              setStatus(e.target.value as PatientStatusFilter);
            }}
          >
            <option value="active">فعال</option>
            <option value="inactive">غیرفعال</option>
            <option value="all">همه</option>
          </SelectField>
        ) : null}
        <Button type="submit" variant="ghost" icon="search" data-testid="patients-search-submit">جستجو</Button>
      </form>

      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مشاهدهٔ فهرست بیماران" onRetry={query.reload}>
        {data ? (
          <>
            <DataTable
              columns={columns}
              rows={data.items}
              rowKey={(row) => row.patient_profile_id}
              rowTestId="patients-result-row"
              busy={query.refreshing}
              minWidth="46rem"
              empty={
                <EmptyState
                  icon="patients"
                  title="بیماری یافت نشد"
                  description={q ? "عبارت جستجو یا فیلتر وضعیت را تغییر دهید." : "هنوز بیماری ثبت نشده است؛ با دکمهٔ «بیمار جدید» ثبت کنید."}
                />
              }
            />
            {data.total > 0 ? (
              <Pagination total={data.total} limit={PATIENT_PAGE_SIZE} offset={safeOffset} onOffsetChange={setOffset} />
            ) : null}
          </>
        ) : null}
      </QueryBoundary>
    </section>
  );
}
