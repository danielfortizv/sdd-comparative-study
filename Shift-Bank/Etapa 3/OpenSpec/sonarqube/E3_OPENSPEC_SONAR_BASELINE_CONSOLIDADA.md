# Stage 3 OpenSpec SonarQube baseline (frozen)

## Provenance

The extraction at `../_experiment_logs/OpenSpec/sonarqube/EXTRACCION_INICIAL_20261117T141345069/` reports CE task `ea27677b-df48-4d54-9b89-25ac686bce41`, project `Shift-Bank---Stage-3---OpenSpec`, status `SUCCESS`, and analysis ID `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`. Its `ce.json` matches the task and project, and gives executedAt `2026-11-17T00:40:14+0000`. The extraction summary, measures, gate, and issues all identify that project; no later Stage 3 scan was submitted before extraction. The baseline extraction files are preserved unchanged and their hashes are in `E3_OPENSPEC_SONAR_BASELINE_EVIDENCE_SHA256.json`.

## D2 metrics

| Metric | Initial value | Interpretation |
|---|---:|---|
| NCLOC | 1,859 | SonarQube `ncloc` |
| Physical lines | 2,219 | `lines` |
| Bugs | 5 | Traditional issue taxonomy |
| Vulnerabilities | 0 | Traditional issue taxonomy |
| Code Smells | 47 | Traditional issue taxonomy |
| Security hotspots metric | 0 | Measure value; hotspot detail endpoint separately returned 403 |
| Technical debt | 301 minutes | `sqale_index` |
| Cyclomatic complexity | 528 | `complexity` |
| Cognitive complexity | 464 | `cognitive_complexity` |
| Duplicated lines density | 0.0% | `duplicated_lines_density` |
| Overall coverage | 80.7% | SonarQube imported measure |
| Line coverage | 80.8% | `line_coverage` |
| Lines to cover | 1,163 | `lines_to_cover` |
| Uncovered lines | 223 | `uncovered_lines` |
| Reliability rating | C (3.0) | `reliability_rating` |
| Security rating | A (1.0) | `security_rating` |
| Maintainability rating | A (1.0) | `sqale_rating` |
| MQR reliability issues / rating | 5 / C (3.0) | Kept separate from traditional counts |
| MQR security issues / rating | 0 / A (1.0) | Kept separate from traditional counts |
| MQR maintainability issues / rating | 47 / A (1.0) | Kept separate from traditional counts |
| MQR maintainability debt | Unavailable | `software_quality_maintainability_debt` unsupported; not imputed |

Traditional findings = 5 + 0 + 47 = **52**. Findings per KLOC = 52 / (1,859 / 1,000) = **27.972** (three decimals). This excludes MQR counts to avoid double counting.

## Gate and issue inventory

Quality Gate was **OK**, `caycStatus` compliant, with `conditions: []`; no configured condition was evaluated. Do not interpret this as a finding-free project.

`issues.json` reports one page, HTTP 200, and 52 items. The complete CSV agrees: 5 `BUG` issues (all MAJOR, all `typescript:S9011`, in `frontend/src/App.tsx`); 47 `CODE_SMELL`s consisting of 39 `MAIN` and 8 `TEST` scope. Severity totals are 14 CRITICAL, 32 MAJOR, 6 MINOR. All 14 CRITICAL are Code Smells, not reliability or security vulnerabilities. Traditional Bugs/Vulnerabilities/Code Smells and MQR reliability/security/maintainability metrics are distinct taxonomies.

The five baseline Bugs were:

- `d48cd859-5ad5-43c6-9d67-27e349eeca8f` — `typescript:S9011`, line 196.
- `1825d55d-c181-4736-b480-8d643469dfea` — `typescript:S9011`, line 201.
- `1ca82a68-f8c8-4707-ad9c-198bf1feddbc` — `typescript:S9011`, line 204.
- `d1809aca-8c80-4272-ad14-3bfd526a68a1` — `typescript:S9011`, line 216.
- `e8ac08b1-6992-40c7-92e2-4af5cba95154` — `typescript:S9011`, line 220.

No vulnerability issue was reported. Hotspot details were not available: `hotspots.json` is HTTP 403 with no items, so the measure value 0 does not substitute for a reviewed hotspot list.

## Scope and coverage attribution

The frozen `sonarqube/sonar-project.properties` hash is `c6d52175bc0623c3c5b64fad0dbe705fb9f8e3cbaf3862466bf8e47277f87ee1`. Its 14 production files are 5 backend modules (`main.py`, `banking.py`, `database.py`, `encryption.py`, `audit.py`) plus 9 files under `frontend/src`. The 20 indexed files reconcile as 14 production files plus 6 test-classified files (5 backend tests and 1 frontend test); no tests were treated as production and no configured production files were missing. Python and frontend coverage sensors processed the input reports without coverage-import warnings. SonarQube's imported coverage measure is the 80.7% above; frontend LCOV covers only three `.mjs` modules, not React TSX paths.

The original extraction's hotspot 403 and its single CE SCM autodetection warning are limitations. No scan, rule profile, Quality Gate, source scope, exclusion, or coverage path was changed in the correction round.
