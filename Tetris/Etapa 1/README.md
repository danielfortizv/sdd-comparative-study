# Tetris Stage 1 experiment

This directory contains five independent Stage 1 implementations of the same Tetris option A seed, plus an isolated BMAD planning-path rerun.

- `shared/seed.md` is the immutable English prompt used for the five-tool baseline.
- `shared/protocol.md` defines the common scope and measurement rules.
- `OpenSpec/`, `Spec Kit/`, `Tessl/`, `Bmad Method/`, and `Kiro/` hold the five original implementations, native specifications, tests, logs, and SonarQube evidence.
- `Bmad Method Full/` is a separate BMAD Method 6.12.0 rerun through product brief, PRD, architecture, epics/stories, and implementation. It is a workflow sensitivity analysis, not a sixth tool.
- `shared/bmad-full-metrics.json` and `shared/report/auditoria-bmad-calculadora-tetris.md` compare the compact and full BMAD paths.
- `shared/report/guion-tetris-etapa1-asesor.md` is the advisor presentation script.
- `shared/report/bmad-full-overleaf-addendum.tex` is the thesis addendum used by the shared Overleaf project.
- `PROGRESS.md` is the chronological experimental record.

The original five-tool baseline remains separate from the BMAD full-path sensitivity condition. SonarQube coverage values describe the scanner's complete project scope; backend-only pytest coverage is reported separately. Theoretical token costs are not Google Cloud invoices.

Local dependencies, build outputs, private authentication/session files, and the complete shared thesis PDF are intentionally excluded from this repository snapshot. The export manifest lists the added files and hashes.
