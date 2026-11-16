# Shift Bank E2 — SonarQube comparison

Project: Shift-Bank---Stage-2---OpenSpec  
Initial analysis ID: 74358b40-4391-4280-83df-9ae09061e287  
Final analysis ID: 5631177d-e954-42db-9a1f-795a50645944  
Final CE task: 8cb5713c-6066-44c0-b59a-84f90403a1c7  
Both Quality Gates: OK. No additional scan was run. Gate conditions are not inferred or expanded here.

| Metric | Initial | Final | Delta |
|---|---:|---:|---:|
| ncloc | 1354 | 1362 | +8 |
| lines | 1621 | 1631 | +10 |
| bugs | 5 | 5 | 0 |
| vulnerabilities | 0 | 0 | 0 |
| code_smells | 41 | 41 | 0 |
| sqale_index, minutes | 246 | 246 | 0 |
| complexity | 387 | 393 | +6 |
| cognitive_complexity | 288 | 289 | +1 |
| duplicated_lines_density | 0.0 | 0.0 | 0 |
| coverage | 0.0 | 0.0 | 0 |
| reliability_rating | 3.0 | 3.0 | 0 |
| security_rating | 1.0 | 1.0 | 0 |
| sqale_rating | 1.0 | 1.0 | 0 |

### Traditional and MQR findings
Traditional initial/final: bugs 5/5, vulnerabilities 0/0, code smells 41/41; ratings reliability 3.0/3.0, security 1.0/1.0, sqale 1.0/1.0.
MQR initial/final: reliability issues 5/5, security issues 0/0, maintainability issues 41/41; ratings reliability 3.0/3.0, security 1.0/1.0, maintainability 1.0/1.0; remediation effort 246/246 minutes. Traditional/MQR values are related classifications of the same analysis and are not summed as independent findings.

Functional corrections did not reduce static-analysis bugs, code smells, or technical debt; these remained unchanged. Coverage 0.0 is reported, but no usable imported coverage report was available. It does not show that automated tests exercised no code. NCLOC and lines deltas are scanner metrics, not added/deleted source LOC. No original complete Stage 1 text snapshot was available for a source line diff.

Raw JSON, CSV, and scanner logs are preserved unmodified in sonarqube/: initial and final CE task records, gates, metrics, summaries, comparison CSV, and scanner logs. They contain aggregate findings; individual issue descriptions were unavailable in the preserved exports.
