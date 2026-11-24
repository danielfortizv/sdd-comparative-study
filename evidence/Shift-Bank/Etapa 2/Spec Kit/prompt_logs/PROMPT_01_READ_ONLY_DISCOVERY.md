# Spec Kit / Gemini — Prompt 01: Read-only Stage 2 discovery

**Send the following text verbatim to Gemini CLI from the root of `Shift-Bank/Etapa 2/Spec Kit`.**

---

We are starting Shift Bank Stage 2 (Option A: functional complexity and state) using the EXISTING GitHub Spec Kit integration and this tool's own Stage 1 application.

THIS TURN IS STRICTLY READ-ONLY DISCOVERY. Do not edit, create, delete, rename, initialize, install, update or commit files. Do not run any `/speckit.*` authoring command yet, and do not implement any code.

Read these governing inputs first:
1. `../SEED-2.md` — proposed common Stage 2 seed.
2. `../E2_COMMON_FUNCTIONAL_CONTRACT.md` — proposed common behavior and acceptance scenarios.
3. `.specify/memory/constitution.md` — the inherited Spec Kit constitution.
4. Existing Stage 1 artifacts under `specs/001-shift-bank-stage1/` and the relevant backend, frontend, test, dependency and configuration files.
5. Existing `.gemini/` and `.specify/` instructions to identify which Spec Kit commands are actually available in THIS installed integration.

Important observed preparation facts that you must VERIFY against files rather than treat as implementation instructions:
- This is the isolated Stage 2 copy of `Etapa 1/Spec Kit`, not a blank repository.
- Preparation reported 59 durable files with matching SHA-256; 12 inherited backend tests, 5 frontend tests and a successful frontend build.
- Stage 1 behavior is COP-denominated, with fresh-code seed balances of COP 5,000,000 (checking) and COP 15,000,000 (savings); inherited MFA triggers at or above COP 1,000,000, uses mock code `123456` and a 300-second challenge lifetime. Confirm these rules in source and tests.
- A separately preserved Stage 1 SQLite database contains mutated historical balances (COP 4,000,000 and COP 16,000,000) and additional transfer history. That database was intentionally NOT copied into the Stage 2 application. Do not access, restore, modify or migrate it; report the migration/fixture decision as pending researcher approval.
- Reported Spec Kit version: 1.0.6. Installed Gemini CLI: 0.65.0, compared with research target 0.60.0. The environment config says `GEMINI_MODEL=gemini-3.5-flash`, but effective model routing is not yet verified. Do not switch models or upgrade tools to hide deviations.
- Do not import another tool's USD balances, MFA PIN/thresholds, code, tests, solution or metrics.

Deliver ONLY a concise read-only discovery report in English, structured as:
A. Inventory of the existing Spec Kit project and real Stage 1 behavior, with file paths.
B. Compatibility/gap matrix for ACH, recurring payments, dynamic limits, UI, persistence and existing MFA.
C. Exact Spec Kit-native artifact workflow appropriate for extending this project (preserve constitution and existing Stage 1 feature; propose a separate Stage 2 feature). Identify any slash command that the current integration lacks instead of inventing it.
D. List of unresolved decisions, distinguishing business requirements from implementation freedom and from protocol deviations. Do not choose COP limit defaults, database migration, or new MFA policy without authorization.
E. Proposed next step and the first ONE material clarification question for the researcher.

Do not create a Stage 2 specification in this turn. Do not run `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`, or `/speckit.implement`. Wait for explicit researcher approval after the discovery report.

---
