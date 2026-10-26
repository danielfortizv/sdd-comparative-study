# Read-only review of session 17 Sonar style corrections

Snapshot: 2026-10-21 00:38:12 America/Bogota. `17-qa-sonar-style` completed at `2026-10-21T00:37:55.9223958-05:00`, exit 0, 313.986 seconds. Compared only the affected hook, hook tests, and native spec/tasks with the retained `docs/generation-16/files` snapshot. No application/test/native file edits, suites, scanners, servers, or Git mutations were performed by this reviewer.

## Result

The tiny production/test diff preserves the timer ownership logic and meaningful assertions. No new correctness defect or assertion weakening was found in these changes. The prior QA16 targeted correctness review continues to apply; final repeated suites and Sonar status must come from root's independent verification.

## Exact source/test diff

- `frontend/src/hooks/useGame.ts:230`: replaces `activeToken && activeToken.gen === intervalGen` with `activeToken?.gen === intervalGen`. An absent token still does not satisfy the numeric generation comparison; a matching token still coalesces the tick.
- Hook lines 239-240: replaces the non-null prefix plus direct generation/request ID reads with `pendingTickTokenRef.current?.gen === myToken.gen && pendingTickTokenRef.current?.id === myToken.id`. Both ownership checks remain conjunctive. An old-generation or old-request completion still cannot clear another tick's token. No queue, timer admission, generation check, or disposal behavior changed.
- `frontend/tests/useGame.test.ts:1247,1260,1279`: changes exactly three `expect(mutationUrls.length).toBe(1)` assertions to `expect(mutationUrls).toHaveLength(1)`. Both forms require the same array length. The A1-in-flight barrier, A2-queued barrier, terminal response, and A2-suppressed assertion remain in their original locations. No assertion or test body was removed.

No other hook/test changes appeared in the comparison with generation 16.

## Native specifications preceded generated changes

Read-only extraction of retained Gemini tool-call records, deduplicated by call ID and bounded to session 17's timestamps, found these successful mutations in order (UTC):

| Timestamp | Mutation |
| --- | --- |
| 2026-10-21 05:33:43.549 | `specs/002-extend-tetris-stage2/spec.md` revised |
| 2026-10-21 05:33:53.570 | `specs/002-extend-tetris-stage2/tasks.md` revised |
| 2026-10-21 05:34:39.291 | `frontend/src/hooks/useGame.ts` corrected |
| 2026-10-21 05:36:07.360 | `frontend/tests/useGame.test.ts` corrected |
| 2026-10-21 05:37:41.289 | Native tasks updated after the corrections |

The native requirement addition explicitly calls for Sonar rules S6582/S5906 while preserving generation/request identity guards and equivalent assertions. The recorded order satisfies the study's specification-first correction rule for this patch. The reviewer made only this researcher note.
