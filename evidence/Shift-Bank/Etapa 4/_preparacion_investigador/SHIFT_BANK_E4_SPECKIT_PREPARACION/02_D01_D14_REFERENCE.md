# Shift Bank E4 — D-01 through D-14 REFERENCE (not source-of-truth full records)

**Status: reference summaries extracted from Table 3 of `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx`.** The original approval records D-01–D-14, if available, govern the full wording. They are the historical outcomes of Tessl's ambiguity-resolution process, not proof that the identical answers have already been approved for this Spec Kit baseline.

All researcher–agent interactions must be in English. Do not paste Tessl implementation, tests or proprietary `.spec.md` into Spec Kit. The guide requires equivalent *business meaning*, with tool-native SDD authoring and explicit human approval.

| ID | Reference decision / contract |
|---|---|
| D-01 | One fixed currency per account: USD, EUR or GBP; never add heterogeneous balances. |
| D-02 | Reference accounts: retain `CHK-1001` USD 2,500.00 and `SAV-2001` USD 10,000.00; add `EUR-3001` and `GBP-4001`, each at 0.00. **Potential conflict with Spec Kit E3 COP balances — stop for review.** |
| D-03 | Backend uses `Decimal`; frontend uses `BigInt`/minor units; two-decimal textual amounts; rational FX rates; `ROUND_HALF_UP` exactly once at the end; no fee or financial floating-point arithmetic. |
| D-04 | Internal transfers only between same-currency accounts; cross-currency flows only through `/api/conversions`. |
| D-05 | Durable append-only SQLite domain events separate from the legacy audit log; migration must not double count. |
| D-06 | CQRS projections updated synchronously/atomically with events; deterministic rebuild; fail closed on inconsistencies. |
| D-07 | Per-operation USD-equivalent limit 5,000.00; daily USD-equivalent limit 10,000.00; MFA when *unrounded* USD equivalent is strictly greater than 1,000.00. **Compare against inherited COP limit and MFA semantics.** |
| D-08 | ACH transfers originate only from USD accounts; internal recurring transfers stay in one currency; recurring ACH is USD-only. |
| D-09 | Composite events, account versions increment exactly once per affected account; ACH debit at pending; settlement does not debit again; failure refunds exactly once. |
| D-10 | Dashboard totals separate by currency; estimated USD summary is presentation-only. |
| D-11 | AES-GCM encryption, HMAC-chained audit and atomicity across event, projection, audit and idempotency; auditable failures. |
| D-12 | Preserve FastAPI, React, SQLite and Docker Compose/Nginx/TLS deployment capability; never claim deployment was verified without executing it. |
| D-13 | UUID `Idempotency-Key` mandatory for internal transfers, FX and ACH; exact replay has no new effects; same key with different payload returns HTTP 409. |
| D-14 | Expected account versions mandatory; stale version yields HTTP 409 `ACCOUNT_VERSION_CONFLICT`; idempotent replay is checked before version validation. |

## Simulated FX rates (guide reference)

| Pair | Exact rational rate |
|---|---|
| USD → EUR | 9/10 |
| USD → GBP | 8/10 |
| EUR → USD | 10/9 |
| GBP → USD | 10/8 |
| EUR → GBP | 8/9 |
| GBP → EUR | 9/8 |

Sanity checks specified by the guide: `100.00 USD → 90.00 EUR`, `90.00 EUR → 80.00 GBP`, `0.05 USD → 0.05 EUR` (`0.045` rounded once with HALF_UP).

## Mandatory reconciliation before implementation

- Verify the **actual** inherited Spec Kit E3 account IDs, currency, seed values, operations and migration semantics from implementation/fixtures.
- E3 `spec.md` supplied in study material states Checking COP 5,000,000.00 and Savings COP 15,000,000.00, with MFA at/above COP 1,000,000.00 and COP limits 5,000,000.00/10,000,000.00. The E4 reference D-02/D-07 assumes USD amounts, account IDs and different threshold semantics. Record this conflict, not as a code defect but as a baseline comparability decision.
- Do not invent an FX conversion for COP, reinterpret peso balances as dollars, overwrite E3 seed values, or backport changes to E3. If authorized, version a prospective, explicit compatibility decision that is consistently applied and declared as a deviation from the shared historical D-01–D-14 template.
- Ask one concise, high-priority researcher question for the resolution; STOP before any specs or implementation.
