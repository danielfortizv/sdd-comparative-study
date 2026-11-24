# GitHub Copilot — Shift Bank E4 / Spec Kit preparation (PREP ONLY)

**Working language:** English. **Current role:** repository/setup assistant, NOT the measured Stage 4 implementation agent unless the researcher separately approves that role. All actions and deviations must be attributed to GitHub Copilot, not Gemini CLI/Codex.

## Authoritative inputs (inspect, do not replace)

1. `Etapas proyecto de grado (1).pdf` — Stage 4 Option A and research rules.
2. `Guia Estandarizacion Metricas.pdf` — normalized D1–D5 metric definitions.
3. `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx` — preparation, D-01–D-14 and two approval gates.
4. `SHIFT_BANK_E3_PROTOCOLO_REPLICABLE_OTRAS_HERRAMIENTAS.docx` and `SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md` — inherited constraints; Tessl examples are HISTORICAL, never copied as implementations.
5. The final **this-tool** E3 implementation: `Shift-Bank/Etapa 3/Spec Kit/` and E3 evidence in `Shift-Bank/Etapa 3/_experiment_logs/Spec Kit/`.
6. This packet's `SEED-4.md`, `02_D01_D14_REFERENCE.md`, and `03_BASELINE_METRICS_CHECKLIST.md`.

If any referenced PDF/DOCX or original approval record is not accessible in the VS Code workspace, report it as MISSING; use this packet only as an explicitly labeled preparatory reference, never invent unseen source content.

Search for the original approved `SEED-4(1).md` / `SEED-4.md` and full D-01–D-14 decision records. This packet's seed was extracted from the literal SEED-4 appendix in the provided Stage 4 replication guide. Compare exact text and SHA-256 against any authoritative original; if they differ, STOP and report the mismatch. Do NOT rewrite the common seed to suit this tool.

## Authorized work

A. Inspect repository structure, Git branch/status, current E3 source and baseline artifacts. Confirm `Etapa 3/Spec Kit` and `Etapa 4/Spec Kit` are the correct paths. If the Stage 4 destination already exists, DO NOT replace or merge it; inventory and STOP for researcher review.

B. Inspect **native GitHub Spec Kit** rules and actual E3 specs, tasks, acceptance results, migrations, backend/frontend, deployment, test fixtures, and repo ignore rules. Do not substitute Tessl `.spec.md` or another tool's code/specs. Determine which agent/tool and model would execute the *measured* Stage 4; do not silently switch to Copilot.

C. Create an isolated `Etapa 4/Spec Kit/` baseline copied from the *finished E3 Spec Kit source only* if the target is absent and the copy is demonstrably safe. Preserve source, approved specs, functional code, tests, manifests, lockfiles, deployment templates, and necessary nonsecret configuration. Exclude `.git`, `.venv`, `node_modules`, `dist`, `.scannerwork`, `.pytest-*`, caches, `.env` files, credentials/tokens, private keys/certificates, existing SQLite DB/WAL/SHM, real volumes, and H8/H9 experimental scratch data. Do not delete or alter anything in E3; use explicit include/exclude controls and show what was copied/skipped. Preserve `.env.example` and safe example fixtures. Do not reuse active Compose resources.

D. Create a SEPARATE Stage 4 evidence folder at `Etapa 4/_experiment_logs/Spec Kit/` with preparation, decisions, sessions, tests, metrics, quality and diffs subfolders, provided this does not overwrite existing material. Keep auxiliary working notes out of the official research repository if its inclusion rules prohibit them. Establish the original source hash/commit, copied-file SHA-256 manifest, exclusions, Git status, and environment versions; do not commit automatically.

E. Make a READ-ONLY inherited-contract inventory: accounts and currencies, exact current seed balances, API endpoints, MFA thresholds, daily/per-operation limits, ACH, recurring payment flows, encryption, audit, database/migrations, tests and deployment. **Critical issue to verify:** E3 Spec Kit documents COP accounts (Checking COP 5,000,000; Savings COP 15,000,000), while the E4 D-02 reference assumes CHK-1001 USD 2,500 and SAV-2001 USD 10,000, with new EUR/GBP accounts. D-07 likewise uses USD-equivalent limits and an MFA threshold unlike the inherited COP baseline. Investigate the actual code/fixtures. Report the exact conflict and possible researcher choices WITHOUT converting data or imposing a solution. This is a mandatory human approval blocker before E4 specification or coding work.

F. Capture baseline test commands and results only if tests are already runnable safely against disposable resources entirely inside E4, and you have verified test setup cannot touch E3 databases/certificates or live Docker resources. Otherwise record `NOT RUN — isolation not demonstrated`. Do not install dependencies, run Docker or Locust, rotate secrets, or run SonarQube during preparation. Existing E3 results are historical references, NOT fresh E4 baseline runs.

G. Plan Stage 4 experiment traceability using the exact common seed, approved business decision sheet D-01 through D-14, native Spec Kit spec workflow, and D1–D5 metrics. Track each human prompt, agent message/session, token in/cache/out, tools, elapsed/active time when available, changed LOC, spec statistics, SonarQube with coverage context, acceptance, incidents, and deviations. Keep Gemini CLI and Codex E3 attribution separate. Archive their original session logs if available; never invent missing D1 metrics.

## Required deliverables (PREP ONLY)

- `Etapa 4/_experiment_logs/Spec Kit/preparacion/PREPARACION_E4_SPECKIT.md`: inventory, source provenance/commit/hash, E3->E4 copy verification, exact changes, safety exclusions, environment versions, current baseline evidence, conflicts, risks, pending approvals.
- `Etapa 4/_experiment_logs/Spec Kit/preparacion/BASELINE_FILES_SHA256.tsv`: relative paths, hash, source and destination (without secrets).
- `Etapa 4/_experiment_logs/Spec Kit/preparacion/BASELINE_TESTS.md`: observed outcomes or NOT RUN with reason, NOT historical results mislabeled as executed.
- `Etapa 4/_experiment_logs/Spec Kit/decisiones/D01_D14_PENDING_REVIEW.md`: decision reference, provenance and explicit unresolved items; do not mark as prospectively approved without human sign-off.
- A brief **native Spec Kit specification plan for researcher review** listing impacted existing specs, proposed new specs, acceptance tests and E3 compatibility risks. This is a proposal only: do not generate/edit functional specs yet.

## Hard STOP conditions

- No Stage 4 feature implementation, schema migration, conversion endpoint, domain event store, CQRS, spec authoring or edits to tests for Stage 4.
- No changes to E3, other SDD tools, shared canonical SEED-4, D-01–D-14 originals, historical research artifacts, production volumes/keys/secrets, or benchmark results.
- No copying Tessl implementation, tests, specific fixes or spec structure into Spec Kit.
- No unapproved changes to business rules, currency semantics, source values, acceptance targets, or test assertions.
- Ask for human **Gate A** approval of baseline reconciliation and the specification plan before the *measured* Spec Kit agent starts discovery/spec authoring. A separate **Gate B** authorizes implementation after the specs are approved.

**Report:** actual files created, commands run (with exit codes), file/hash counts, unresolved blockers, proposed next measured-agent prompt, and remaining human approvals. Do not assume that documentation or successful E3 tests prove Stage 4 passed.

**STOP FOR HUMAN REVIEW — STATUS: E4 / SPEC KIT / PREPARATION ONLY.**
