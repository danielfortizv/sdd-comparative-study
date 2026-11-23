# Recommended Next Prompt for the Measured Stage 4 Agent

**Do not send or execute this prompt until Gate A is explicitly approved.** Replace every bracketed value using researcher-approved evidence. This prompt authorizes specification/discovery only, not implementation.

```text
You are the measured Stage 4 agent for Shift Bank, Option A — GitHub Spec Kit.

Use only the isolated workspace:
  Shift-Bank/Etapa 4/Spec Kit/

The researcher has approved Gate A in [approval record/path]. The approved COP/USD reconciliation is [exact approved rule and mapping, or explicit statement that COP is preserved]. The authoritative D-01–D-14 records are [paths]. The approved common SEED-4 file is [path] with SHA-256 [approved hash]. The measured agent/tool is [researcher-selected tool], version [version], using model [researcher-approved model].

Before any work, confirm those approvals and hashes. If any source is missing, mismatched, or ambiguous, STOP and ask the researcher; do not infer rates, convert balances, relabel currencies, alter seed values, or change acceptance targets.

Use the native GitHub Spec Kit workflow and the approved SEED-4 verbatim. Treat the copied E3 files and their SHA-256 manifest as the inherited baseline. Do not modify Etapa 1, Etapa 2, Etapa 3, Tessl, shared seeds, or historical evidence. Do not install dependencies, run Docker/Locust/SonarQube, or modify functional code/tests in this specification-only phase unless the researcher separately authorizes it.

Perform discovery/clarification only for approved D-01–D-14 and the Stage 4 common REQ-01–REQ-06. Then propose the native Spec Kit specification, data model, API contracts, plan, tasks, and acceptance mapping in the new Stage 4 feature directory. Preserve inherited Stage 1–3 behaviors and explicitly map migration, currency, event sourcing, CQRS, idempotency, account versions, ACH/recurring, MFA, encryption, audit, and deployment constraints.

Record each prompt/response, session ID, model, token input/cache/output, tools, elapsed/active time when available, LOC, specification counts, incidents, and deviations. Keep Copilot preparation and historical Gemini/Codex E3 attribution separate. Mark unavailable measurements N/D; never fabricate them.

Do not implement any feature. After producing the specification proposal, acceptance map, and D1–D5 evidence record, STOP for human review and Gate B approval.
```
