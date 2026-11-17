# E0.3 CI attempt 2 — failure (authorized corrective; non-security)

- Run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44112675849
- Event: push
- SHA: 3c63e93846e7a79e6700414ab891fc5e3d983427
- Result: **17 passed, 1 failed, 0 skipped** (18 pytest functions)
- Failed test: `test_e03_zz_a07_c01_evidence_schema`
- Classification: **NON_SECURITY_HARNESS** (A07-C01 checked for its own evidence file before writing it)
- **No further CI attempt authorized** under D0.1 (max 1 initial + 1 corrective).
- Physical/governance writers for A01–A06, A05, A08, REG, CLOSE, A07-C02 produced OBSERVED_PASS evidence JSON in this run's artifact.
- `E03-A07-C01.json` was written with classification `OBSERVED_FAIL` recording `missing E03-A07-C01` (self-ordering defect), then the pytest assertion failed the job.
