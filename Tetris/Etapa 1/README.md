# Tetris Stage 1 experiment

This directory contains five independent Stage 1 implementations of the same Tetris option A seed. The single BMAD entry is the complete planning workflow.

- `shared/seed.md` is the immutable English prompt used for the five-tool baseline.
- `shared/protocol.md` defines the common scope and measurement rules.
- `OpenSpec/`, `Spec Kit/`, `Tessl/`, `Bmad Method/`, and `Kiro/` hold the five implementations, native specifications, tests, logs, and SonarQube evidence.
- `Bmad Method/` contains BMAD Method 6.12.0 through product brief, PRD, architecture, epics/stories, implementation, correction, and validation. The original generated filenames are preserved as provenance.
- `shared/bmad-metrics.json` is the BMAD measurement source. `shared/metrics-preliminary.json` and `shared/token-sessions.csv` incorporate that same execution into the five-tool comparison.
- `shared/report/guion-tetris-etapa1-asesor.md` is the advisor presentation script.
- `shared/report/tetris-etapa1-overleaf.tex` is the current Tetris thesis section. `shared/report/Tetris-Etapa-1-comparacion.pdf` extracts its seven compiled pages, including the radar and tables. The full Overleaf thesis stays in the shared project.
- `PROGRESS.md` records the current experiment and provenance. Earlier BMAD work remains available through Git history.

SonarQube coverage values describe the scanner's complete project scope; backend-only pytest coverage is reported separately. Theoretical token costs are not Google Cloud invoices. The BMAD SonarQube project key remains `tetris-stage1-bmad-full` so its archived API evidence and dashboard resolve to the measured scan.

Local dependencies, build outputs, private authentication/session files, and the complete shared thesis PDF are intentionally excluded from this repository snapshot.
