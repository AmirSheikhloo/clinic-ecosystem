"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { useSession } from "@/components/session/SessionProvider";

type Note = { id: string; body: string; pinned: boolean; created_at_utc: string };
type Tag = { id: string; tag_code: string; tag_name: string };
type Balance = {
  outstanding_irr: number;
  allocated_irr: number;
  patient_credit_irr: number;
  posted_invoices: number;
};
type InvoiceList = {
  items: Array<{
    id: string;
    invoice_number: string | null;
    financial_status: string;
    outstanding: number;
    patient_payable_total: number;
  }>;
};

export function PatientDossierOps({ patientId }: { patientId: string }) {
  const { can } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [noteBody, setNoteBody] = useState("");
  const [tagCode, setTagCode] = useState("ALERT");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const notes = useApiQuery<{ items: Note[] }>(
    can(P.patientsViewProfile) ? `/api/v1/patients/${patientId}/notes` : null,
    "بارگذاری یادداشت‌ها ناموفق بود",
    refresh,
  );
  const tags = useApiQuery<{ items: Tag[] }>(
    can(P.patientsViewProfile) ? `/api/v1/patients/${patientId}/tags` : null,
    "بارگذاری برچسب‌ها ناموفق بود",
    refresh,
  );
  const balance = useApiQuery<Balance>(
    can(P.financeInvoiceView) ? `/api/v1/finance/patients/${patientId}/balance` : null,
    "بارگذاری مانده مالی ناموفق بود",
    refresh,
  );
  const invoices = useApiQuery<InvoiceList>(
    can(P.financeInvoiceView)
      ? `/api/v1/finance/invoices${buildQuery({ patient_id: patientId, limit: 20 })}`
      : null,
    "بارگذاری صورتحساب‌ها ناموفق بود",
    refresh,
  );

  async function addNote() {
    if (!noteBody.trim() || !can(P.patientsUpdate)) return;
    setBusy(true);
    setError(null);
    const result = await apiJson(`/api/v1/patients/${patientId}/notes`, {
      method: "POST",
      body: { body: noteBody.trim() },
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setNoteBody("");
    setRefresh((v) => v + 1);
  }

  async function noteAction(noteId: string, action_kind: "PIN" | "UNPIN" | "RETRACT") {
    if (!can(P.patientsUpdate)) return;
    setBusy(true);
    setError(null);
    const result = await apiJson(`/api/v1/patients/${patientId}/notes/${noteId}/actions`, {
      method: "POST",
      body: { action_kind, reason: action_kind === "RETRACT" ? "retract_ui" : "pin_ui" },
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setRefresh((v) => v + 1);
  }

  async function addTag() {
    if (!tagCode.trim() || !can(P.patientsUpdate)) return;
    setBusy(true);
    setError(null);
    const result = await apiJson(`/api/v1/patients/${patientId}/tags`, {
      method: "POST",
      body: {
        tag_code: tagCode.trim(),
        tag_name: tagCode.trim() === "ALERT" ? "هشدار عملیاتی" : tagCode.trim(),
      },
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setRefresh((v) => v + 1);
  }

  async function removeTag(assignmentId: string) {
    if (!can(P.patientsUpdate)) return;
    setBusy(true);
    setError(null);
    const result = await apiJson(`/api/v1/patients/${patientId}/tags/${assignmentId}?reason=ui_remove`, {
      method: "DELETE",
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setRefresh((v) => v + 1);
  }

  return (
    <section className="space-y-6" data-testid="patient-dossier-ops">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      {can(P.financeInvoiceView) ? (
        <div className="ds-card space-y-3 p-4" data-testid="patient-finance">
          <h3 className="ds-section-title">وضعیت مالی</h3>
          {balance.data ? (
            <p className="text-sm tabular-nums">
              مانده {formatCount(balance.data.outstanding_irr)} · پرداخت‌شده {formatCount(balance.data.allocated_irr)} · اعتبار{" "}
              {formatCount(balance.data.patient_credit_irr)} · {formatCount(balance.data.posted_invoices)} صورتحساب
            </p>
          ) : null}
          <ul className="space-y-2">
            {(invoices.data?.items ?? []).map((inv) => (
              <li key={inv.id} className="flex justify-between gap-2 text-sm">
                <span className="tabular-nums">{inv.invoice_number ?? inv.id.slice(0, 8)}</span>
                <StatusBadge tone={inv.outstanding === 0 ? "ok" : "warn"}>{inv.financial_status}</StatusBadge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="ds-card space-y-3 p-4" data-testid="patient-notes">
        <h3 className="ds-section-title">یادداشت‌های عملیاتی</h3>
        <ul className="space-y-2 text-sm">
          {(notes.data?.items ?? []).map((n) => (
            <li key={n.id} className="rounded border border-[var(--ds-border)] px-3 py-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  {n.pinned ? <StatusBadge tone="info">سنجاق</StatusBadge> : null} {n.body}
                </div>
                {can(P.patientsUpdate) ? (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      loading={busy}
                      onClick={() => void noteAction(n.id, n.pinned ? "UNPIN" : "PIN")}
                      data-testid="note-pin"
                    >
                      {n.pinned ? "برداشتن سنجاق" : "سنجاق"}
                    </Button>
                    <Button
                      variant="ghost"
                      loading={busy}
                      onClick={() => void noteAction(n.id, "RETRACT")}
                      data-testid="note-retract"
                    >
                      جمع‌آوری
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        {can(P.patientsUpdate) ? (
          <div className="flex gap-2">
            <input
              className="ds-input flex-1"
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              placeholder="یادداشت جدید"
              data-testid="note-body"
            />
            <Button loading={busy} onClick={() => void addNote()} data-testid="note-add">
              ثبت
            </Button>
          </div>
        ) : null}
      </div>

      <div className="ds-card space-y-3 p-4" data-testid="patient-tags">
        <h3 className="ds-section-title">برچسب‌ها و هشدارها</h3>
        <div className="flex flex-wrap gap-2">
          {(tags.data?.items ?? []).map((t) => (
            <span key={t.id} className="inline-flex items-center gap-1">
              <StatusBadge tone={t.tag_code === "ALERT" ? "danger" : "info"}>{t.tag_name}</StatusBadge>
              {can(P.patientsUpdate) ? (
                <button
                  type="button"
                  className="text-xs text-[var(--ds-danger)]"
                  onClick={() => void removeTag(t.id)}
                  data-testid="tag-remove"
                >
                  حذف
                </button>
              ) : null}
            </span>
          ))}
        </div>
        {can(P.patientsUpdate) ? (
          <div className="flex gap-2">
            <input
              className="ds-input flex-1"
              value={tagCode}
              onChange={(e) => setTagCode(e.target.value)}
              data-testid="tag-code"
            />
            <Button loading={busy} onClick={() => void addTag()} data-testid="tag-add">
              افزودن برچسب
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
