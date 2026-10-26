# Stage 2 controlled protocol v1.0

Source decisions: Stage 2 option A in the study matrix and the thesis appendix. The exact common seed is `seed.md`; record its SHA-256. Each tool starts from its own final Stage 1 directory, copied into its own Stage 2 directory. Do not supply outputs from one tool as input to another.

## Controlled environment

- OpenSpec, Spec Kit, Tessl and BMAD: Gemini CLI 0.60.0 with requested Gemini 3.5 Flash on Vertex AI; record the effective model shown by logs. Kiro: its native Auto mode.
- All agent interactions and specifications are in English.
- New app features are generated from native specs. Researcher-authored harness, metrics, logs, and independent acceptance checks live in `docs/` or `shared/` and are labeled as such.
- Preserve the exact Stage 1 source manifest, all prompts, CLI JSON output, stderr, invocation start/end times, and original session transcripts. No secrets in the repository.
- Record requested model and observed model separately. Never infer missing token counts.

## Metrics and evidence

For each invocation: prompt hash, elapsed wall time, exit code, input/output/cached tokens, model response count, and transcript path when reported. Count prompts and explicit post-implementation corrections separately. Record question count and tool/version information.

For specs and code: physical lines, Unicode characters, number of files, lines per file, baseline/final/delta, and inclusion/exclusion rules. Count native spec artifacts separately from application source. Exclude dependencies, builds, lockfiles, logs, and researcher-created acceptance files from generated-source metrics.

Validation: Stage 1 regression, Stage 2 shared acceptance catalog, backend suite and coverage, frontend production build, and browser check. A pass is reported only when executed. SonarQube: unique Stage 2 project key, quality gate, bugs, vulnerabilities, security hotspots, code smells, cognitive complexity, duplication, maintainability/reliability/security ratings, technical debt and coverage if measured. Source code coverage and SonarQube overall coverage are distinct. SonarQube does not measure scalability directly.

Screenshots must depict actual CLI, app, test, or SonarQube views. Link each screenshot to the raw log or result. The Google Doc summarizes metrics and embeds representative captures; raw evidence remains in Stage 2.
