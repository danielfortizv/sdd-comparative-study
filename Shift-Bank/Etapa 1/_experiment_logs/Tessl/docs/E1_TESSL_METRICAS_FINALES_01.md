# Tessl — Stage 1 — Final Quantitative Measurements

## 1. Experimental Identification

- Case study: Shift Bank.
- Stage: 1.
- SDD tool: Tessl CLI 0.118.1.
- SDD plugin: `tessl-labs/spec-driven-development@2.0.1`.
- Gemini CLI version observed: 0.65.0.
- Measurement checkpoint: After correction cycle 01.
- Date: November 1, 2026.
- Measurement mode: Read-only filesystem inspection.
- Git branch: `ShiftBank`.
- Git HEAD: `d66eb238d884827c0c2860bfde9d0d10de38fd1a`.
- Repository tracking: Tessl project directory remained untracked at the time of measurement.

## 2. Specification Metrics

| Specification | Lines | Normalized characters | Raw bytes |
|---|---:|---:|---:|
| accounts.spec.md | 53 | 2,232 | 2,285 |
| transfers.spec.md | 76 | 3,471 | 3,547 |
| transactions.spec.md | 53 | 2,361 | 2,414 |
| mfa.spec.md | 59 | 2,764 | 2,823 |
| **Total** | **241** | **10,828** | **11,069** |

The original files use CRLF line endings. Character counts obtained through Python text-mode reading normalize CRLF to LF; raw decoded character counts and byte counts include the original CRLF representation.

### Specification Distribution

- Specification files: 4.
- Average lines per file: 60.25.
- Minimum: 53.
- First quartile: 53.
- Median: 56.
- Third quartile: 63.25.
- Maximum: 76.

Quartiles were calculated using NumPy linear interpolation.

### SHA-256 Checksums

- `accounts.spec.md`: `838390da2d70bf5614d3ae3946d98cf6afc52560a7eb6d172ac7d907d7e4ad5c`
- `transfers.spec.md`: `38d642c9fc973a0e1663f02be888772cb6d0ebdcffbb867213e44608a13e9362`
- `transactions.spec.md`: `0ceaade0c249abe7ffd6b39fecccb2b733cf6ff4d44ecd54275912215205e90e`
- `mfa.spec.md`: `1c1114f9e3e8625fcb9f72f03acfe18c26b9da9775ba4da7a0f09f5d16721ad3`

## 3. Source Code Metrics

| Component | Files | Physical LOC |
|---|---:|---:|
| Backend Python production | 14 | 695 |
| Frontend TypeScript/TSX production | 9 | 1,046 |
| Frontend CSS production | 1 | 820 |
| **Total production** | **24** | **2,561** |

Configuration code, including 21 lines in `frontend/vite.config.ts`, was excluded from production LOC.

### Automated Test Code

| Component | Files including test infrastructure | LOC |
|---|---:|---:|
| Backend | 6 | 452 |
| Frontend | 5 | 599 |
| **Total** | **11** | **1,051** |

All LOC measurements count physical lines, including comments and blank lines.

## 4. Derived Metrics

- Code/specification ratio: 2,561 / 241 = **10.63**.
- Previously identified distinct testable requirements: 51.
- Functional requirements: 45.
- Non-functional requirements: 6.
- Requirements per 100 specification lines: 51 / 241 × 100 = **21.16**.

The specification correction clarified existing requirements without establishing new functional capabilities. The 51-requirement inventory is carried forward from the original audit; a new independent verification of all 51 requirements was not part of this measurement session.

## 5. Evolution Across Correction Cycle 01

| Metric | Initial implementation | Final implementation | Difference |
|---|---:|---:|---:|
| Specification files | 4 | 4 | 0 |
| Specification LOC | 235 | 241 | +6 |
| Backend production LOC | 663 | 695 | +32 |
| Frontend TS/TSX LOC | 1,046 | 1,046 | 0 |
| Frontend CSS LOC | 820 | 820 | 0 |
| Total production LOC | 2,529 | 2,561 | +32 |
| Backend test LOC | 371 | 452 | +81 |
| Frontend test LOC | 561 | 599 | +38 |
| Total test LOC | 932 | 1,051 | +119 |
| Automated tests | 40 | 45 | +5 |

The source-code and test-code changes total **+151 net physical lines** across the two measured checkpoints.

This agrees with the net result of the visible accepted edit operations (+159 added, -8 removed). The previous agent summary of +146 added and -7 removed is inconsistent with this evidence. Exact additions and deletions remain non-reproducible through Git because the project did not have a tracked pre-correction baseline.

## 6. Automated Test Verification

Latest previously observed post-correction test results:

- Backend Pytest: 22 passed, one warning.
- Frontend Vitest: 23 passed.
- Total automated tests: 45 passed.
- Production build: successful.

The final filesystem measurement itself did not rerun the tests.

## 7. Recovered Gemini CLI Session Statistics

The termination screenshot recorded the following session:

**Session ID:** `f7e1369b-b67f-4997-b9a9-2a228c9ecd17`

### Interaction Statistics

| Metric | Value |
|---|---:|
| Tool calls | 153 |
| Successful tool calls | 152 |
| Failed tool calls | 1 |
| Tool-call success rate | 99.3% |
| User agreement | 100%, 152 reviewed |
| CLI-reported code additions | 4,041 |
| CLI-reported code deletions | 141 |

The CLI-reported code-change statistics are cumulative session counters, not a Git diff of correction cycle 01.

### Processing Time

| Metric | Duration |
|---|---|
| Wall time | 2 h 43 min 27 s |
| Agent active | 2 h 4 min 14 s |
| API time | 30 min 4 s |
| Tool time | 1 h 34 min 10 s |

### Model Usage

| Model | Requests | Input tokens | Cache reads | Output tokens |
|---|---:|---:|---:|---:|
| gemini-3.8-flash | 146 | 16,593,024 | 15,464,495 | 70,736 |
| gemini-3-flash-preview | 4 | 47,764 | 0 | 478 |
| **Total** | **150** | **16,640,788** | **15,464,495** | **71,214** |

The first model was labeled `main` and the second `utility_loop_detector`.

The session included an API error indicating an invalid number of function response parts relative to function call parts. Consequently, the session's duration includes unsuccessful execution time and should not be interpreted solely as productive development time.

The CLI interface in a later session displayed `gemini-3.5-flash`, which differs from the main model identifier recorded in this session's usage report. The identifiers are preserved independently; their equivalence is not assumed.

These statistics describe the identified Gemini session, not necessarily every session used in Stage 1.

## 8. Reproducibility and Exclusions

The filesystem measurement used local Python commands, file enumeration, SHA-256 hashing, and NumPy percentile calculations.

Excluded from production code measurements:

- Automated test files and test infrastructure.
- Dependencies and `node_modules`.
- Build artifacts and `dist`.
- Python caches and virtual environments.
- Tessl, Gemini, Codex, and editor configuration directories.
- Generated database files.
- Research documentation and reports.
- Root build configuration files.

The session did not modify the project.

## 9. Outstanding Measurements

The following remain unresolved:

1. Final independent verification of all 51 previously identified requirements.
2. SonarQube static analysis metrics and technical debt.
3. Visual/manual functional assessment of the running application.
4. Token and timing data from other Gemini sessions, where applicable.
5. USD financial cost, which has not been established from billing evidence.
6. Exact historical Git diff of correction cycle 01.

This record closes the quantitative filesystem measurement checkpoint. Subsequent results must be documented separately.