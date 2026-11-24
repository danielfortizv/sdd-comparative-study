# E3 Kiro D1 Evidence Manifest

## Original telemetry

| Source | Role | SHA-256 | Reference |
|---|---|---|---|
| C:\Users\danie\.kiro\sessions\b9af73140b3bde55\sess_7f1b54d0-e77f-4cb7-b439-d06e5aa2dca1\session.json | Session ID, workspace, creation and last-modified timestamps | 4B1C378F1968ABDA62791875669E1AB1AAD644E1E2C53E3BACD38D6E5A4A3CF1 | Session sess_7f1b54d0-e77f-4cb7-b439-d06e5aa2dca1 |
| C:\Users\danie\.kiro\sessions\b9af73140b3bde55\sess_7f1b54d0-e77f-4cb7-b439-d06e5aa2dca1\messages.jsonl | User/assistant events, tool calls/results, interaction resolutions, sub-agent events, usage summaries | 2223039EE31A1B8F6946F68CED59A782EE005FB8C2AF8253803FE2157D53F28C | Stage 3 begins line 798 at event 835f6c6d-83ba-4099-97a0-9c89bd220833; T34 prompt dff2c00b-3ff1-4973-be64-eccd6ca59278; closure prompt 03f9fa7c-be02-493e-b833-229676676159 at line 3202 |

## Experiment-log cross references

- ../bitacora.md — activity log and execution chronology.
- ../README.md — log directory conventions and experiment context.
- ../REPORTE_FINAL_ETAPA3_KIRO.md — final Stage 3 outcome summary; not used to derive token/credit metrics.
- ../pruebas/ and ../sonarqube/ — preserved test and SonarQube evidence cited in the conversation; not used to infer Kiro usage.

These files provide context and corroboration. Native messages.jsonl and session.json are the authority for recovered D1 telemetry. Raw source files were not modified.

## Integrity and reproducibility

Hashes were computed with SHA-256 using PowerShell Get-FileHash on the original files. To verify:

Get-FileHash -Algorithm SHA256 -LiteralPath '<source path>'

To reproduce the event counts and usage totals, parse messages.jsonl line by line as JSON and retain timestamps at or after 2026-11-16T19:36:25.080Z. See E3_KIRO_D1_METODO.md for aggregation rules and caveats. The raw source export is intentionally left in place rather than duplicated into the experiment log directory.
