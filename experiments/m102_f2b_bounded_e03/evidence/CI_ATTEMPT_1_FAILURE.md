# E0.3 CI attempt 1 — failure (non-security harness)

- Run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44111930395
- Event: push
- SHA: 29b622003f178e90e7670ba0de068a03ec9acd8d
- Result: 9 failed, 9 passed, 0 skipped
- Classification: **NON_SECURITY_HARNESS** (authorized for one corrective attempt)
- Root causes observed:
  1. `alembic.autocommit_block()` AssertionError `_transaction is not None` during Phase-6
  2. A03 overlapping-writer Barrier+FOR UPDATE deadlock/lock_timeout
  3. Cascaded missing evidence for A07-C01
- Security negatives that passed: A01-P01, A01-N01, A03-N01, A05-C01, A06-N02, A08-N01, A08-P01, REG-P01, A07-C02
- No forbidden operation success; no STOP_SECURITY privilege fallback observed
