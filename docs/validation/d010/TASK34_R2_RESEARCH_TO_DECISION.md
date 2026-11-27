# Task 34 R2 — Research-to-decision matrix

Sources inspected during this increment. Distinguishes verified official documentation, engineering inference, and Clinic Ecosystem project decisions. **No invented social-media research.** Anecdotal forum claims without stable URLs are omitted.

| Finding | Source class | Source URL | Edge case | Resulting requirement | Test ID |
|---|---|---|---|---|---|
| Package redemption is separate from booking; no-show may optionally redeem or charge fee | Official docs | https://jane.app/guide/selling-redeeming-and-refunding-a-package | No-show with prepaid entitlement | PREPAY-02: default do not consume entitlement on no-show; any no-show fee is financial, not clinical completion | EXT-PREPAY-02 |
| Return visit reminders: suggested date ≠ reminder send date; suppress when booked | Official docs | https://jane.app/guide/return-visit-reminders | Booking after reminder; cancel after final reminder | RECALL-01/02: rolling from actual completion; suppress when qualifying booking exists | EXT-RECALL-01 |
| QZ silent print requires server-side SHA-512 signing; private key never in frontend | Official docs | https://qz.io/docs/signing | Unsigned/replayed print command | PRINT-02: simulated adapter in preview; real QZ trust BLOCKED without cert/hardware | EXT-PRINT-02 |
| Combobox: listbox popup, arrow/enter/escape, aria-activedescendant | Official docs | https://www.w3.org/WAI/ARIA/apg/patterns/combobox/ | Keyboard-only Persian filter | DESK-02: accessible interdependent comboboxes | EXT-DESK-02 |
| Shopify POS: enrolled default receipt printer; avoid per-sale device dialogs | Official docs | https://help.shopify.com/en/manual/sell-in-person/shopify-pos/receipt-management/set-default-receipt-printer | Printer changed without re-test | PRINT-02: enrollment + test print before auto-print | EXT-PRINT-02 |
| Apple HIG RTL: logical start for icons; do not mirror non-directional glyphs | Official docs | https://developer.apple.com/design/human-interface-guidelines/right-to-left | Clipped Persian labels | UX-02: logical CSS + RTL shell | EXT-UX-02 |
| Fluent 2 Drawer: overlay from opposite edge; focus trap | Official docs | https://fluent2.microsoft.design/components/web/react/core/drawer/usage | Schedule scroll jump | FIN-03: left overlay finance drawer | EXT-FIN-03 |
| WCAG 2.2 success criteria + prefers-reduced-motion | Official docs | https://www.w3.org/TR/WCAG22/ | Continuous badge flash | DASH-03: ≤2 pulses then static | EXT-DASH-03 |
| Cliniko patient recalls setup | Official docs | https://help.cliniko.com/en/articles/8410284-set-up-patient-recalls | Indefinite daily spam | RECALL-02: capped cycle + quiet hours | EXT-RECALL-02 |
| PostgreSQL 15 unique constraints / transactional idempotency patterns | Official docs | https://www.postgresql.org/docs/15/ddl-constraints.html | Double-submit checkout | FIN-05: durable UUID idempotency keys; no truncated composites | EXT-FIN-05 / unit `checkout-intent` |
| Stripe idempotency keys (engineering analogy only — not Iran card policy) | Official docs | https://docs.stripe.com/api/idempotent_requests | Same key different payload | Reject conflict; replay identical payload | EXT-FIN-05 |
| ESC/POS 80mm/58mm paper widths (hardware capability reference) | Engineering inference | https://reference.epson-biz.com/modules/ref_escpos/ | Wrong width layout | PRINT-01: default 80mm, optional 58mm simulated | EXT-PRINT-01 |
| Jalali calendar month length / leap Esfand | Engineering inference + project decision | https://en.wikipedia.org/wiki/Solar_Hijri_calendar | End-of-month completion | RECALL-01: Jalali month add with day clamp; Tehran local date | `test_rolling_recall_mehr_aban` |

**Iran applicability:** Jane/Cliniko/Shopify/Stripe insurance, tax and card networks are **not** copied as legal or payment policy. Clinic Ecosystem keeps IRR integer ledger, synthetic POS, and disabled live CARD_TO_CARD/ONLINE until Gate B.

**SOURCE_UNAVAILABLE / excluded:** Untraceable Reddit/LinkedIn anecdote rows from earlier drafts are removed. Physical thermal hardware: NOT RUN in Linux agent (simulated adapter only).

**Project decisions (not research):** one-beneficiary invoice/receipt guards; shared settlement DISABLED pending `SETTLEMENT_BATCH_ATTRIBUTION_ARCHITECTURE.md` ratification; prepaid entitlement production activation blocked.
