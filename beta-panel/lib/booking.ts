/**
 * Stable booking request identity + idempotency key cache for reception desk.
 * Acknowledgement state and conflict IDs are part of the fingerprint.
 */

export type BookingIntent = {
  patientId: string;
  serviceId: string;
  resourceIds: string[];
  startLocal: string;
  durationMinutes: number;
  acknowledgeOverlap: boolean;
  acknowledgedConflictIds: string[];
};

export function bookingFingerprint(intent: BookingIntent): string {
  const normalized = [
    intent.patientId,
    intent.serviceId,
    [...intent.resourceIds].sort().join(","),
    intent.startLocal,
    String(intent.durationMinutes),
    intent.acknowledgeOverlap ? "1" : "0",
    [...intent.acknowledgedConflictIds].sort().join(","),
  ].join("|");
  let hash = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = (hash * 31 + normalized.charCodeAt(i)) >>> 0;
  }
  return `desk-${hash.toString(16)}-${normalized.length}`;
}

export class IdempotencyKeyStore {
  private readonly cache = new Map<string, string>();

  keyFor(intent: BookingIntent, createId: () => string = () => crypto.randomUUID()): string {
    const fingerprint = bookingFingerprint(intent);
    const existing = this.cache.get(fingerprint);
    if (existing) return existing;
    const created = createId();
    this.cache.set(fingerprint, created);
    return created;
  }

  clear(): void {
    this.cache.clear();
  }

  size(): number {
    return this.cache.size;
  }
}

/** Conflict ids ordered for stable fingerprints / ack payloads. */
export function sortedConflictIds(
  conflicts: Array<{ appointment_id: string }>,
): string[] {
  return conflicts.map((c) => c.appointment_id).sort();
}
