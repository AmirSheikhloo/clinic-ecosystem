# BETA-01B synthetic demo procedure (disposable data only)

Prerequisites: PostgreSQL 15 with TP0001–TP0007 applied, `tp_app_login` runtime role, Docker available for seeding.

1. Seed synthetic reception fixtures (migrator role), capturing `tenant_a_id` and receptionist credentials from `tests/integration/beta01b_seed.py`.
2. Start API with realm enabled for that tenant:

```bash
export CLINIC_ENV=development
export CLINIC_BETA_AUTH_REALM_ENABLED=1
export CLINIC_BETA_AUTH_REALM_TENANT_ID=<tenant_a_id>
export CLINIC_ACCESS_TOKEN_SIGNING_SECRET=<32+-char-dev-secret>
export CLINIC_DATABASE_URL=postgresql+asyncpg://tp_app_login:<pwd>@127.0.0.1:5432/tenant_app
uvicorn clinic_ecosystem.presentation.http.app:create_app --factory --port 8000
```

3. Start Beta panel BFF:

```bash
cd beta-panel
export CLINIC_ENV=development
export CLINIC_BETA_PANEL_ENABLED=1
export CLINIC_API_BASE_URL=http://127.0.0.1:8000
npm run start
```

4. Open `http://127.0.0.1:3100/login`, sign in as `receptionist@beta01b.test`.
5. On Desk: search/register a synthetic patient (name only), select service + eligible resource, pick Tehran local time, submit once.
6. Confirm appointment ID appears; open Daily list and filter the same calendar day.
7. Logout; verify expired-session redirect by clearing cookies or waiting for TTL.

Do not use real patient identifiers. Do not point the panel at production.
