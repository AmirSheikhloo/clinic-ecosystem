# Task 34 R2 — Research-to-decision matrix

Sources inspected during this increment. Distinguishes verified docs, anecdotal reports, and Clinic Ecosystem decisions. No fabricated community consensus.

| Finding | Source URL | Edge case | Resulting requirement | Test ID |
|---|---|---|---|---|
| Package redemption is separate from booking; no-show may optionally redeem or charge fee | https://jane.app/guide/selling-redeeming-and-refunding-a-package | No-show with prepaid entitlement | PREPAY-02: default do not consume entitlement on no-show; any no-show fee is financial, not clinical completion | EXT-PREPAY-02 |
| Return visit reminders: suggested date ≠ reminder send date; suppress when booked | https://jane.app/guide/return-visit-reminders | Booking after reminder; cancel after final reminder | RECALL-01/02: rolling from actual completion; suppress when qualifying booking exists | EXT-RECALL-01 |
| QZ silent print requires server-side SHA-512 signing; private key never in frontend | https://qz.io/docs/signing | Unsigned/replayed print command | PRINT-02: simulated adapter in preview; real QZ trust BLOCKED without cert/hardware | EXT-PRINT-02 |
| Combobox: listbox popup, arrow/enter/escape, aria-activedescendant | https://www.w3.org/WAI/ARIA/apg/patterns/combobox/ | Keyboard-only Persian filter | DESK-02: accessible interdependent comboboxes | EXT-DESK-02 |
| Shopify POS: enrolled default receipt printer; avoid per-sale device dialogs | https://help.shopify.com/en/manual/sell-in-person/shopify-pos/receipt-management/set-default-receipt-printer | Printer changed without re-test | PRINT-02: enrollment + test print before auto-print | EXT-PRINT-02 |
| Apple HIG RTL: logical start for icons; do not mirror non-directional glyphs | https://developer.apple.com/design/human-interface-guidelines/right-to-left | Clipped Persian labels | UX-02: logical CSS + RTL shell | EXT-UX-02 |
| Fluent 2 Drawer: overlay from opposite edge; focus trap | https://fluent2.microsoft.design/components/web/react/core/drawer/usage | Schedule scroll jump | FIN-03: left overlay finance drawer | EXT-FIN-03 |
| WCAG 2.2 + reduced motion | https://www.w3.org/TR/wcag/ | Continuous badge flash | DASH-03: ≤2 pulses then static | EXT-DASH-03 |
| Cliniko recalls / appointments (feature overview) | https://help.cliniko.com/en/articles/8410284-set-up-patient-recalls | Indefinite daily spam | RECALL-02: capped cycle + quiet hours | EXT-RECALL-02 |
| Reddit/LinkedIn clinic admin anecdotes (duplicate payments, printer offline) | Public forums — anecdotal, non-representative | Double-click checkout; spool unknown | FIN-05 / PRINT-02: durable idempotency; reprint ≠ recheckout | EXT-FIN-05 |

**Iran applicability:** Jane/Cliniko/Square insurance, tax and card networks are not copied. Clinic Ecosystem keeps IRR integer ledger, synthetic POS, and disabled live CARD_TO_CARD/ONLINE until Gate B.

**SOURCE_UNAVAILABLE:** Square package-management deep link not independently verified this turn beyond vendor marketing; treated as secondary. Physical thermal hardware: NOT RUN in Linux agent.
