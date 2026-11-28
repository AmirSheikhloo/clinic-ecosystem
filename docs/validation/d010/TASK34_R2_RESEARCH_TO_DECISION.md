# Task 34 R2 — Research-to-decision matrix

Sources inspected during this increment. Distinguishes **official documentation**, **community anecdotes** (traceable URLs only), **engineering inference**, and **Clinic Ecosystem project decisions**. No fabricated community consensus. No blind copy of foreign legal/insurance/payment policy into Iran.

**Iran applicability:** Jane/Cliniko/Square/Shopify/Stripe insurance, tax, card-network, and fiscal-receipt rules are **not** copied. Clinic Ecosystem keeps IRR integer ledger, synthetic POS, and disabled live CARD_TO_CARD/ONLINE until Gate B.

| Source class | Finding | Source URL | Edge case | Resulting requirement | Test ID |
|---|---|---|---|---|---|
| Official | Package redemption is separate from booking; no-show may optionally redeem or charge fee | https://jane.app/guide/selling-redeeming-and-refunding-a-package | No-show with prepaid entitlement | PREPAY-02: default do not consume entitlement on no-show; any no-show fee is financial, not clinical completion | EXT-PREPAY-02 |
| Official | Return visit reminders: suggested date ≠ reminder send date; suppress when booked | https://jane.app/guide/return-visit-reminders | Booking after reminder; cancel after final reminder | RECALL-01/02: rolling from actual completion; suppress when qualifying booking exists | EXT-RECALL-01 |
| Official | Related-client payment keeps **separate invoices per service recipient**; payment listing follows the Pay-button profile; no joint clinical invoice | https://jane.app/guide/payments-for-related-clients | One payer settles multiple patients | MULTI-01/02: independent invoices/receipts per beneficiary; shared settlement feature-flagged OFF until ratified batch contract | EXT-MULTI-02 |
| Official | QZ silent print requires server-side SHA-512 signing; private key never in frontend | https://qz.io/docs/signing | Unsigned/replayed print command; key in SPA | PRINT-02: simulated adapter in preview; real QZ trust BLOCKED without cert/hardware approval | EXT-PRINT-02 |
| Official | QZ printer/job status distinguishes SPOOLING/PRINTING from PAPEROUT/OFFLINE/ERROR/UNKNOWN | https://qz.io/docs/printer-status | Spool accepted but paper-out / offline / unknown | PRINT-02: statuses QUEUED/SPOOLED/FAILED/UNKNOWN; no false hardware-success; explicit reprint | EXT-PRINT-STATUS |
| Community anecdote | QZ tray testing notes: some drivers report job complete even when paper-out; only disconnect reliably fails the job | https://github.com/qzind/tray/issues/736 | Timeout after spool acceptance; reconnect | PRINT-02: UNKNOWN ≠ success; recover via explicit retry; never re-checkout | EXT-PRINT-UNKNOWN |
| Official | Shopify POS: enrolled default receipt printer; avoid per-sale device dialogs | https://help.shopify.com/en/manual/sell-in-person/shopify-pos/receipt-management/set-default-receipt-printer | Printer changed without re-test | PRINT-02: enrollment + test print before auto-print | EXT-PRINT-02 |
| Official | Shopify POS reprint from existing order/receipt event — no new payment | https://help.shopify.com/en/manual/sell-in-person/shopify-pos/receipt-management/managing-receipts | Lost receipt; double-click print | PRINT-01: reprint from immutable snapshot; print-job id ≠ checkout idempotency | EXT-PRINT-REPRINT |
| Official | Shopify auto-print only when default printer connected; country fiscal copy rules not applicable here | https://help.shopify.com/en/manual/sell-in-person/shopify-pos/customize-pos/printed-receipts/printing-options | Auto-print while disconnected | PRINT-02: refuse auto-print when health≠ENROLLED; no silent claim | EXT-PRINT-AUTO |
| Official | Square Terminal RECEIPT action reprints with `is_duplicate` and separate idempotency key — payment unchanged | https://developer.squareup.com/docs/terminal-api/advanced-features/issue-receipts | Reprint vs original; duplicate action | PRINT-01: reprint marked as copy; finance untouched | EXT-PRINT-REPRINT |
| Official | Square API idempotency: same key → same result; same key + different payload → error | https://developer.squareup.com/docs/build-basics/common-api-patterns/idempotency | Double-click checkout; timeout retry | FIN-05: durable checkout intent UUID; payload mismatch rejected | EXT-FIN-05 |
| Official | PostgreSQL 15 unique constraints / transactional integrity | https://www.postgresql.org/docs/15/ddl-constraints.html | Double-submit checkout | FIN-05: durable UUID keys; unique evidence on settlement batches | EXT-FIN-05 |
| Official | Combobox: listbox popup, arrow/enter/escape, aria-activedescendant | https://www.w3.org/WAI/ARIA/apg/patterns/combobox/ | Keyboard-only Persian filter | DESK-02: accessible interdependent comboboxes | EXT-DESK-02 |
| Official | Apple HIG RTL: logical start for icons; do not mirror non-directional glyphs | https://developer.apple.com/design/human-interface-guidelines/right-to-left | Clipped Persian labels | UX-02: logical CSS + RTL shell | EXT-UX-02 |
| Official | Fluent 2 Drawer: overlay from opposite edge; focus trap | https://fluent2.microsoft.design/components/web/react/core/drawer/usage | Schedule scroll jump | FIN-03: left overlay finance drawer | EXT-FIN-03 |
| Official | WCAG 2.2 + reduced motion | https://www.w3.org/TR/wcag22/ | Continuous badge flash | DASH-03: ≤2 pulses then static | EXT-DASH-03 |
| Official | Cliniko recalls / appointments (feature overview) | https://help.cliniko.com/en/articles/8410284-set-up-patient-recalls | Indefinite daily spam | RECALL-02: capped cycle + quiet hours | EXT-RECALL-02 |
| Engineering inference | Spool acceptance ≠ physical print confirmation when OS/driver status is lossy | Derived from QZ status model + issue #736 observations | UNKNOWN after SPOOLED | Persist UNKNOWN; operator chooses retry/cancel/fallback; no infinite auto-retry | EXT-PRINT-UNKNOWN |
| Engineering inference | ESC/POS 80mm/58mm paper widths are printer-dependent | https://reference.epson-biz.com/modules/ref_escpos/ | Wrong width layout / clipping | PRINT-01: default 80mm, optional 58mm; test margins in simulated preview | EXT-PRINT-01 |
| Project decision | 80mm default / 58mm optional; Persian RTL compact receipt; synthetic watermark; no tax-invoice claim | Owner R2 §22 | Hardware absent on Linux agent | Simulated adapter PASS; physical/QZ NOT RUN / BLOCKED | EXT-PRINT-01 |
| Project decision | Shared multi-patient settlement remains DISABLED; one-beneficiary invoice/receipt guards preserved | ACR-D0.11 + `ACR_D0.12_SETTLEMENT_BATCH_ATTRIBUTION_CANDIDATE.md` | Parent pays for two patients | Separate invoices + batch print; settlement-batch ACR candidate only | EXT-MULTI-02 |
| Official | Carbon Data Table + Pagination: server-side paging, page-size in footer, bounded page window with ellipsis | https://carbondesignsystem.com/components/data-table/usage/ · https://carbondesignsystem.com/components/pagination/usage/ | 500 pages must not render 500 buttons | DASH-PAG-01: footer 5/10/15/20/40/50 default 10; ellipsis window | DASH-PAG-01 |
| Official | Carbon Status indicator: text + color; never color alone | https://carbondesignsystem.com/components/status-indicator/usage/ | Color-blind misread of ops badge | OPS-01: icon+text badges; shared tokens | DASH-OPS-01 |
| Official | TanStack Query: keepPreviousData / placeholderData; distinguish isLoading vs isFetching | https://tanstack.com/query/latest/docs/framework/react/guides/paginated-queries | Poll fade / empty flash | DASH-REFRESH-01: keepPrevious; no opacity fade on background refresh | DASH-REFRESH-01 |
| Official | SWR: revalidate on focus; dedupe; stale-while-revalidate | https://swr.vercel.app/docs/revalidation | Hidden-tab poll waste; focus stale | DASH-REFRESH-02: 30s poll; pause when hidden; bump on focus/online | DASH-REFRESH-02 |
| Official | WCAG 2.2 focus visible + reduced motion | https://www.w3.org/TR/wcag22/ | Continuous needs-status flash | DASH-03: ≤2 pulses then static; prefers-reduced-motion | DASH-OPS-PULSE |
| Official | Apple HIG notifications: non-blocking; do not steal focus | https://developer.apple.com/design/human-interface-guidelines/notifications | Toast during checkout | NOTIF-01: toast non-modal; center persists after dismiss | DASH-NOTIF-01 |
| Official | ARIA APG Disclosure / Dialog patterns for filter panel + notification popover | https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/ | Keyboard trap / lost focus | DASH-FILTER-01: expandable filters; Escape/outside close | DASH-FILTER-01 |
| Project decision | Five metric cards; Today non-interactive; online metric by confirmation time; review badge independent of daily count | Owner dashboard PO instruction 2026-11-28 | Online booking for next month | DASH-05 online metric + unreviewed badge | DASH-ONLINE-01 |
| Project decision | Ops labels: در انتظار / انجام‌شده / نیازمند تعیین وضعیت / لغوشده / انجام‌نشده — preserve underlying domain facts | Owner dashboard PO instruction | Elapsed time ≠ absence | OPS presentation mapping | DASH-OPS-01 |
| Engineering inference | `formatJalaliDateTime(...).split(" ")[0]` yields day-only when fa-IR medium inserts spaces | Derived from Intl fa-IR + Latin digit conversion | Top-bar clock showed `7 · 14:34` | Use `formatJalaliDate` + explicit Tehran time suffix | DASH-CLOCK-01 |

## Executable edge-case tests produced by this research

| Test ID | Assertion |
|---|---|
| EXT-PRINT-01 | `buildThermalReceiptText` 80/58mm RTL Persian; synthetic marker; no national-id phrasing |
| EXT-PRINT-02 | Enrollment + test print required before auto-print; QZ path returns BLOCKED |
| EXT-PRINT-STATUS | Simulated failed/disconnected → FAILED; unknown → UNKNOWN; hardwareClaim=`none` |
| EXT-PRINT-REPRINT | `reprintJob` uses prior snapshot; new job id; checkout not invoked |
| EXT-PRINT-AUTO | Duplicate `autoIntentKey` after refresh → FAILED without finance mutation |
| EXT-PRINT-BATCH | `submitBatchPrintJobs` emits independent per-patient jobs under one batch id |
| EXT-FIN-05 | Checkout intent store: same fingerprint → same key; payload change → new key |
| EXT-MULTI-02 | Feature flag shared settlement OFF; one-beneficiary allocation guard remains |
| DASH-PAG-01 | Page sizes 5/10/15/20/40/50; default 10; ellipsis window for large page counts |
| DASH-REFRESH-01 | Background refresh does not set DataTable busy opacity |
| DASH-ONLINE-01 | online_bookings_today by created_at; unreviewed backlog across midnight |
| DASH-OPS-01 | operationalPresentation maps CONFIRMED→در انتظار, NO_SHOW→انجام‌نشده |
| DASH-CLOCK-01 | Top bar clock contains month name + year + «به وقت تهران» |
| DASH-NOTIF-01 | Notification read ≠ online booking review |

## SOURCE_UNAVAILABLE / NOT RUN

- Square Appointments deep package-management pages beyond Terminal RECEIPT + idempotency docs: not required for print/settlement decisions this tip; marketing pages treated as secondary.
- Physical thermal hardware + real QZ certificate/signing on Windows workstation: **NOT RUN** in Linux agent (genuine external blocker).
- Reddit/LinkedIn clinic-admin threads: **not cited**. Prior generic row without URLs removed; do not invent social-media research. Where community signal was needed for printer uncertainty, the traceable QZ Tray GitHub issue above is used instead.
