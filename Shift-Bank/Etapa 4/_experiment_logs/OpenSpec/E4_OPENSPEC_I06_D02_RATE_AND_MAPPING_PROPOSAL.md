# Iteration 06 D-02 rate and account-mapping proposal

**Status:** Analysis only. The researcher approved the priority to preserve inherited financial value and transaction history, but did not approve a rate, account mapping, new balances, or a D-02 deviation. The advisor's 1 USD = 4,000 COP is only a candidate. No migration was performed.

## Evidence and decision layers

- **Common approved contract:** D-01 limits spendable account currencies to USD/EUR/GBP, one currency per account. D-02 reference accounts are CHK-1001 USD 2,500.00, SAV-2001 USD 10,000.00, EUR-3001 EUR 0.00, GBP-4001 GBP 0.00.
- **Inherited OpenSpec source facts:** `backend/database.py` initializes `acc_checking` at 5,000,000.00 and `acc_savings` at 15,000,000.00 with no currency column. It also inserts completed `tx_seed_1` (Savings → Checking, 500,000.00, 2026-09-28 10:00Z) and `tx_seed_2` (Checking → Savings, 100,000.00, 2026-09-28 11:00Z). `openspec/specs/bank-accounts/spec.md`, `transfers/spec.md`, `mfa/spec.md` and frontend validation/test language label inherited values COP. This supports COP as intended semantics, but currency is not stored on the source records.
- **Not observed:** No populated runtime SQLite database was present in the copied H0 source inventory. These are source initialization/test observations, not evidence of actual customer balances, production history, pending ACH, scheduled obligations, or current daily usage.
- **Researcher-approved priority:** Preserve inherited financial value and transaction history. This approves the priority only, not the proposed numerical conversion or identities.
- **Technical-advisor proposal:** Fixed simulated one-time migration rate 1 USD = 4,000 COP. It is not a market/historical rate and is not a D-03 operational rate. It is not approved.
- **Unapproved choices/deviations:** Rate, public/internal identity mapping, converted opening balances, acceptance of deviations from D-02 reference amounts, pending-operation treatment, legacy limit/MFA carryover, and migration event boundary remain unapproved.

## Exact arithmetic for the candidate rate

Using Decimal/exact rational arithmetic only, USD = COP / 4,000:

| Source amount | Exact candidate USD | D-02 reference comparison |
|---:|---:|---|
| 5,000,000.00 COP | 1,250.00 USD | CHK-1001 reference is 2,500.00 USD; candidate is 1,250.00 lower (50% below reference). |
| 15,000,000.00 COP | 3,750.00 USD | SAV-2001 reference is 10,000.00 USD; candidate is 6,250.00 lower (62.5% below reference). |
| 500,000.00 COP | 125.00 USD | Seeded tx_seed_1, Savings → Checking. |
| 100,000.00 COP | 25.00 USD | Seeded tx_seed_2, Checking → Savings. |

The inherited opening total is 20,000,000.00 COP, which maps to 5,000.00 USD under this candidate. The D-02 reference opening total is 12,500.00 USD. The candidate total is 7,500.00 USD below the reference total (60% below it). The candidate values are exact at two decimals; no rounding occurs for these four examples. No deposit, withdrawal, or plug is proposed to eliminate the difference.

For an arbitrary legacy amount stored in two-decimal COP, calculate the exact rational quotient and round only the final USD amount to cents using ROUND_HALF_UP. In integer minor units, if `c` is COP cents, the exact USD-cent quotient is `c / 4000`; apply signed half-up rounding once at the conversion boundary. No binary floating point. Rounding per historical row and summing rows need not equal converting a cutover account snapshot, so the migration must not infer balances by summing incomplete/ambiguous history.

This policy would preserve nominal value only under the researcher-approved simulated equivalence of 4,000 COP per USD. It is not evidence of market value or historical purchasing power. Its one-time migration rate must remain separate from D-03's fixed ongoing USD/EUR/GBP operational FX rates and must not be reused for normal conversion or post-cutover limit valuation.

## Candidate account identity mapping (not approved)

| Existing internal ID | Proposed canonical public reference | Active currency | Candidate opening balance | D-02 status |
|---|---|---|---:|---|
| `acc_checking` | `CHK-1001` | USD | 1,250.00 USD | Currency/reference name align; amount deviates from 2,500.00 USD by −1,250.00. |
| `acc_savings` | `SAV-2001` | USD | 3,750.00 USD | Currency/reference name align; amount deviates from 10,000.00 USD by −6,250.00. |
| New internal/public ID (to be specified) | `EUR-3001` | EUR | 0.00 EUR | Reference ID/currency/amount align if authorized and created later. |
| New internal/public ID (to be specified) | `GBP-4001` | GBP | 0.00 GBP | Reference ID/currency/amount align if authorized and created later. |

Retaining `acc_checking` and `acc_savings` as internal primary keys can preserve existing foreign keys and audit references. A public alias table can map them to D-02 references. However, an alias field alone does **not** establish D-02 identity compliance: the researcher/native API contract must state whether `/api/accounts` exposes `id=CHK-1001`/`SAV-2001` as canonical public IDs and whether requests accept both old IDs and new public IDs. If `id` remains `acc_checking`/`acc_savings` and D-02 IDs are merely labels, the exact D-02 identity contract is not met. Accepting legacy IDs can preserve request compatibility, but account listing shape and “exactly two” inherited UI/spec scenarios change. No IDs, API fields, aliases or accounts were changed/created.

## History, event bootstrap, audit and conservation

The source rows are completed and directional: 500,000 COP moves Savings to Checking, then 100,000 COP moves Checking to Savings. Their aggregate net is zero; on a posting replay their account-level net is +400,000 COP Checking / −400,000 COP Savings, equivalent under the candidate to +100/−100 USD. The initialization code also creates the 5m/15m balances separately. Neither code nor an observed DB proves whether those balances are before or after the two historical rows. Reapplying the rows to balances that already include them would double-apply history; using them to derive balances without a complete chronological ledger could lose state.

Recommended technical boundary for review: take the verified current account balances at one migration cutover as the posting snapshot; convert each account snapshot once; append one idempotent migration-boundary/domain event per migrated account with original ID, explicitly approved legacy currency/rate, source nominal amount, converted amount, rounding rule, public mapping and deterministic migration-batch identity. Import original transactions as immutable, explicitly COP-denominated legacy provenance/history records that do not post again to the new balance projection. If the researcher instead proves a complete pre-snapshot ledger, a different replay boundary can be designed; current evidence does not.

The domain event store must rebuild the converted cutover balances from the migration boundary and subsequent Stage 4 financial events. Historical `tx_seed_1`/`tx_seed_2` may remain queryable with their original IDs, direction, timestamps and COP amounts, but must not be replayed as new balance effects on top of a cutover snapshot. Re-running the same migration batch against the same source snapshot must be a no-op; a changed source snapshot, conflicting alias or incomplete state must fail closed. Any rollback must restore the pre-cutover source state and prove no post-cutover effects were lost or duplicated. This is a proposed design/test boundary, not implementation.

Keep old HMAC audit rows and chain ordering/keys unchanged. Do not convert audit entries into domain events, rewrite historical IDs in the audit chain, or append financial effects to the old chain twice. New migration/domain-event/projection/idempotency writes and the required audit outcome must commit atomically per D-11. If there is no usable audit secret or verification fails, migration must fail closed. Current E4 contains no observed runtime DB to test this against.

The migration rate, if approved, applies once to source COP state. After cutover only USD/EUR/GBP accounts are spendable; historical COP amounts remain provenance with explicit currency labels, not a fourth active account currency. Ongoing conversions use only D-03 rates.

## Compatibility and unresolved cutover policies

- **Limits/MFA:** After an account is USD, new operations use D-07 exactly: USD-equivalent operation cap 5,000.00, daily 10,000.00, MFA iff unrounded USD equivalent is greater than 1,000.00. Under the candidate, 5m COP is 1,250 USD, which would exceed the new MFA threshold if it were an operation amount; this does not mean an existing pending transfer can be reauthorized or downgraded automatically. The inherited configurable 5m/10m COP-like limits and any current-day usage need explicit treatment at cutover. Do not reset or convert accrued usage without approval.
- **Pending ACH:** D-08 requires USD source accounts; any existing pending COP-denominated ACH may already have had one debit. Its settlement/refund must never debit twice or lose the one refund. Researcher must decide whether migration requires no pending ACH, converts and carries it under the one-time policy, or resolves it under the legacy state machine before cutover. No pending record was observed.
- **Recurring:** Internal recurring transfers remain same-currency if both mapped accounts become USD, but stored COP amount and next-run state need a one-time conversion/cutover decision. Recurring ACH must originate in USD. Decide whether schedules are converted with the migration rate, suspended for resolution, or block migration; do not invent. No live schedule state was observed.
- **Idempotency/versioning:** Existing request endpoints lack D-13 request keys and D-14 account versions. Preserve completed legacy transaction IDs as history; do not fabricate prior idempotency records. New requests require UUID keys and expected versions; replay check precedes version check. Set a deterministic initial migrated account version and migration event version behavior, with exactly one increment per affected account under D-09. Treatment of any in-flight MFA/ACH/schedule operation without these new fields requires approval.
- **API/frontend/E3 regression:** Preserve internal FK/audit IDs and route aliases if approved; expose canonical D-02 public IDs explicitly. Frontend must show USD balances and clearly labelled COP historical provenance, avoid floats, and handle 409/version/idempotency conflicts. Existing COP and exactly-two-account examples are historical regression fixtures; tests must distinguish retained legacy behavior from new public contracts without weakening financial assertions.
- **Deployment/restart:** The event store and projections must persist across restart and rebuild deterministically. Compose currently requires local `.env.local`, now moved; a protected external configuration path/override needs separate authorization before deployment. No Compose changes/deployment were made.

## Recommendation and concise approval statement
The 4,000 COP/USD candidate is arithmetically exact for the known seed values and yields an auditable, deterministic migration **if** it is approved as a one-time simulated equivalence and if migration uses a balance snapshot boundary with non-posting historical provenance. It preserves aggregate value only under that chosen equivalence. It does not satisfy D-02's exact USD opening balances; the differences total 7,500 USD. A public alias can preserve internal identity references but meets D-02 IDs only if the public API treats the D-02 references as canonical IDs.

Because common D-02 is fixed and experimental comparability matters, **do not authorize migration or H2 specification generation on this candidate alone**. The researcher must explicitly accept or reject the numerical deviation and the public identity mapping, and decide how active legacy obligations/limits carry over. If exact D-02 balances are mandatory alongside value preservation, the candidate is incompatible and no balancing entries may be invented; the policy needs a different researcher decision before specifications.

Suggested approval text for the researcher to accept, edit or reject (policy approval only, not migration authorization):

> I approve / reject the one-time simulated migration rate 1 USD = 4,000 COP. If approved, I accept / reject converted candidate balances of USD 1,250.00 for CHK-1001 and USD 3,750.00 for SAV-2001, with deviations of −USD 1,250.00 and −USD 6,250.00 from common D-02; no balancing deposits/withdrawals are permitted. I approve / reject retaining `acc_checking` and `acc_savings` as internal keys while exposing CHK-1001/SAV-2001 as canonical public IDs and accepting legacy IDs as input aliases. I approve / reject preserving seeded/history transactions as non-posting COP provenance at a verified balance-snapshot event boundary. For any pending ACH, recurring obligation, pending MFA and current-day limit usage, migration must [block until resolved / other explicitly stated policy]. This approves policy for later specification only; it does not authorize migration, account/API changes, new-account creation, H2 authoring or implementation.
