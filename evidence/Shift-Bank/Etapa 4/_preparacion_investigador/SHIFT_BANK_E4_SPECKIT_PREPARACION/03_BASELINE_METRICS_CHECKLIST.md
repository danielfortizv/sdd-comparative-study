# Shift Bank E4 — Spec Kit preparation, measurements, and review gates

## Scope of this packet

- Case study: Shift Bank. Stage 4, Option A — multicurrency, simulated FX, Event Sourcing and CQRS.
- Measured SDD framework: **Spec Kit**. The setup helper is **GitHub Copilot**, not automatically the measured agent.
- Baseline source: **this tool's own** completed `Etapa 3/Spec Kit/`. Never reuse Tessl, OpenSpec, BMAD or Kiro trees.
- Canonical seed: use the shared `SEED-4.md` *verbatim*, separate from any tool-specific prompt. This packet extracts the appendix in the supplied replication guide. Seek original `SEED-4(1).md` and compare exact bytes/hash.
- Fourteen decisions: extract/check full approved originals; the packet's reference sheet is **not** a replacement for their primary record.

## Before the measured Stage 4 agent receives the SEED

- [ ] Identify source directory, Git branch/commit, dirty/untracked files and current E3 stage status.
- [ ] Verify `Etapa 4/Spec Kit` is absent or intentionally reserved; never overwrite existing work.
- [ ] Confirm source copy exclusions and non-destructive handling of `.pytest-*` (Windows ACL), database files, Docker volumes, keys and `.env`.
- [ ] Record OS, Python, Node, actual Spec Kit CLI/extension, coding agent version, model and runtime. Differences from research fixed version/model rules must be registered as deviations, not concealed.
- [ ] Preserve native `.specify`/`specs` and Stage 3 contracts/tests; record SHA-256 manifest for copied files.
- [ ] Identify baseline data currency/account IDs, transaction rules, ACH, recurring, limits, MFA, encryption/audit and server/SPA endpoints.
- [ ] **Human blocker:** reconcile Spec Kit E3 COP accounts/thresholds with E4 reference USD/EUR/GBP D-01, D-02 and D-07. No silent conversion or seed rewrite.
- [ ] Baseline pytest, Vitest and build only if isolated and safe; capture stdout and exact counts. Otherwise mark NOT RUN. Historical E3 runs: 97/97 backend, 13/13 frontend, production build PASS, 9/9 isolated Docker checks (different stage, historical, not E4 baseline tests).
- [ ] Preserve E3 static-analysis historical results for E3→E4 comparison with consistent scope and coverage provenance. E3 reported Sonar Quality Gate OK, 6,204 NCLOC, 3 bugs, 1 vulnerability, 70 code smells, 0.0% duplication, and 508 min technical debt; E3 coverage 0.0 reported with unverified import. **Never assume this is Stage 4 quality.**
- [ ] Archive E3 Codex session JSONL and Gemini logs without modifying either; handle missing cost/token/time values as N/D.
- [ ] Define a safe location for `Etapa 4/_experiment_logs/Spec Kit/` outside the implementation, applying the research team's rules on excluding auxiliary analysis from the official Git repo.

## Stage 4 human gates

1. **Gate A — Baseline/discovery and specification plan:** researcher approves conflicts/decisions and which native Spec Kit artifacts will be authored. Prior to approval, no specs are created or changed.
2. **Native Spec Kit specification phase:** only after Gate A; clarification D-01 through D-14 with English answers and stable approved semantics; verify specifications and acceptance mapping; capture exact approved hash/version.
3. **Gate B — Implementation:** researcher independently authorizes modifications after approving the specs. Update approved specs first for any business-rule change; no direct code changes bypassing SDD.
4. **Verification/closure:** acceptance, E3 regression, integrations, financial invariants, event replay/idempotency, SonarQube/cov as observed, capture tool usage, CLOSE WITH LIMITATIONS when measurements unavailable rather than infinite retries.

## D1–D5 collection contract

| Dimension | Fields / source requirements |
|---|---|
| D1 Effort | Tok In, Tok Cache, Tok Out, Cred (Kiro only), Costo ($), Msgs, Tool Calls, Tiempo (s); original session JSONL/status screenshots; separate measured-agent sessions from Copilot setup. Never double-count cached tokens or confuse model calls with user prompts. |
| D2 Code quality | LOC and diff LOC (new/modified/deleted); SonarQube findings/ratings, Hal/KLOC, coverage import provenance, technical debt (minutes), complexity, duplication; same source scope across stages. |
| D3 Specifications | Native approved spec `.md` files only; count files, physical lines, density, code-to-spec ratio, atomic reqs, req density and 5-number distribution using uniform counting rules. Do not count setup notes/README as formal specs. |
| D4 Functional | Common REQ-01 to REQ-06 and inherited acceptance; classify PASS/FAIL/NOT VERIFIED based on observed evidence; keep extras separate from minimum contract. |
| D5 Human interventions | Sequence number, issue, relevance/severity, justification, researcher correction, spec updates, deviations, supporting transcript and test evidence. |

E4 and E3 measurements must have comparable unit and scope before calculating percentages. Show E4 value and E3 variation on a separate line in academic tables, if both measurements exist.

## Stage 4 common minimum acceptance (read-only preparation inventory)

- REQ-01: currency-aware balances/history and legacy monetary preservation.
- REQ-02: simulated FX with rate transparency and exact monetary arithmetic.
- REQ-03: durable domain events independently reconstruct state and are distinct from HMAC audit records.
- REQ-04: separate commands/read models; projections replay/rebuild deterministically.
- REQ-05: internal transfer/ACH/recurring/limits/MFA/encryption/audit compatibility without duplicate monetary effects.
- REQ-06: testable evidence for migration, retry, failure, projection and inherited regression.

## Progress and stop condition for THIS preparation invocation

**Preparation = complete** only if the agent provides a source-to-copy provenance trail, an inventory of artifacts and skips, a safe baseline/no-run rationale, a comparison of currency contracts, a D1–D5 evidence plan, and a clear list of approvals required. Preparation ≠ Stage 4 implementation.

**STOP FOR HUMAN REVIEW.**
