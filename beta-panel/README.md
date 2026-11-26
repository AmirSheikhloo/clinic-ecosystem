# Clinic Ecosystem — BETA-01B Panel

Development-only Persian RTL reception UI with a same-origin Next.js BFF.

## Security

- Access tokens stay in HttpOnly `ce_beta_session` cookies (never `localStorage` / `sessionStorage`).
- State-changing routes require `x-csrf-token` matching the Readable `ce_beta_csrf` cookie, plus Origin checks.
- Panel fails closed unless `CLINIC_ENV` is `development` or `test` and `CLINIC_BETA_PANEL_ENABLED=1`.
- Backend URL uses server-only `CLINIC_API_BASE_URL` (not `NEXT_PUBLIC_*`).

## Run (synthetic local)

```bash
export CLINIC_ENV=development
export CLINIC_BETA_PANEL_ENABLED=1
export CLINIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run build
npm run start
```

Open `http://127.0.0.1:3100/login`.
