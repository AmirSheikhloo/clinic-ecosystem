# Agent runtime evidence — Gate A M0

**Specification:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`  
**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`

## Python (Agent)

- 3.12.3

## Docker (Agent)

- NOT AVAILABLE (`docker: command not found`)

## CI evidence path

- Workflow: `.github/workflows/m0-postgres-integration.yml`
- Required suites expanded for Appendix E.1.4–E.1.10 / E.3 / E.4 closure
- Evidence guard: `.github/scripts/assert_m0_pytest_evidence.py` (27 required node ids)
- Prior accepting run (pre-remediation, 12 tests): https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/42536959128 on `2f5831c`
- Post-remediation accepting run: *pending — fill after green CI*

## Milestone implication

M0-B and M0-C require a new green CI run covering the expanded required suite before re-acceptance.
