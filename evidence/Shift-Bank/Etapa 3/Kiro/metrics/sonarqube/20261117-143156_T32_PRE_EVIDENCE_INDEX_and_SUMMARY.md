# T32 — SonarQube PRE-remediation Evidence Index & Summary (Shift Bank Stage 3, Kiro)

**Purpose:** Consolidated index and verification note for the Stage 3 (Kiro) SonarQube
**PRE-remediation** scan. This is read-only evidence consolidation. No scan was rerun, no
application code was modified, no corrections were applied, and no values were fabricated —
every number below traces to a preserved raw file in this directory.

**Evidence prefix:** `20261117-143156_T32_PRE_`
**Location:** `Etapa 3/_experiment_logs/Kiro/sonarqube/`
**Note generated (local):** 2026-11-17 14:31:56

---

## 1. Compute Engine task & analysis identity

Source: `..._ce_task.json`

| Field | Value |
|---|---|
| CE task id | `104e3187-6709-49a3-a6fb-60d8c2ca5263` |
| Task type | `REPORT` |
| Status | **SUCCESS** |
| analysisId | `b330beea-9010-4b1c-b036-6f61d6ac6675` |
| componentKey | `Shift-Bank---Stage-3---Kiro` |
| componentName | `Shift Bank Etapa 3 (Kiro)` |
| Submitter | `admin` |
| executedAt | 2026-11-17T19:33:31+0000 (executionTimeMs 4390) |
| warningCount | 1 — SCM provider autodetection failed (benign; no git metadata in scan context) |

Scanner (`..._scanner.log`) corroborates: `Project key: Shift-Bank---Stage-3---Kiro`,
`ANALYSIS SUCCESSFUL`, `EXECUTION SUCCESS`, total time 1:28.437s. Both coverage reports were
ingested (`Parsing report '/usr/src/backend/coverage.xml'`; `Analysing [/usr/src/frontend/coverage/lcov.info]`).

---

## 2. File inventory (filename → what it is)

All files present and non-empty (byte sizes shown for completeness).

| File | Bytes | Contents |
|---|---:|---|
| `..._ce_task.json` | 704 | CE task result: SUCCESS + analysisId + componentKey + submitter + warning |
| `..._measures.json` | 2,540 | Project measures (traditional + MQR metrics, size, coverage, duplication) |
| `..._quality_gate.json` | 100 | Quality Gate project status |
| `..._issues_p1.json` | 191,355 | All 172 issues, single page (ps=500, total=172) |
| `..._issues_p1_with_facets.json` | 191,355 | Same 172 issues + facet aggregations (severities, types, rules, impacts) |
| `..._rules_metadata.json` | 102,845 | Metadata for the 17 observed rules (name, type, clean-code attribute/category, MQR impacts) |
| `..._scanner.log` | 19,470 | Scanner stdout — ANALYSIS SUCCESSFUL, exit success |
| `..._sonar-project.properties` | 2,952 | Exact scanner configuration used |
| `..._backend_coverage.xml` | 77,421 | Imported backend Cobertura coverage (coverage.py 7.17.3; line-rate 0.952) |
| `..._frontend_lcov.info` | 19,411 | Imported frontend LCOV coverage (Vitest; near-zero line hits) |

**Completeness verdict: ALL required artifacts present and non-empty.** Issue count in the
JSON (`total:172`) matches the measures `code_smells=172` and the severity facet total
(138+29+4+1 = 172). No missing or inconsistent evidence; nothing blocks completion.

---

## 3. Quality Gate

Source: `..._quality_gate.json`

```json
{"projectStatus":{"status":"OK","conditions":[],"ignoredConditions":false,"caycStatus":"compliant"}}
```

- **Result: OK (PASSED).**
- `caycStatus`: **compliant** (Clean-as-You-Code).
- No failing conditions, no ignored conditions.

The gate passes because the default "Sonar way" gate evaluates *new code*, and there is no new-code
baseline on a first analysis. The 172 findings are overall-code debt and do not fail the gate.

---

## 4. Traditional metrics

Source: `..._measures.json`

| Metric | Value |
|---|---|
| bugs | 0 |
| vulnerabilities | 0 |
| security_hotspots | 0 |
| code_smells | **172** |
| reliability_rating | **A** (1.0) |
| security_rating | **A** (1.0) |
| security_review_rating | **A** (1.0) |
| sqale_rating (maintainability) | **A** (1.0) |
| sqale_index (total debt) | **831 min** (~13 h 51 m) |
| sqale_debt_ratio | 0.6% |
| reliability_remediation_effort | **0** |
| security_remediation_effort | 0 |
| duplicated_lines_density | 0.0% (0 blocks, 0 files) |
| coverage | **44.1%** |
| line_coverage | 44.2% |
| branch_coverage | 31.8% |
| lines_to_cover | 3,585 |
| uncovered_lines | 2,000 |
| ncloc | 4,970 (py=2,909; ts=1,748; css=313) |
| lines (physical) | 7,503 |
| complexity | 659 |
| cognitive_complexity | 449 |
| files | 40 |
| functions | 283 |
| classes | 47 |
| statements | 1,907 |
| comment_lines_density | 24.1% |

---

## 5. MQR (Multi-Quality Rule) metrics — with reliability divergence called out

Source: `..._measures.json` (`software_quality_*` metrics)

| MQR metric | Value |
|---|---|
| software_quality_maintainability_rating | **A** (1.0) |
| software_quality_security_rating | **A** (1.0) |
| software_quality_reliability_rating | **C** (3.0) |
| software_quality_maintainability_remediation_effort | 811 min |
| software_quality_reliability_remediation_effort | 205 min |
| software_quality_security_remediation_effort | 0 |
| software_quality_maintainability_debt_ratio | 0.5% |

### ⚠ Traditional-vs-MQR reliability divergence

- **Traditional `reliability_rating` = A (1.0)** and traditional `reliability_remediation_effort = 0`.
- **MQR `software_quality_reliability_rating` = C (3.0)** with 205 min of MQR reliability effort.

This divergence is real and expected given the data: under the MQR model, **38 issues carry a
RELIABILITY impact** (facet `impactSoftwareQualities`: RELIABILITY=38) even though **0 issues are
classified as traditional BUG type** (types facet: BUG=0, all 172 are CODE_SMELL). The RELIABILITY
impact comes almost entirely from:
- `typescript:S6772` ×37 — MAINTAINABILITY:MEDIUM **+ RELIABILITY:LOW**
- `typescript:S8786` ×1 — **RELIABILITY:MEDIUM** (regex backtracking; the single highest-severity
  reliability-impact finding and the key driver pushing the MQR reliability rating to C)

> Note on the brief: the `205 min` figure is the **MQR** reliability effort
> (`software_quality_reliability_remediation_effort`). The **traditional**
> `reliability_remediation_effort` is `0`. Both are preserved verbatim in `..._measures.json`.

---

## 6. Issues by severity

Source: `..._issues_p1_with_facets.json` (facets) — all are type CODE_SMELL (BUG=0, VULNERABILITY=0)

| Severity | Count |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 4 |
| MAJOR | 138 |
| MINOR | 29 |
| INFO | 1 |
| **Total** | **172** |

MQR impact severities facet: HIGH=4, MEDIUM=138, LOW=66, INFO=1, BLOCKER=0.
Clean-code attribute categories: INTENTIONAL=109, CONSISTENT=58, ADAPTABLE=5, RESPONSIBLE=0.

---

## 7. Issues by rule (name · MQR impact · typical area)

Source: `..._issues_p1_with_facets.json` (rules facet) + `..._rules_metadata.json`

| Rule | Count | Name | MQR impact(s) | Area |
|---|---:|---|---|---|
| python:S9073 | 86 | Composite assertions should be split | MAINT:MEDIUM | backend/tests |
| typescript:S6772 | 37 | Spacing between inline elements should be explicit | MAINT:MEDIUM, RELIABILITY:LOW | frontend/src |
| python:S9083 | 12 | Pytest fixture/mark parentheses consistency | MAINT:LOW | backend/tests |
| python:S5778 | 8 | Only one method invocation when testing exceptions | MAINT:MEDIUM | backend/tests |
| typescript:S6759 | 8 | React props should be read-only | MAINT:LOW | frontend/src |
| python:S8410 | 5 | Use `Annotated` type hints for FastAPI DI | MAINT:LOW | backend/app |
| python:S3776 | 3 | Cognitive Complexity too high | **MAINT:HIGH** | backend/app (all CRITICAL) |
| python:S5713 | 3 | Redundant exception class already caught | MAINT:LOW | backend/app |
| typescript:S3358 | 2 | Extract nested ternary into independent statement | MAINT:* | frontend/src |
| python:S1192 | 1 | Define a constant instead of duplicating a literal | **MAINT:HIGH** | backend/app (CRITICAL) |
| typescript:S8786 | 1 | Regex vulnerable to backtracking | **RELIABILITY:MEDIUM** | frontend/src |
| python:S107 | 1 | Too many function parameters | MAINT:MEDIUM | backend/app |
| python:S8409 | 1 | Redundant FastAPI `response_model` | MAINT:LOW | backend/app |
| python:S1135 | 1 | Complete the TODO comment | MAINT:INFO | backend/app |
| python:S9100 | 1 | Remove useless `yield` | MAINT:MEDIUM | backend/tests |
| typescript:S6819 | 1 | Prefer `output` of nested component (a11y/semantics) | MAINT:* | frontend/src |
| typescript:S7721 | 1 | (TypeScript rule, singleton) | MAINT:* | frontend/src |

(Rules marked `MAINT:*` have a maintainability impact recorded in `..._rules_metadata.json`;
only S6772 and S8786 add a RELIABILITY impact, which together account for the 38-issue RELIABILITY
facet and the MQR reliability-C rating.)

---

## 8. Production vs test split

Source: component paths in `..._issues_p1.json`

| Area | Issues | Remediation effort |
|---|---:|---:|
| backend/tests | 107 | 487 min |
| frontend/src | 50 | 265 min |
| backend/app | 15 | 79 min |
| **Total** | **172** | **831 min** |

> **Production code** (`backend/app` + `frontend/src`) = 65 issues / 344 min.
> **Test-only code** (`backend/tests`) = 107 issues / 487 min — the single largest block, dominated
> by `python:S9073` (composite assertions) and therefore the **lowest** correction priority.

---

## 9. The 4 CRITICAL issues (all in production `backend/app`)

Source: `..._issues_p1.json`

| # | Rule | File:line | Message | Effort | MQR |
|---|---|---|---|---:|---|
| 1 | python:S3776 | `backend/app/audit.py:315` | Reduce Cognitive Complexity from 17 to 15 | 7 min | MAINT:HIGH |
| 2 | python:S3776 | `backend/app/config.py:105` | Reduce Cognitive Complexity from 18 to 15 | 8 min | MAINT:HIGH |
| 3 | python:S3776 | `backend/app/crypto.py:80` | Reduce Cognitive Complexity from 18 to 15 | 8 min | MAINT:HIGH |
| 4 | python:S1192 | `backend/app/repository.py:342` | Define a constant instead of duplicating a literal 3× | 6 min | MAINT:HIGH |

All four are CODE_SMELL (there are zero BUG/VULNERABILITY issues). Combined effort: 29 min.

---

## 10. Recommended correction priorities (production-first; effort grounded in real debt minutes)

Totals are the sum of preserved per-issue `effort` values.

**P1 — The 4 CRITICAL production items (29 min).** Highest MQR maintainability severity (HIGH),
all in `backend/app`:
- 3× cognitive-complexity refactors: `audit.py:315` (7m), `config.py:105` (8m), `crypto.py:80` (8m).
- 1× duplicated-literal extraction: `repository.py:342` (6m).

**P2 — MQR reliability-C drivers in frontend production (~190 min).** These are what pull the MQR
reliability rating down to C:
- `typescript:S8786` ×1 — regex backtracking, **RELIABILITY:MEDIUM** (highest-severity reliability item).
- `typescript:S6772` ×37 — explicit JSX inline spacing, RELIABILITY:LOW (≈185 min at 5 min each).

**P3 — Remaining production smells (~125 min).** Other `backend/app` items (FastAPI `Annotated`
DI ×5, redundant exception classes ×3, redundant `response_model`, `S107` params 20m, TODO) and
remaining `frontend/src` smells (`S6759` read-only props ×8, `S3358` nested ternary ×2, `S6819`,
`S7721`).

**P4 — Test-only smells (`backend/tests`, 487 min) — lowest priority.** 107 findings, overwhelmingly
`python:S9073` composite assertions (×86) plus `python:S9083`/`S5778`/`S9100`. These do not affect
production behavior; address only if test-suite hygiene is in scope.

> Priority total check: P1(29) + production share of P2/P3 (265 frontend + 79 backend − overlap) …
> the authoritative totals are the per-area sums in §8 (production 344 min, tests 487 min, grand
> total 831 min = `sqale_index`).

---

## 11. Coverage aggregation explanation (44.1% is expected, NOT a defect)

- Sonar project coverage = **44.1%** (line 44.2%, branch 31.8%), `uncovered_lines=2,000` of
  `lines_to_cover=3,585`.
- This aggregates two very different sources:
  - **Backend** (`..._backend_coverage.xml`, coverage.py 7.17.3): `line-rate 0.952` — ~95% line
    coverage, consistent with the T31 backend-only figure.
  - **Frontend** (`..._frontend_lcov.info`, Vitest): near-zero line hits (e.g. `src/App.tsx` reports
    `(empty-report)` with all `DA` lines at 0). Only the 3 Task-30 smoke tests exist, so frontend
    line coverage is ~2.78% and its large uncovered line count dominates the aggregate.
- **Conclusion:** the aggregate 44.1% is the arithmetic combination of a well-covered backend and an
  intentionally minimal frontend (per Task 30). This is expected aggregation behavior, **not** a
  regression or defect. Backend coverage did not drop.

---

## 12. Project-key reconciliation note for T35 (config-only; no app code change)

- **Project key actually used in this PRE scan:** `Shift-Bank---Stage-3---Kiro`
  (confirmed in `..._ce_task.json`, `..._scanner.log`, and `..._sonar-project.properties`).
- **The T4-staged / original `sonar.projectKey`** in the preparation artifacts was
  `shift-bank-stage3-kiro` (different key).
- **Action for T35 (final scan):** the final scan **MUST reuse the same key actually used here**,
  `Shift-Bank---Stage-3---Kiro`, so the PRE and final analyses live under the same SonarQube
  project and compare 1:1. The researcher should reconcile `sonar.projectKey` in the staged
  properties to `Shift-Bank---Stage-3---Kiro` **before** running T35.
- This is a scanner-configuration note only. **No application code is affected.**

---

## 13. Status

- **T32 PRE-remediation evidence is COMPLETE** — all 10 required artifacts are present, non-empty,
  and mutually consistent; every figure above traces to a preserved raw file.
- **Execution STOPS here at the T33 researcher gate (G-SONAR-PRE).**
- **No T34 corrections begin without explicit researcher approval.**
