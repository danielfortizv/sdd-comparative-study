# Tetris Stage 1 — durable experiment record

Updated 2026-10-05 (America/Bogota). Scope: option A only. This repository presents **one implementation per tool**, with the complete BMAD planning workflow as its BMAD entry. Previous work is retained in Git history, not the current comparison.

## Controlled conditions

- Five roots: `OpenSpec`, `Spec Kit`, `Tessl`, `Bmad Method`, `Kiro`.
- Common English seed: `shared/seed.md`, SHA-256 `2AE084C9C64FC41F65D0E07581CED9E30B6C68891D9F8688A37F34594ECFD1C5`.
- Common product: 10×20 Tetris, seven unrotated pieces, 500 ms gravity, three arrow controls, collision, lock, line clear, game over and restart. FastAPI state and rules; React/TypeScript client. Rotation, scoring and persistence excluded.
- Gemini CLI 0.60.0 through Vertex AI project `project-e6384dd1-d4d3-4a03-948` for four tools. Kiro CLI used its GitHub-authenticated Auto mode. `.geminiignore` excludes context not needed for generation.
- Tool artifacts remain separate. SonarQube Community Build 26.9.0.129388 was used for static analysis. Scanner coverage is global; pytest coverage is backend-only. Theoretical model costs are not cloud invoices.

## Current results

| Tool | Main specification | Agent time | Backend tests | SonarQube overall: LOC / coverage / vulnerabilities / smells / cognitive / debt | Gate |
| --- | --- | ---: | --- | --- | --- |
| OpenSpec | 4 files, 442 lines, 30 requirements | 51.08 min | 13 passed; 91% backend coverage | 898 / 60.2% / 1 / 15 / 76 / 81 min | OK |
| Spec Kit | 8 files, 1,002 lines, 38 requirements | 55.98 min | 18 passed; 91% backend coverage; 5 frontend tests passed | 748 / 62.0% / 2 / 7 / 78 / 35 min | OK |
| Tessl | 2 files, 136 lines, 34 requirements | 81.68 min | 9 passed; 91% backend coverage; 2 frontend tests passed | 788 / 60.4% / 1 / 13 / 69 / see `Tessl/docs/sonar-metrics.json` | OK |
| Bmad Method | 6 files, 1,120 lines, 30 PRD FR IDs | 54.99 min | 13 passed; 98% backend coverage; independent smoke passed | 669 / 63.2% / 1 / 13 / 97 / 84 min | OK |
| Kiro | 3 files, 608 lines, 35 requirements | 9.10 min | 39 passed; 99% backend coverage | 497 / 72.6% / 0 / 10 / 45 / see `Kiro/docs/sonar-metrics.json` | OK |

All five frontend production builds passed. SonarQube counted zero bugs and zero duplication across the five projects. See each `docs/sonar-*.json`, test/build logs and `shared/metrics-preliminary.json` for the underlying evidence.

## BMAD canonical execution

- Installation: BMAD Method 6.12.0, modules `core` and `bmm`, Gemini integration. The retained native workflow includes product brief, PRD, architecture, epics/stories, implementation and scope correction.
- Six principal Markdown artifacts: 1,120 physical lines, 878 nonblank, 68,220 characters; 30 distinct PRD functional IDs. Two `.memlog.md` traces and sprint YAML are excluded from the specification count.
- Nine Gemini invocations including an unsuccessful startup: 3,299.511 seconds. Nineteen deduplicated JSONL transcripts recorded 358 model responses, 342 tool calls, 17,653,626 input tokens, 12,533,513 cached input tokens and 237,579 output tokens. Theoretical cost under the thesis formula: USD 11.6984.
- Nine source files, 1,036 physical lines. Independent backend suite: 13 tests passed, 98% module coverage. Frontend build and independent acceptance smoke passed.
- SonarQube project key `tetris-stage1-bmad-full`: gate OK, 669 ncloc, 789 physical lines, 63.2% global coverage, zero duplication, zero bugs, one vulnerability, 13 code smells, 97 cognitive complexity, 84 minutes technical debt. This original key is kept to preserve the measured dashboard and API JSON.
- Two scope corrections removed unsupported performance/capacity targets from native artifacts. Materialization manifests under `Bmad Method/docs/` link model output to written files. Generated names containing `Full` are preserved to avoid altering evidence provenance.

## Measurement and interpretation

- The per-tool scripts are `shared/collect-bmad-metrics.py`, `shared/collect-current-metrics.py` and `shared/collect-run-tokens.py`. For BMAD, the token CSV has one truthful aggregate across nine invocations because retained transcripts cannot be allocated reliably to individual command runs. It does not represent a single invocation.
- OpenSpec, Spec Kit and Tessl each have missing token traces (1, 1 and 3 runs respectively); their observed totals are lower bounds. Kiro has no verifiable token/credit record. Google Cloud credits may cover use, but no invoice amount is inferred.
- The five suites use different scenarios. Their pass counts are evidence of local validation, not a common functional acceptance rate. Review time and human-only defects remain N/D until a uniform procedure is applied.
- The radar uses five Sonar dimensions normalized within Tetris only. Bugs and duplication tie at zero. Coverage is reported as supporting evidence, not used to score the stage.

## Reports and verification

- Live thesis: [Overleaf project](https://www.overleaf.com/project/6a99e23073b642f16984b2ff), `comparativa_practica.tex` imports one `tetris-etapa1-overleaf.tex`. The former BMAD addendum was removed after user confirmation. The project recompiled to 98 pages; nine compiler diagnostics persisted, with Tetris pages rendered in the resulting PDF.
- The exact Tetris section source is `shared/report/tetris-etapa1-overleaf.tex`; its seven compiled pages are `shared/report/Tetris-Etapa-1-comparacion.pdf`. Page images `vista-bmad-unificado-overleaf.png`, `vista-radar-tetris-overleaf.png` and `vista-metricas-tetris-overleaf.png` are actual PDF renders.
- The presentation script is `shared/report/guion-tetris-etapa1-asesor.md`. The same BMAD numbers appear in thesis tables, plots, script, `shared/bmad-metrics.json`, CSV and Sonar API evidence.
- The [Google Docs comparative report](https://docs.google.com/document/d/1ccfD-2xwJw-CXM6Kny6EPiABqNVgeJ3h8A20ykhVfBg/edit) was updated on 2026-10-06. Its three native tables now show the canonical BMAD specification, 9 invocations/54.99 min, tokens, tests and Sonar metrics. The old BMAD screenshot was replaced by an actual render of the updated thesis radar and issues table; the other SonarQube dashboard captures remain. Connector readback confirmed the former BMAD values and image object are absent. A seven-page PDF export was inspected for layout.
- To recheck the BMAD smoke test from the Stage 1 root, install backend dependencies and run `python shared/verify-bmad-acceptance.py`. To query/repeat Sonar scanning in the original local workspace, use `shared/scan-bmad.ps1`; its private token path is intentionally excluded from Git.

## Next step

No additional Stage 1 generation is scheduled. A uniform cross-tool functional acceptance protocol and measured human review would be future experimental work, not values inferred from these separate suites.
