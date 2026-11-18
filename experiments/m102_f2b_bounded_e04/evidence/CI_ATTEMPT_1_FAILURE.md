# E0.4 CI attempt 1 — failure (non-security harness)

- Run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44293883965
- Event: push; SHA: 2a561cb0413de79991c99047d8c6ecb423da5d53
- Result: 4 failed / 28 passed / 0 skipped (32 pytest functions)
- Classification: **NON_SECURITY_HARNESS** (authorized for one corrective attempt)
- Root causes:
  1. A05 still asserted historical `experiment/m102-f2b-e03-*` branch filter string after e04 port
  2. Cascaded missing `E03-A05-C01` blocked staged C01 + V02/V04
- Security negatives that passed: A01, A02, A03, A04, A06, A08, REG, most E04-V* denials
- No STOP_SECURITY / privilege fallback / forbidden success observed
