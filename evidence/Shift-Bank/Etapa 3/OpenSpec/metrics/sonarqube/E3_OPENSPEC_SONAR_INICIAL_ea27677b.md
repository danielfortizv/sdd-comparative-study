# Shift Bank E3 OpenSpec — Initial SonarQube Submission

**Analysis submission:** successful. **Server-side completion and metrics:** unverified because authenticated SonarQube read APIs returned HTTP 401. No rescan was performed.

- Project key: Shift-Bank---Stage-3---OpenSpec
- Compute Engine task: ea27677b-df48-4d54-9b89-25ac686bce41
- Analysis ID: unavailable until Compute Engine task is readable
- Analysis timestamp: unavailable from the server API
- Scanner: SonarScanner CLI 8.1.0.6389; original log E3_OPENSPEC_SONAR_SCAN_20261116T193919.log
- Server: SonarQube Community Build 26.9.0.129388
- Scanner log reports ANALYSIS SUCCESSFUL and EXECUTION SUCCESS and confirms report upload; this does not prove Compute Engine completion.

## D2 metrics

| Metric | Initial value | Status |
|---|---:|---|
| NCLOC / physical lines | unavailable | API HTTP 401; not zero |
| Bugs / Vulnerabilities / Code Smells | unavailable | Issues API HTTP 401; not zero |
| Security hotspots | unavailable | Hotspots API HTTP 401; not zero |
| Technical debt (minutes) | unavailable | Measures API HTTP 401 |
| Cyclomatic / cognitive complexity | unavailable | Measures API HTTP 401 |
| Duplicated lines (%) | unavailable | Measures API HTTP 401 |
| Coverage / new-code coverage / lines to cover | unavailable as Sonar metrics | Measures API HTTP 401 |
| Reliability / security / maintainability ratings | unavailable | Measures API HTTP 401 |
| MQR software-quality metrics | unavailable | Metrics/measures API HTTP 401 |
| Quality Gate and conditions | unavailable | Quality Gate API HTTP 401 |
| Hallazgos and Hallazgos/KLOC | not calculated | Inputs unavailable; traditional and MQR taxonomies not combined |

No issue findings or code corrections are inferred from these unavailable values.

## Scope and coverage reconciliation

The scanner indexed 20 files. The saved configuration selects 14 production files (5 backend modules and all 9 frontend/src files) and classifies 6 test files through sonar.tests (5 backend test files and 1 frontend test file). The scanner's 20-file text/secrets sensor count includes those test-classified files. This reconciles the earlier 14-source inventory; no test directory is configured as production source and no relevant application file is missing from the configured scope. The source SHA-256 list and exact properties are preserved for a comparable final scan.

Scanner log confirms the Python Cobertura sensor parsed backend-coverage-sonar.xml and the JavaScript/TypeScript sensor analyzed frontend-lcov-sonar.info, with no coverage-import warning. Server-computed coverage remains unverified. The scanner reported Sonar way profiles for CSS, JS, Python and TypeScript.

Log warnings: SCM provider autodetection failed because this copied project is not detected as a Git working tree; the text/secrets sensor also warned it only retrieves language-associated files without SCM. Keep the same scope/configuration for comparison and document this limitation.

## API access and next steps

The anonymous read-only checks for Compute Engine status, project analysis history, measures, Quality Gate, issues, hotspots, metrics definitions and quality profiles returned HTTP 401. The API response archive records each status/body. This indicates authentication is required; it is not evidence of an empty project. Minimum useful project access is an authenticated account with Browse and See Source Code; the task owner or an account with permission to read Compute Engine tasks may be needed for task details. A browser export of the project overview, measures, Quality Gate conditions, issues (all pages/statuses), and security hotspots can be used if API access cannot be granted.

No correction plan is proposed from unseen issues. After read access is available, retrieve the existing task ea27677b-df48-4d54-9b89-25ac686bce41, then prioritize verified encryption/key, audit/atomicity, authentication/HTTPS and reliability findings. Do not resubmit an analysis.

Full machine-readable status and access responses are in E3_OPENSPEC_SONAR_CE_INICIAL_ea27677b.json, E3_OPENSPEC_SONAR_METRICAS_INICIALES_ea27677b.json, E3_OPENSPEC_SONAR_ISSUES_INICIALES_ea27677b.json, E3_OPENSPEC_SONAR_GATE_INICIAL_ea27677b.json, E3_OPENSPEC_SONAR_API_ACCESS_ea27677b.json, and E3_OPENSPEC_SONAR_SCOPE_RECONCILIATION_ea27677b.json.
