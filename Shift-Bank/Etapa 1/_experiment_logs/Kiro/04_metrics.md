# Kiro — Stage 1 Metrics

## 1. Execution Metrics

| Metric | Value |
|---|---:|
| Executions | 8 |
| Total estimated credits | 18.85 |
| Total elapsed time | 51m 36s |
| Average credits / execution | 2.36 |
| Average elapsed time / execution | 6m 27s |

> Note: Kiro reports estimated credits per execution. The aggregate above corresponds to the 8 recorded executions.

---

## 2. Specification Metrics

| Metric | Value |
|---|---:|
| Specification files | 3 |
| Total specification lines | 668 |

### Specification artifacts

1. `.kiro/specs/shift-bank/requirements.md` — 159 lines
2. `.kiro/specs/shift-bank/design.md` — 376 lines
3. `.kiro/specs/shift-bank/tasks.md` — 133 lines

**Total:** 668 lines

---

## 3. SonarQube Metrics

**Project:** `shift-bank-stage1-kiro`

| Metric | Value |
|---|---:|
| Quality Gate | Passed |
| NCLOC | 1,264 |
| Bugs | 0 |
| Vulnerabilities | 0 |
| Code Smells | 14 |
| Cognitive Complexity | 73 |
| Coverage | 0.0% |
| Duplicated Lines Density | 0.0% |
| Security Rating | A |
| Reliability Rating | A |
| Maintainability Rating | A |
| Technical Debt (SQALE Index) | 79 |

### SonarQube analysis configuration

- Sources: `backend, frontend`
- SonarQube: `localhost:9000`
- Project key: `shift-bank-stage1-kiro`
- Scanner image: `sdd-sonar-scanner:frozen`
- Excluded: virtual environments, `node_modules`, build/dist artifacts, coverage and SQLite databases.

---

## 4. Functional Validation

| Validation | Result |
|---|---|
| Application implementation | Passed |
| Backend validation | Passed |
| Frontend build/type-check | Passed |
| Manual functional validation | Passed |
| MFA threshold behavior | Passed |
| MFA incorrect code/retry | Passed |
| MFA expiration | Passed |
| Insufficient funds during MFA | Passed |
| Historical transactions | Passed |
| Balance integrity | Passed |
| Internal ID exposure check | Passed |

### Observed scope difference

When the MFA dialog is cancelled, the frontend closes the dialog and does not provide a Resume mechanism for the pending transfer.

This was reviewed against `requirements.md`, `design.md` and `tasks.md` and was classified as:

**Not an implementation issue / outside the approved scope.**

The pending transfer remains on the backend until expiration; the limitation is that the frontend does not provide a mechanism to resume it after dismissal.

---

## 5. Implementation

| Metric | Value |
|---|---:|
| Tasks planned | 22 |
| Tasks implemented | 22 |
| Implementation completion | 100% |
| Application source correction rounds after implementation | 0 |
| Post-implementation compliance status | Conformant |

---

## 6. Notes

Kiro generated and implemented the complete requirements → design → tasks → implementation workflow.

The three specification artifacts were:

- `requirements.md`
- `design.md`
- `tasks.md`

SonarQube reported no bugs or vulnerabilities, 14 code smells, 73 cognitive complexity, 0% test coverage and 0% duplication.