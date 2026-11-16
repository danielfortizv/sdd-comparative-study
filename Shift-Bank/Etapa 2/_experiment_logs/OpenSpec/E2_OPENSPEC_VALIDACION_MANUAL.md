# Shift Bank E2 — Manual validation status

No manual browser test or browser-driven end-to-end suite was run. A21 remains NOT EXECUTED. A05 and A10 are PARTIAL for rendered UI observation. Automated helper tests and a production build are not browser observations.

## Still to observe manually
1. Stage 1 accounts, balances, seeded history, and account history filtering.
2. Internal transfer and MFA at COP 1,000,000 inclusive; valid/invalid amount and insufficient funds messages.
3. Beneficiary creation, listing, editing, deletion, and inline routing/account field feedback.
4. ACH ad hoc and saved-beneficiary submission, pending state, later settlement, and failed refund/history.
5. Limits consultation and update, invalid values, exact boundaries, and reductions below usage.
6. Recurring internal/ACH creation, UTC timestamps, MFA, pause/resume/cancel, failures, and upcoming occurrence.
7. Leave app open through ACH and recurring background state transitions and observe five-second refresh.

The list is pending work, not claimed results. Do not expose public ACH failure controls or alter historical data.

A01–A21 states and their automated evidence are in E2_OPENSPEC_AUDITORIAS_CORRECCIONES.md.
