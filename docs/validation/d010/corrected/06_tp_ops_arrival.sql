ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS arrived_at_utc TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS historical_entry_reason VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS suppress_reminders BOOLEAN NOT NULL DEFAULT FALSE;

-- D010 Expand-and-Contract: NOT VALID until backfill completes on upgrade paths
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_arrived_chk;
ALTER TABLE appointments
  ADD CONSTRAINT appointments_arrived_chk CHECK (
    (status <> 'CHECKED_IN') OR (arrived_at_utc IS NOT NULL)
  ) NOT VALID;
