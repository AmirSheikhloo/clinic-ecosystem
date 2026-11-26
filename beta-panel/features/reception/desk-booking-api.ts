import {
  apiFetch,
  extractOverlapConflicts,
  tehranLocalToUtcIso,
  type ApiErrorBody,
  type BookingIntent,
  type OverlapConflict,
} from "@/lib/client";

export type BookingResponseBody = ApiErrorBody & { appointment_id?: string; replayed?: boolean };

export async function postManualAppointment(intent: BookingIntent, idempotencyKey: string) {
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
    }),
  });
  const data = (await response.json().catch(() => ({}))) as BookingResponseBody;
  return { response, data, startIso, conflicts: extractOverlapConflicts(data) as OverlapConflict[] | null };
}
