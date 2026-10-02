# Spec Kit — Stage 1 Metrics

## Gemini session metrics

### Session 001 — Spec Kit planning

- Session ID: `1d4d8431-8916-44a7-a6ec-2687561f4f46`
- Tool calls: 86
- Successful tool calls: 86
- Failed tool calls: 0
- Success rate: 100.0%
- User agreement: 100.0% (86 reviewed)
- Wall time: 1h 6m 7s
- Agent active: 22m 55s
- API time: 11m 40s
- Tool time: 11m 15s
- Model: `gemini-3.5-flash`
- Requests: 63
- Input tokens: 5,658,719
- Cache reads: 3,365,884
- Output tokens: 55,693

### Session 002 — Spec Kit implementation and validation

- Session ID: `07253ebf-ef55-4b14-b4b1-5a395fa93d4`
- Tool calls: 152
- Successful tool calls: 151
- Failed tool calls: 1
- Success rate: 99.3%
- User agreement: 100.0% (152 reviewed)
- Code changes reported: +5,257 / -2,588
- Wall time: 1h 43m 53s
- Agent active: 30m 42s
- API time: 23m 25s
- Tool time: 7m 17s
- Model: `gemini-3.5-flash`
- Requests: 163
- Input tokens: 23,627,709
- Cache reads: 18,014,851
- Output tokens: 84,277

### Session 003 — Final validation and implementation correction

- Session ID: `ea637f31-1ea8-4f04-96e4-0095f8d7db6e`
- Tool calls: 69
- Successful tool calls: 67
- Failed tool calls: 2
- Success rate: 97.1%
- User agreement: 100.0% (67 reviewed)
- Wall time: 24m 24s
- Agent active: 17m 42s
- API time: 8m 26s
- Tool time: 9m 15s
- Model usage included:
  - `gemini-3.8-flash`
  - `gemini-3-flash-preview`
  - `gemini-3.5-flash-lite`

This session included the implementation correction for structured MFA errors, expiration handling, and pending-transfer timer restoration.

### Session 004 — Final implementation validation

- Session ID: `f2a6562c-4ed6-4e6e-970d-ec00d2bb318`
- Tool calls: 65
- Successful tool calls: 65
- Failed tool calls: 0
- Success rate: 100.0%
- User agreement: 100.0% (65 reviewed)
- Code changes reported: +128 / -82
- Wall time: 17m 52s
- Agent active: 15m 39s
- API time: 12m 43s
- Tool time: 2m 55s
- Primary model: `gemini-3.5-flash`
- Requests: 68
- Input tokens: 2,927,465
- Cache reads: 2,132,180
- Output tokens: 7,105

Additional model usage:
- `gemini-3.1-flash-lite`: 1 request
- `gemini-3-flash-preview`: 3 requests

## Aggregate recorded Gemini activity

Across the five recorded Gemini sessions:

- Total tool calls: **412**
- Successful tool calls: **408**
- Failed tool calls: **4**
- Aggregate success rate: **99.0%**
- Aggregate recorded wall time: **4h 42m 30s**

The aggregate wall time is the sum of recorded Gemini session wall times and must not be interpreted as uninterrupted human work time.

## Reported code changes

Across sessions where Gemini reported line changes:

- Lines added: **8,030**
- Lines removed: **4,622**

These values represent Gemini's reported file changes across sessions and should not be interpreted as application-source changes performed exclusively during human correction rounds.

## SonarQube final analysis

- SonarQube: Community Build `26.9.0.129388`
- Scanner CLI: `8.1.0.6389`
- Project: `Shift Bank - Stage 1 - Spec Kit`
- Project key: `shift-bank-stage1-speckit`
- Sources: `backend`, `frontend`
- Files analyzed: **28**
- Quality Gate: **Passed**
- Security: **A — 0 open issues**
- Reliability: **C — 6 open issues**
- Maintainability: **A — 27 open issues**
- Coverage: **0.0%**
- Lines to cover: **761**
- Duplications: **2.1%**
- Security Hotspots: **0**

The Reliability rating and Maintainability issues are recorded as observed static-analysis results. They were not automatically treated as requirements for additional application changes.

## SonarQube analysis warnings

The final analysis reported warnings related to:

- SCM provider autodetection.
- Python version not being explicitly configured.
- `sonar.tests` not being explicitly configured.
- SCM/dirty-file detection because the analysis was executed from the working repository state.

These warnings did not prevent the analysis from completing successfully.

SonarQube Community Build also reports a limitation on its security analysis. Therefore, the Security A result must not be interpreted as proof that every possible security vulnerability is absent.

### Session 005 — Final documentation / validation work

- Session ID: `3a4aafb0-6293-468e-bba5-559eb2995d5c`
- Tool calls: 40
- Successful tool calls: 39
- Failed tool calls: 1
- Success rate: 97.5%
- User agreement: 100.0% (39 reviewed)
- Code changes reported: +63 / -39
- Wall time: 1h 10m 14s
- Agent active time: 9m 3s
- API time: 7m 29s
- Tool time: 1m 33s

#### Model Usage

- `gemini-3.8-flash`: 39 requests
  - Input tokens: 969,942
  - Cache reads: 723,258
  - Output tokens: 3,138
- `gemini-3.5-flash-lite`: 1 request
  - Input tokens: 709
  - Output tokens: 8
- `gemini-3-flash-preview`: 1 request
  - Input tokens: 4,351
  - Output tokens: 119