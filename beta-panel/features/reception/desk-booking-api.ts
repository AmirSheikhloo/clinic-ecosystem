import {
  apiFetch,
  extractOverlapConflicts,
  tehranLocalToUtcIso,
  type ApiErrorBody,
  type BookingIntent,
  type OverlapConflict,
} from "@/lib/client";
import type { GroupBookingIntent } from "@/lib/booking";

export type BookingResponseBody = ApiErrorBody & {
  appointment_id?: string;
  replayed?: boolean;
  status?: string;
};

export type GroupBookingResponseBody = ApiErrorBody & {
  lines?: Array<{ client_line_id: string; appointment_id: string; status: string }>;
  replayed?: boolean;
};

export async function postManualAppointment(
  intent: BookingIntent,
  idempotencyKey: string,
) {
  const startIso = tehranLocalToUtcIso(intent.startLocal);
  const end = new Date(new Date(startIso).getTime() + intent.durationMinutes * 60_000);
  const response = await apiFetch("/api/appointments", {
    method: "POST",
    csrf: true,
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      beneficiary_patient_id: intent.patientId,
      service_id: intent.serviceId,
      resource_ids: intent.resourceIds,
      start_at_utc: startIso,
      end_at_utc: end.toISOString(),
      booking_channel: "MANUAL_STAFF",
      capacity_pool: "MANUAL",
      acknowledge_overlap: intent.acknowledgeOverlap,
      acknowledged_conflict_ids: intent.acknowledgedConflictIds,
      immediate_check_in: !!intent.immediateCheckIn,
    }),
  });
  const data = (await response.json().catch(() => ({}))) as BookingResponseBody;
  return {
    response,
    data,
    startIso,
    conflicts: extractOverlapConflicts(data) as OverlapConflict[] | null,
  };
}

export async function postGroupAppointments(
  intent: GroupBookingIntent,
  idempotencyKey: string,
) {
  const lines = intent.lines.map((line) => {
    const startIso = tehranLocalToUtcIso(line.startLocal);
    const end = new Date(new Date(startIso).getTime() + line.durationMinutes * 60_000);
    return {
      client_line_id: line.clientLineId,
      service_id: line.serviceId,
      resource_ids: line.resourceIds,
      start_at_utc: startIso,
      end_at_utc: end.toISOString(),
      acknowledge_overlap: line.acknowledgeOverlap,
      acknowledged_conflict_ids: line.acknowledgedConflictIds,
      startIso,
    };
  });
  const response = await apiFetch("/api/v1/appointments/group", {
    method: "POST",
    csrf: true,
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      beneficiary_patient_id: intent.patientId,
      immediate_check_in: !!intent.immediateCheckIn,
      booking_channel: "MANUAL_STAFF",
      capacity_pool: "MANUAL",
      lines: lines.map(({ startIso: _s, ...rest }) => rest),
    }),
  });
  const data = (await response.json().catch(() => ({}))) as GroupBookingResponseBody;
  return {
    response,
    data,
    lines,
    lineConflicts: extractGroupLineConflicts(data),
  };
}

/** Per-line conflicts from atomic group 409 (keyed by client_line_id). */
export function extractGroupLineConflicts(
  data: ApiErrorBody,
): Record<string, OverlapConflict[]> | null {
  const detail = data.detail;
  const root =
    detail && typeof detail === "object"
      ? (detail as { error?: string; line_conflicts?: Record<string, OverlapConflict[]> })
      : null;
  const error =
    root?.error
    || data.error
    || (typeof detail === "object" && detail && "error" in detail
      ? String((detail as { error?: string }).error)
      : undefined);
  if (error !== "manual_overlap_acknowledgement_required") return null;
  const map = root?.line_conflicts;
  if (map && typeof map === "object") return map;
  // Fallback: single-line conflicts shape should not apply to group, but keep empty map.
  return {};
}
