# Common protocol v1

## Decision and sources

Scope: only Tetris Stage 1 option A. The Google Doc matrix identifies option A as grid, piece rendering, gravity, basic collisions and line clearing. Option B adds rotation and line counter; option C adds ghost piece and configurable controls. The option A choice was delegated by the user. The thesis requires controlled common requirements, starting state, tool versions, time and acceptance testing. The matrix requires all interactions with the tools in English, the same initial seed and separate artifacts.

Primary matrix: https://docs.google.com/document/d/1Fi7XAKY2Cd379spmq7ggxgoE0rEjKx6pq66hTdLj-6c/edit

## Controlled conditions

- Start each tool in an empty, separate directory with the same `shared/seed.md` prompt text.
- Use Gemini CLI 0.60.0 and Gemini 3.5 Flash through Vertex AI for OpenSpec, GitHub Spec Kit, Tessl and BMad Method, if that model is actually available to the authorized GCP project. Record the exact resolved model and version. Use Kiro Auto mode as specified by the matrix and record what the UI reports.
- GCP project: `project-e6384dd1-d4d3-4a03-948`; Vertex AI location: `global`. Do not store tokens, credentials or service account keys in this workspace.
- Use Python FastAPI for the backend and React with TypeScript for the frontend. Backend owns state and rules, frontend renders API state.
- No manual edits to tool-generated application code after generation. Log each clarification and resulting specification change. Harness files, experiment logs, and external acceptance tests are researcher-created and clearly identified.
- Do not use Git commits. Preserve raw session transcripts and tool output when available.
- Keep reports, screenshots and evaluation notes in each tool's `docs/` and in the shared `report/`. Place `.geminiignore` at each Gemini-driven tool root, ignoring `docs/`, `.env`, `node_modules/`, `build/` and `dist/`.

## Acceptance criteria and metrics

The common external acceptance checks will cover 10 by 20 board dimensions; piece spawn; left/right/down moves; wall, bottom and settled-block collisions; automatic ticking; locking; one and multiple completed-line clears; subsequent spawn; game over; frontend build; API run. A test is counted as passed only when actually executed against that tool's output. Record omissions separately.

For each tool record start/end time, wall-clock duration, prompt count, question count, explicit correction count, prompt/transcript path, exact tool and model versions, input/output tokens if reported (otherwise `unavailable`), generated or edited spec line and character counts, spec lines per file, code line and character counts, external acceptance results, backend tests, frontend build, and SonarQube project key and metrics. Do not infer token counts from cost or text length. Count source lines and characters over text files only, excluding dependencies, build output, reports, generated lockfiles and transcripts; record inclusions and exclusions.

SonarQube metrics: quality-gate status, bugs, vulnerabilities, security hotspots, code smells, cognitive complexity, duplication percentage, maintainability rating, reliability rating, security rating and coverage if instrumentation supplies it. Report missing metrics as unavailable. SonarQube does not directly measure scalability; describe scalability only from architecture and any actually executed performance test, without claiming it is a SonarQube metric.

Screenshots must come from the actual tool, test or SonarQube interface and be linked to raw evidence. The final document will place these captures next to the comparative values.
