# Clinic Ecosystem — Permanent Engineering Standards

**Scope:** Applies to all new and modified code in this repository’s non-production beta panel and related application increments.  
**Authority:** Product Owner instruction (accelerated implementation standards). Does not amend frozen `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`.

## Architecture

- Respect Clean Architecture: Domain, Application, Infrastructure, Presentation/UI.
- Feature-oriented modules; single responsibility; composition over duplication.
- Avoid circular dependencies, unexplained magic values, and unnecessary abstraction.
- Preserve security contracts: HttpOnly cookies, CSRF, origin checks, RBAC, tenant isolation, RLS, audit, idempotency.

## File size guidance

- Prefer small cohesive files (components ~30–200 lines; hooks ~30–150; services ~50–250).
- Review files over ~300 lines for decomposition without sacrificing cohesion.
- Generated files, lockfiles, migrations, and cohesive fixtures may exceed guidelines.

## Frontend organization

Prefer scalable folders: `app/`, `features/`, `components/{ui,layout,forms,tables,feedback,navigation}/`, `design-system` tokens via CSS variables, `hooks/`, `lib/{api,dates,formatters,validation,errors}/`, `config/`, `types/`, `assets/`.

Pages compose features; do not invent unsupported backend contracts.

## Design system

- Centralize semantic tokens in `beta-panel/design-system/` (`tokens.css`, `base.css`, `components.css`, `motion.css`) imported from `app/globals.css`.
- Shared primitives: `components/ui/`, `components/forms/`, `components/tables/`, `components/feedback/`, `components/layout/`.
- Feature modules own their views under `features/{reception,dashboard,patients,appointments,catalog}/`.
- Global themes (Ocean, Midnight, Emerald, Graphite) with light/dark appearance.
- Theme preference may use `localStorage`; **never** store patient PII or auth tokens there.

## Persian UI / Latin digits (strict)

- All Persian UI is RTL.
- Display digits must be Latin `0–9` only (`numberingSystem: "latn"` / `toLatinDigits`).
- Keep Jalali calendar semantics and Asia/Tehran wall time; keep Gregorian/UTC API/DB contracts.
- Centralize date/number formatters; add regression tests for Jalali+Latin digits.

## Motion

- Use CSS token durations; respect `prefers-reduced-motion`.
- Preserve keyboard focus, dialog semantics, and immediate interaction.

## Performance & reliability

- Avoid unnecessary client components, duplicate fetches, and unsafe caching of tenant data.
- Correct authorization and transaction integrity always beat premature optimization.

## Testing

- Run unit, typecheck, lint, build, PG15 integration, and Playwright E2E in batches.
- Do not silently skip required suites or claim PASS without execution evidence.
