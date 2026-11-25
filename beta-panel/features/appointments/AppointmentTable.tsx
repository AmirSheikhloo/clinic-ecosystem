"use client";

import { DataTable } from "@/components/tables/DataTable";
import { formatTehran } from "@/lib/client";
import { appointmentStatusLabel } from "@/lib/format/status";
import type { AppointmentItem } from "./types";

type Props = {
  items: AppointmentItem[];
  onOpen?: ((item: AppointmentItem) => void) | null;
};

export function AppointmentTable({ items, onOpen }: Props) {
  return (
    <DataTable
      rows={items}
      rowKey={(row) => row.appointment_id}
      rowTestId="appointment-row"
      columns={[
        {
          key: "time",
          header: "زمان",
          className: "tabular-nums",
          cell: (item) => formatTehran(item.scheduled_start_at_utc),
        },
        {
          key: "patient",
          header: "بیمار",
          cell: (item) => `${item.patient_first_name} ${item.patient_last_name}`,
        },
        {
          key: "service",
          header: "خدمت",
          cell: (item) => item.service_name,
        },
        {
          key: "status",
          header: "وضعیت",
          cell: (item) => appointmentStatusLabel(item.status),
        },
        {
          key: "open",
          header: "",
          cell: (item) =>
            onOpen ? (
              <button
                type="button"
                className="text-[var(--ds-primary)] hover:underline"
                onClick={() => onOpen(item)}
                data-testid="appointment-open"
              >
                جزئیات
              </button>
            ) : null,
        },
      ]}
    />
  );
}
