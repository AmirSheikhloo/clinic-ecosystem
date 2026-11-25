"use client";

import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehran } from "@/lib/client";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
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
          className: "tabular-nums whitespace-nowrap",
          cell: (item) => (
            <span title={formatTehran(item.scheduled_start_at_utc)}>
              {formatTehranTime(item.scheduled_start_at_utc)} – {formatTehranTime(item.scheduled_end_at_utc)}
            </span>
          ),
        },
        {
          key: "patient",
          header: "بیمار",
          className: "font-medium",
          cell: (item) => `${item.patient_first_name} ${item.patient_last_name}`,
        },
        { key: "service", header: "خدمت", cell: (item) => item.service_name },
        {
          key: "status",
          header: "وضعیت",
          cell: (item) => <StatusBadge tone={appointmentStatusTone(item.status)}>{appointmentStatusLabel(item.status)}</StatusBadge>,
        },
        {
          key: "open",
          header: "",
          className: "text-end",
          cell: (item) =>
            onOpen ? (
              <Button variant="subtle" size="sm" onClick={() => onOpen(item)} data-testid="appointment-open">
                جزئیات
              </Button>
            ) : null,
        },
      ]}
    />
  );
}
