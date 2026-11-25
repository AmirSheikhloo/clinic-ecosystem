"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SelectField } from "@/components/forms/SelectField";
import { DataTable, type DataTableColumn } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { useSession } from "@/components/session/SessionProvider";
import { buildQuery } from "@/lib/api";
import { formatJalaliDate } from "@/lib/format/jalali";
import { P } from "@/lib/permissions";
import { clampOffset } from "@/lib/pagination";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import { PATIENT_PAGE_SIZE, type PatientRow, type PatientStatusFilter } from "./types";

type Props = {
  selectedId: string | null;
  onSelect: (patient: PatientRow) => void;
  refreshToken: number;
};

export function PatientDirectory({ selectedId, onSelect, refreshToken }: Props) {
  const { can } = useSession();
  const canProfile = can(P.patientsViewProfile);
  const [draft, setDraft] = useState("");
  const [filters, setFilters] = useState<{ q: string; status: PatientStatusFilter }>({
    q: "",
    status: "active",
  });
  const [offset, setOffset] = useState(0);

  const path = `/api/v1/patients/directory${buildQuery({
    q: filters.q,
    status: filters.status,
    limit: PATIENT_PAGE_SIZE,
    offset,
  })}`;
  const query = useApiQuery<Page<PatientRow>>(path, "جستجوی بیمار ناموفق بود", refreshToken);

  function submit(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setFilters((current) => ({ ...current, q: draft.trim() }));
  }

  const columns: DataTableColumn<PatientRow>[] = [
    {
      key: "name",
      header: "بیمار",
      cell: (row) => (
        <button
          type="button"
          className={`text-right font-medium hover:underline ${
            selectedId === row.patient_profile_id ? "text-[var(--ds-primary-strong)]" : ""
          }`}
          aria-pressed={selectedId === row.patient_profile_id}
          onClick={() => onSelect(row)}
        >
          {row.first_name} {row.last_name}
        </button>
      ),
    },
    { key: "dossier", header: "شماره پرونده", cell: (row) => row.dossier_number ?? "—", className: "tabular-nums" },
    {
      key: "birth",
      header: "تولد (جلالی)",
      cell: (row) => (row.birth_date ? formatJalaliDate(`${row.birth_date}T12:00:00Z`) : "—"),
      className: "tabular-nums",
    },
    { key: "status", header: "وضعیت", cell: (row) => <ActiveBadge active={row.is_active} /> },
    {
      key: "open",
      header: "",
      cell: (row) =>
        canProfile ? (
          <Link
            href={`/patients/${row.patient_profile_id}`}
            className="text-[var(--ds-primary)] hover:underline"
            data-testid="patients-open-profile"
          >
            پرونده
          </Link>
        ) : null,
    },
  ];

  const data = query.data;
  const safeOffset = data ? clampOffset(data.total, PATIENT_PAGE_SIZE, offset) : offset;

  return (
    <section className="space-y-4" aria-label="فهرست بیماران">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
        <div className="min-w-48 flex-1">
          <label className="block space-y-1 text-sm">
            <span className="ds-field-label">نام، نام خانوادگی یا شماره پرونده</span>
            <input
              className="ds-input"
              value={draft}
              maxLength={120}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="جستجو در بیماران"
              aria-label="جستجو در بیماران"
              data-testid="patients-search-query"
            />
          </label>
        </div>
        {canProfile && (
          <SelectField
            label="وضعیت"
            value={filters.status}
            data-testid="patients-status-filter"
            onChange={(e) => {
              setOffset(0);
              setFilters((current) => ({ ...current, status: e.target.value as PatientStatusFilter }));
            }}
          >
            <option value="active">فعال</option>
            <option value="inactive">غیرفعال</option>
            <option value="all">همه</option>
          </SelectField>
        )}
        <Button type="submit">جستجو</Button>
      </form>

      <QueryBoundary
        loading={query.loading && !data}
        error={query.error}
        deniedWhat="مشاهدهٔ فهرست بیماران"
        onRetry={query.reload}
      >
        {data && (
          <>
            <DataTable
              columns={columns}
              rows={data.items}
              rowKey={(row) => row.patient_profile_id}
              rowTestId="patients-result-row"
              empty={
                <EmptyState
                  title="بیماری یافت نشد"
                  description={
                    filters.q
                      ? "عبارت جستجو یا فیلتر وضعیت را تغییر دهید."
                      : "هنوز بیماری ثبت نشده است؛ از فرم کنار صفحه ثبت کنید."
                  }
                />
              }
            />
            {data.total > 0 && (
              <Pagination
                total={data.total}
                limit={PATIENT_PAGE_SIZE}
                offset={safeOffset}
                onOffsetChange={setOffset}
              />
            )}
          </>
        )}
      </QueryBoundary>
    </section>
  );
}
