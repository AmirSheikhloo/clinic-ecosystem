"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/feedback/Toast";
import { apiJson } from "@/lib/api";
import { P } from "@/lib/permissions";
import { useSession } from "@/components/session/SessionProvider";
import type { CalendarItem } from "./types";

type Props = {
  items: CalendarItem[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onChanged: () => void;
};

type BulkAction = "complete" | "no-show" | "cancel";

/**
 * Bulk completion / no-show / cancel for list management (APPT-01 extension).
 * Ordinary single completion remains on the details dialog — this is additive.
 * Does not fabricate arrival times.
 */
export function BulkAppointmentOps({ items, selectedIds, onSelectionChange, onChanged }: Props) {
  const { can } = useSession();
  const toast = useToast();
  const [busy, setBusy] = useState<BulkAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [groupId, setGroupId] = useState("");

  const selected = items.filter((i) => selectedIds.includes(i.appointment_id));
  const canComplete = can(P.appointmentsComplete);
  const canNoShow = can(P.appointmentsMarkNoShow);
  const canCancel = can(P.appointmentsCancel);

  async function run(action: BulkAction) {
    if (!selected.length || busy) return;
    setBusy(action);
    setError(null);
    let ok = 0;
    let fail = 0;
    for (const row of selected) {
      const path =
        action === "complete"
          ? `/api/v1/appointments/${row.appointment_id}/complete`
          : action === "no-show"
            ? `/api/v1/appointments/${row.appointment_id}/no-show`
            : `/api/v1/appointments/${row.appointment_id}/cancel`;
      const result = await apiJson(path, {
        method: "POST",
        version: row.aggregate_version,
        body: action === "cancel" ? { reason: "BULK_CANCEL" } : undefined,
        idempotencyKey: `bulk-${action}-${row.appointment_id}-${row.aggregate_version}`,
        fallbackMessage: "عملیات گروهی ناموفق بود",
      });
      if (result.ok) ok += 1;
      else fail += 1;
    }
    setBusy(null);
    onSelectionChange([]);
    onChanged();
    if (fail === 0) toast.success(`${ok} نوبت با موفقیت به‌روز شد`);
    else setError(`${ok} موفق · ${fail} ناموفق`);
  }

  function navigateGroup() {
    const q = groupId.trim();
    if (!q) return;
    // Group reception navigation: filter list deep-link by reception group query param when known.
    window.location.assign(`/appointments?view=list&group=${encodeURIComponent(q)}`);
  }

  if (!canComplete && !canNoShow && !canCancel) return null;

  return (
    <section
      className="ds-card flex flex-wrap items-end gap-3 p-3"
      aria-label="عملیات گروهی نوبت‌ها"
      data-testid="bulk-appointment-ops"
    >
      <p className="text-sm text-[var(--ds-text-muted)]">
        انتخاب‌شده: <span className="tabular-nums font-medium text-[var(--ds-text)]">{selectedIds.length}</span>
      </p>
      {canComplete ? (
        <Button
          size="sm"
          disabled={!selected.length || !!busy}
          loading={busy === "complete"}
          onClick={() => void run("complete")}
          data-testid="bulk-complete"
        >
          تکمیل گروهی
        </Button>
      ) : null}
      {canNoShow ? (
        <Button
          size="sm"
          variant="danger"
          disabled={!selected.length || !!busy}
          loading={busy === "no-show"}
          onClick={() => void run("no-show")}
          data-testid="bulk-no-show"
        >
          عدم حضور گروهی
        </Button>
      ) : null}
      {canCancel ? (
        <Button
          size="sm"
          variant="danger"
          disabled={!selected.length || !!busy}
          loading={busy === "cancel"}
          onClick={() => void run("cancel")}
          data-testid="bulk-cancel"
        >
          لغو گروهی
        </Button>
      ) : null}
      <label className="ms-auto flex items-end gap-2 text-sm">
        <span>
          گروه پذیرش
          <input
            className="ds-input mt-1 w-40"
            placeholder="شناسه گروه"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
            data-testid="group-reception-id"
          />
        </span>
        <Button size="sm" variant="ghost" disabled={!groupId.trim()} onClick={navigateGroup} data-testid="group-reception-nav">
          نمایش گروه
        </Button>
      </label>
      {error ? <Alert tone="danger">{error}</Alert> : null}
    </section>
  );
}
