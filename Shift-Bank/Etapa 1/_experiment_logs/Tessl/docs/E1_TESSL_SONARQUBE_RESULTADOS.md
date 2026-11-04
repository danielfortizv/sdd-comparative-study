# Tessl — Stage 1 — SonarQube Static Code Quality Results

## 1. Analysis Identification

- Case study: Shift Bank.
- Stage: 1 — Final post-correction implementation.
- SDD tool: Tessl.
- Analysis date: November 1, 2026 (Colombia local time).
- SonarQube: Community Build 26.9.0.129388.
- SonarScanner CLI: 8.1.0.6389.
- Project key: `Shift-Bank---Stage-1---Tessl`.
- Compute Engine task: `a44da0ec-0849-4c9e-b31b-9dedcf1c2df9`.
- Analysis ID: `6162a378-470a-415b-8dc8-65672ca29dfe`.
- Analysis status: SUCCESS.
- Quality Gate reported status: OK, with zero configured conditions.

## 2. Analysis Scope

The scanner analyzed the Shift Bank Python backend and React/TypeScript/CSS frontend under one SonarQube project.

- Files indexed: 41.
- Languages detected: Python, TypeScript, CSS.
- Quality profiles: Sonar way.
- Scanner analysis duration: 44.045 seconds.
- Scanner total execution duration: 50.624 seconds.

Automated tests were designated separately from production sources. Node dependencies, compiled frontend assets, Python caches, and the local database were excluded.

The scanner reported that no SCM provider was detected. The analysis nevertheless completed successfully.

## 3. Static Analysis Metrics

| Metric | SonarQube key | Value |
|---|---|---:|
| Bugs | `bugs` | 0 |
| Vulnerabilities | `vulnerabilities` | 0 |
| Code smells | `code_smells` | 21 |
| Technical debt | `sqale_index` | 82 minutes |
| Cognitive complexity | `cognitive_complexity` | 98 |
| Duplicated lines | `duplicated_lines_density` | 0.0% |
| Reliability rating | `reliability_rating` | A (1.0) |
| Security rating | `security_rating` | A (1.0) |
| Maintainability rating | `sqale_rating` | A (1.0) |
| Non-comment LOC | `ncloc` | 2,182 |
| SonarQube lines | `lines` | 2,585 |
| Reported coverage | `coverage` | 0.0% |

Ratings were interpreted using the standard SonarQube metric scale, where a numerical rating of 1.0 corresponds to A.

## 4. Derived Quality Indicators

Using SonarQube's 2,182 non-comment lines as the normalization denominator:

- Code smells per KLOC: 21 / 2.182 = **9.62**.
- Total detected bugs and vulnerabilities: **0**.
- Total detected bugs, vulnerabilities, and code smells: **21**.
- Total detected issues per KLOC: **9.62**.
- Estimated technical debt per KLOC: 82 / 2.182 = **37.58 minutes**.

These are normalized indicators derived from the observed metrics, not additional SonarQube API measurements.

## 5. Interpretation

### Reliability

SonarQube detected no bugs and assigned a Reliability Rating of A.

This indicates no bug-classified issues were identified by the enabled static analysis rules. It does not prove that the application is free of runtime defects.

### Security

SonarQube detected no vulnerabilities and assigned a Security Rating of A.

This result reflects the scanner's configured rules and analyzed files. It does not substitute for penetration testing, dependency security analysis, or broader security verification.

### Maintainability

The scanner identified 21 code smells and estimated 82 minutes of technical debt.

Despite these maintainability findings, the reported Maintainability Rating was A. This indicates a favorable maintainability classification under the active SonarQube rating system.

### Complexity and Duplication

The aggregate cognitive complexity was 98, and duplicated-line density was 0.0%.

The absence of detected duplication is favorable. However, the complexity figure is an aggregate measurement and should not be interpreted as the cognitive complexity of an individual function.

## 6. Coverage Measurement Limitation

The SonarQube API returned `coverage = 0.0`.

No Python or frontend coverage reports were explicitly generated and supplied to the scanner during this analysis.

Therefore, the result is classified as **coverage not independently established by the experiment**, rather than evidence that the existing automated tests exercised no application code.

The earlier verification checkpoint reported 45 passing automated tests. Test success and test coverage are separate measurements.

## 7. Quality Gate Interpretation

The Quality Gate API returned:

```json
{
  "status": "OK",
  "conditions": [],
  "ignoredConditions": false,
  "caycStatus": "compliant"
}
```

The reported gate status is OK, but the conditions array is empty.

Therefore, the experiment cannot claim that any explicit minimum coverage, maximum technical debt, issue threshold, or other quality criterion was evaluated and passed by this gate.

## 8. LOC Measurement Distinction

The final filesystem measurement identified 2,561 physical production source lines, including comments and blank lines.

SonarQube independently reported 2,182 non-comment lines and 2,585 lines under its own indexing and measurement definitions.

These values must be preserved separately because the source scopes and counting rules are not identical.

The standard code/specification ratio uses the reproducible filesystem measurement of 2,561 physical production lines divided by 241 specification lines, yielding 10.63.

The issue-density calculation instead uses the SonarQube denominator of 2,182 non-comment lines to remain consistent with the static analysis source.

## 9. Experimental Validity

This analysis was performed after the approved specification correction cycle, not on the initial implementation.

The results represent one completed static analysis of the final Stage 1 Tessl implementation.

No source-code corrections were made in response to SonarQube findings during this measurement.

The detected code smells and technical debt remain recorded as observed findings, preserving the generated implementation for comparison with the other SDD tools.

## 10. Conclusion

The final Shift Bank Stage 1 implementation generated through Tessl received A ratings for reliability, security, and maintainability.

SonarQube identified zero bugs, zero vulnerabilities, 21 code smells, 82 minutes of technical debt, an aggregate cognitive complexity of 98, and 0.0% detected duplication.

These findings suggest favorable static reliability and security results, with remaining maintainability improvements identified by the scanner.

The reported quality ratings must be understood within the limits of static analysis. Code coverage was not established, and the Quality Gate had no configured conditions.

This document constitutes the final SonarQube quantitative measurement record for Shift Bank Stage 1 using Tessl.