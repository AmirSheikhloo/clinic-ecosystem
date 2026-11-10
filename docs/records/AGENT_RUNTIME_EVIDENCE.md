# Agent runtime evidence — Gate A M0

**Feature branch:** `cursor/gate-a-m0-bootstrap-95a4`

## Agent environment

- Python: 3.12.3
- Docker: **NOT AVAILABLE** (`NOT RUN LOCALLY` for Testcontainers)

## CI (post final security remediation)

- Workflow: `.github/workflows/m0-postgres-integration.yml`
- Required node ids: **38**
- Green push run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/42882396949
- Commit: `3598011896017d6ec210282b2ce11eb9087a36f8`
- Result: **38 passed, 0 skipped, 0 failed**

## Milestone implication

CI is green for the remediation suite. **M0-B / M0-C are not auto-accepted** — awaiting human review of this evidence. E.1.7 backup/restore identities remain deferred.
