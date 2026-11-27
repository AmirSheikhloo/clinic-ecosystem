# Task 34 R2 — Product Owner demonstration guide

## Windows one-command preview

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_preview.ps1
```

After readiness, the launcher opens the actual panel URL (not a hardcoded port). Credentials file path is printed (`PREVIEW_URL.txt` / `runtime/preview.env`).

## Stable demo roles (isolated preview only)

When `CLINIC_DEMO_ALIASES_ENABLED=1` (set by the preview stack):

| Alias | Persian label | Password |
|---|---|---|
| owner | مالک کلینیک | `Clinic123!` |
| manager | مدیر | `Clinic123!` |
| deputy | جانشین مدیر | `Clinic123!` |
| head | سرپرست پذیرش | `Clinic123!` |
| receptionist | پذیرشگر عمومی | `Clinic123!` |
| limited | پذیرشگر محدود | `Clinic123!` |
| doctor | پزشک (نمونه ورود) | `Clinic123!` |
| clerk | منشی بدون مجوز | `Clinic123!` |

Use the Persian role selector on `/login`, or type the alias + shared password. Normal email logins remain available for automated tests.

## Preseeded scenarios to try

1. **Reception desk** — `/desk`: identify patient, multi-service cart, cashier with discount / partial pay / accept excess credit.
2. **Dashboard** — `/dashboard`: three quick actions, four metric cards filtering today's table, needs-status badge.
3. **Appointments** — `/appointments`: Jalali day/week/month; lifecycle complete/no-show/cancel.
4. **Patient dossier** — `/patients`: notes, tags, invoices.
5. **Finance / inventory / audit** — manager/owner roles; audit shows allowlisted details only.
6. **Print** — after checkout success, simulated thermal text is available (no hardware claim).

## Explicitly disabled / blocked

- Shared multi-patient single-inflow settlement (feature flag OFF until ACR ratification).
- Live CARD_TO_CARD / ONLINE / real notifications / prepaid forfeiture.
- Canonical patient merge; official Alembic beyond TP0007.
