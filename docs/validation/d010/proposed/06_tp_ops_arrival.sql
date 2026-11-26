ALTER TABLE appointments
  ADD COLUMN arrived_at_utc TIMESTAMPTZ NULL,
  ADD COLUMN historical_entry_reason VARCHAR(200) NULL,
  ADD COLUMN suppress_reminders BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE appointments
  ADD CONSTRAINT appointments_arrived_chk CHECK (
    (status <> 'CHECKED_IN') OR (arrived_at_utc IS NOT NULL)
  );
