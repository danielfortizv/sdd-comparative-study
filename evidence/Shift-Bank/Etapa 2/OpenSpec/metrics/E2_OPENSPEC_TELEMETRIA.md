# Shift Bank E2 — Telemetry and deviations

## Recorded environment and deviations
- The experiment used Codex, not Gemini CLI as in the original plan.
- Codex CLI recorded as 0.168.0.
- OpenSpec observed as 1.11.0; preparation record reports 1.9.0.
- Recorded runtimes: Python 3.13.2, Node.js 24.19.0, npm 11.17.0, Vite 5.4.21.
- Exact internal model ID is not present in available evidence.
- No reliable token, cost, total tool-call, total session count, or all-session duration telemetry exists. No such numbers are estimated.
- No subagents were used for this consolidation; no parallel agent runtimes are available. Existing records do not provide agent runtime/session identifiers for earlier turns. Compacted/resumed turns are not counted as separate sessions.

## Measured implementation time
E2_OPENSPEC_IMPLEMENTATION_LOG.md records implementation from 2026-11-16 16:59:31.3817947 UTC to 17:34:03 UTC, approximately 34 min 32 s. Preparation/discovery was excluded. Time for the later correction/audit and final consolidation has no reliable start/end measurement and is not estimated.

## Human decisions and interventions
Traceable decisions: LIM-D01, LIM-D02, UTC-D01, ACH-D01, REC-D01, REC-D02, REC-D03, SPEC-D01 through SPEC-D04, REVIEW-F01 through REVIEW-F03, followed by explicit approval of the 22-task apply phase. They are recorded as decision identifiers, not a count of distinct sessions/messages.

## Recorded errors and fixes
- REC-D03 test exposed check ordering that obscured the late-first-execution outcome; validation order was corrected.
- Early isolated tests exposed fixture/assertion mistakes involving MFA threshold, daily usage, an open SQLite connection, and concurrent values; corrected before final passing suite.
- Initial sandbox Vite access and unsupported PowerShell UTC parameter were handled and recorded in implementation evidence.
- Final functional audit caught missing status refresh in the open UI; periodic polling and a cancellation test were added.
- First build after polling change identified missing TypeScript declaration for the MJS helper; refreshPolling.d.mts was added and subsequent build passed.
- Anonymous Sonar issues API returned HTTP 401; no credentials were available or saved.
- No Sonar scan was run in the final closure.

## Final observed verification
22 backend tests PASS; 5 frontend tests PASS; production build PASS; OpenSpec strict validation PASS; 22/22 tasks complete. These are executed test counts, not the 91 acceptance scenario count.
