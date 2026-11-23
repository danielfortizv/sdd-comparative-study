# MASTER PROMPT FOR CODEX — Shift Bank Stage 3 / Spec Kit / PREPARATION ONLY

You are acting as a **local experimental-preparation engineer** for an academic comparative SDD study. You are **NOT** the agent being evaluated. The evaluated development workflow is **GitHub Spec Kit + Gemini CLI**, which will start only **after** I explicitly approve the Stage 3 readiness report.

## Your mission

**Execute HITO 0 ONLY: verify, replicate and freeze the completed Shift Bank Stage 2 Spec Kit baseline into an isolated Stage 3 Spec Kit workspace; prepare instrumentation/evidence folders; run inherited regression tests safely; then STOP.** Do the authorized safe preparation autonomously. Do not require confirmation for routine file reads, creation of empty evidence folders, normal durable-file copying after preflight, or execution of isolated inherited tests. Stop and report if you encounter an existing conflicting destination, mismatched hash, insecure database access, unapproved dependency/source change, or an operation that would touch historical data. Never bypass such a blocker for convenience.

## Read these files FIRST

The instruction package should be located in:

`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_codex_prep\`

Read in this order, in full:

1. `README_COMO_USAR.md`
2. `00_CONTEXTO_Y_CONTRATOS.md`
3. `01_PLAN_TECNICO_HITO0.md`
4. `02_EVIDENCIAS_Y_METRICAS.md`
5. `03_HANDOFF_A_GEMINI.md`
6. `CHECKLIST_ENTREGA.md`
7. `SEED-3.md` **VERBATIM, NO EDITS**

If these inputs are missing or paths differ, locate the extracted package in the Stage 3 directory and document the actual path. Do not fabricate their contents or guess an alternative source. The common seed must have SHA-256:

`99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`

Also inspect actual source evidence in:

`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\_experiment_logs\Spec Kit\`

Especially the E2 closure report, final SHA-256 manifest, test evidence, SonarQube reports, and real inherited source configuration. The .md files are instructions and context, **not substitutes for inspection of the real local files**.

## Hard boundaries

- **Source:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit`
- **New Stage 3 workspace:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Spec Kit`
- **New Stage 3 evidence:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Spec Kit`
- **Common immutable seed:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\SEED-3.md`

Only write within the new E3 workspace, new E3 evidence directory, and the E3 seed if it does not exist; never overwrite an existing different seed. **Never write** to Stage 1, Stage 2, other SDD tools, Tessl, other cases, other stages, old SonarQube data, or the parent monorepo's global configuration. Never copy code, implementation techniques, generated specs or known defect fixes from Tessl. Do not change Git history, branches or commits. Do not commit or stage files.

**Never migrate, read-write mount, modify, clean up or start a server on an E1/E2 database.** Do not copy historical `.db`, `.sqlite`, `-wal`, `-shm`, secrets, `.env*`, private keys, certificates, `.venv`, `node_modules`, build directories, caches or session data into the new workspace. Use safe exclude-on-copy rather than destructive deletion. If the E3 destination is populated with conflicting files, STOP before overwriting anything. No `robocopy /MIR`, `git reset`, `git clean`, broad `Remove-Item`, Docker volume deletion or secret printing.

## Execution plan — run, don't merely describe

**0 — Preflight.** Resolve and inspect all paths. Validate the source's identity as the FINAL E2 **Spec Kit** implementation. Check Git status/commit, historical E2 closure report, existing E3 destination, SDD native configuration and manifest conventions. Verify that the supplied seed is byte-identical. Before doing anything potentially destructive, inspect and STOP if there is a collision.

**1 — Freeze the true E2 source.** Compute a reproducible SHA-256 inventory of durable source/spec/tests/config files, excluding ephemeral data. Reconcile it against the existing `E2_SPECKIT_FINAL_MANIFEST_SHA256.csv` if available. The historical study reports 74 durable files, but use ACTUAL counts, explicit filters and hashes; do not artificially make counts match.

**2 — Create the independent E3 copy.** Copy only the allowed durable files with their paths/bytes intact. Preserve `.specify`, specs E1/E2, backend/frontend source, tests, package/dependency manifests, configuration and `.gitignore`. Do not create any E3 features/specifications. Compute an E3 durable manifest and verify exact one-to-one file/hash equivalence with the E2 source before running any tests. If it fails, STOP and report discrepancies.

**3 — Prepare the environment.** Capture OS, PowerShell, Python, Node, npm, Git, Gemini CLI, Spec Kit integration, branch/commit, effective configuration, and Docker availability (read-only probes only). Report unverified facts as `N/D`. Create independent E3 Python/Node dependency environments only when needed, using existing lock/manifests without editing them. Do not change global tooling or install Stage 3 crypto/Locust/Docker dependencies.

**4 — Verify inherited tests on a DISPOSABLE E3 DB.** Inspect backend DB initialization and `conftest.py` before importing/running anything. Point all tests explicitly to a safe isolated test database/path **within Stage 3** (never a historical or preserved DB). Run the backend pytest suite, frontend Vitest suite, and frontend production build with full raw logs, timestamps and exit codes. Historical E2 results for comparison: 47 backend tests, 12 frontend tests, frontend build PASS. Do not edit code or tests to improve outcomes. If unsafe or blocked, mark `NOT EXECUTED` with the exact reason. Rehash durable files after tests and confirm no source/spec/lockfile was changed.

**5 — Create evidence and reporting.** Populate only the Stage 3 Spec Kit evidence folders (`preparacion`, `sesiones`, `decisiones`, `pruebas`, `locust`, `sonarqube`, `diffs`). Write the real E2/E3 SHA manifests, comparison matrix, version/Git logs, database-isolation report, Codex-preparation log, raw test outputs and `preparacion/E3_SPECKIT_HITO0_READINESS.md`. Do not create fake load, deployment, coverage, SonarQube or Gemini results; those phases have not started. Record everything you personally did as `CODEX_PREPARACION_HITO0`, separate from future D1 Gemini measurements.

**6 — Final gate.** Use `CHECKLIST_ENTREGA.md` to give a defendable `GO PARA GEMINI HITO 1` or `NO-GO` with objective supporting evidence. List all generated file paths, actual commands and test counts, missing evidence, unexpected differences, security/isolation observations and next human action. Report the source and destination inventories and verified SHA counts.

## Explicit prohibitions

Do not launch Gemini. Do not run `/speckit.*` workflows or create `specs/003-...`. Do not implement encryption, audit logging, Locust or container deployment; do not create an E3 data model or amend approved E2 functional specs. Do not run SonarQube, load testing or Docker deployment. Do not remediate inherited SonarQube findings, change historical E2 files, rotate secrets, change any business rule, or provide a production-ready certification. Do not draft the academic thesis conclusions. Do not advance to HITO 1.

## Response language and stopping rule

You may reason and implement the preparation in English, but write the **final summary and readiness report in Spanish**, with clear `PASS / FAIL / NOT EXECUTED / N/D` distinctions. Use citations to **local file paths, commands and logs**. Do not invent outputs. If a step fails, record the observed failure before attempting only safe, in-scope environment fixes.

The required final response format is:

```text
E3 SPEC KIT — HITO 0: GO PARA GEMINI HITO 1 / NO-GO
Source E2: [resolved path, commit, durable files]
Destination E3: [resolved path, durable files]
SEED-3 SHA256: [actual]
Source↔copy SHA256: [match/missing/changed/unexpected]
Backend pytest: [exact passed/failed, exit code]
Frontend Vitest: [exact passed/failed, exit code]
Frontend build: [PASS/FAIL, exit code]
Safety: [DB isolation, secret protection, source not modified]
Evidence directory: [actual path]
Evidence created: [file names]
Blockers or limitations: [precise facts]
Awaiting human authorization: YES — do not start HITO 1.
```

**STOP as soon as this report is complete.**
