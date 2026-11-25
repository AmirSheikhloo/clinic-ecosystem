"use client";

import Link from "next/link";
import { useState } from "react";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { DataTable } from "@/components/tables/DataTable";
import { Card } from "@/components/ui/Card";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { formatTehran, tehranYmdOf } from "@/lib/client";
import { appointmentStatusLabel } from "@/lib/format/status";
import type { Page } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";
import type { PatientHistoryItem } from "./types";

const SIZE = 10;

export function PatientHistory({ patientId }: { patientId: string }) {
  const [offset, setOffset] = useState(0);
  const query = useApiQuery<Page<PatientHistoryItem>>(
    `/api/v1/patients/${patientId}/appointments${buildQuery({ limit: SIZE, offset })}`,
    "بارگذاری سابقه نوبت‌ها ناموفق بود",
  );
  const data = query.data;
  return (
    <Card className="space-y-3" data-testid="patient-history">
      <h3 className="font-semibold">سابقهٔ نوبت‌ها و خدمات</h3>
      <QueryBoundary loading={query.loading && !data} error={query.error} deniedWhat="مشاهدهٔ سابقهٔ نوبت‌ها" onRetry={query.reload}>
        {data && (
          <>
            <DataTable
              rowTestId="patient-history-row"
              rows={data.items}
              rowKey={(row) => row.appointment_id}
              empty={<EmptyState title="هنوز نوبتی برای این بیمار ثبت نشده است" />}
              columns={[
                { key: "time", header: "زمان (جلالی)", cell: (r) => formatTehran(r.scheduled_start_at_utc), className: "tabular-nums" },
                { key: "service", header: "خدمت", cell: (r) => r.service_name },
                { key: "channel", header: "کانال", cell: (r) => (r.booking_channel === "MANUAL" ? "دستی" : "آنلاین") },
                { key: "status", header: "وضعیت", cell: (r) => <StatusBadge>{appointmentStatusLabel(r.status)}</StatusBadge> },
                {
                  key: "calendar",
                  header: "",
                  cell: (r) => (
                    <Link
                      className="text-[var(--ds-primary)] hover:underline"
                      href={`/appointments?date=${tehranYmdOf(r.scheduled_start_at_utc)}`}
                      data-testid="history-calendar-link"
                    >
                      تقویم
                    </Link>
                  ),
                },
              ]}
            />
            {data.total > SIZE && <Pagination total={data.total} limit={SIZE} offset={offset} onOffsetChange={setOffset} />}
          </>
        )}
      </QueryBoundary>
    </Card>
  );
}
