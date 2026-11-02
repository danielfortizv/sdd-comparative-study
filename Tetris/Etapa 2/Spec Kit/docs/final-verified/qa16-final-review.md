# Final targeted read-only QA3 review after session 16

Snapshot: 2026-10-21 00:30:27 America/Bogota. `16-qa-final-regressions` completed at `2026-10-21T00:29:36.0926977-05:00`, exit 0, 375.325 seconds. This report inspects the written files and supersedes the open targeted QA3 test gaps in `qa12-final-review.md`; it does not replace historical evidence or root's independent execution logs.

No application, test, or native specification was edited by this reviewer. No test suite, app server, scanner, Gemini process, or Git mutation was run. Only this researcher review note was created. Final pass counts, coverage, build, dependency audit, browser observations, and Sonar status remain root's coordinated verification responsibility.

## Result

No additional concrete production defect or necessary unmet QA3 assertion gap was identified in the requested scope. The previously reported production timer/body/restart fixes remain present, and session 16 completed the remaining targeted test evidence. No unrelated queue cleanup, layout, or optional additional test work is requested by this review.

## Written evidence

| Required behavior | Evidence inspected | Review conclusion |
| --- | --- | --- |
| Entire immutable GET state, including activePiece | `backend/tests/unit/test_qa_iteration1.py:96-108` | `expected_snapshot` is frozen once before the three-request loop with `mode='json', by_alias=True`. Each actual GET must return 200 and equal that complete snapshot; current stored state must also remain equal. The actual route is enclosed by the zero-draw spy. The earlier post-route moving baseline defect is corrected. |
| An unresolved old queue does not block new generation | `frontend/tests/useGame.test.ts:720-785` | A's fetch is actually entered before restart; B's mutation completes while A remains unresolved. |
| Queued A2 is suppressed after A1 settles following restart | `useGame.test.ts:787-880` | A1 fetch is proven in flight at 834-835; A2 is then queued and count stays one at 837-846. B restarts and mutates successfully at 848-860. A1 settles, microtasks flush, B's state stays unchanged by A, and old-session fetch count remains one at 875-880. This now combines the previously separated causal windows. |
| StrictMode setup/cleanup compatibility and final disposal | `useGame.test.ts:1291-1378` | Real React.StrictMode wrapper at 1315-1317; game starts, A1 dispatches, A2 remains queued, final unmount precedes A1 settlement, and timer advance produces no additional fetch. The last exposed game reference/score remains unchanged; no invalid null-after-unmount expectation remains. |
| Unmount with in-flight automatic tick and queued user action | `useGame.test.ts:1116-1189` | Tick dispatch is asserted, a move is queued behind it, pre-unmount game is captured, then unmount precedes resolution and 2000-ms timer advance. Assertions require moveCount 0, tickCount 1, identical exposed snapshot and original score. |
| Terminal game over suppresses already queued action and stops gravity | `useGame.test.ts:1192-1288` | First action is proven dispatched before a second is queued. Resolving the first to game_over changes terminal state, queued second action never dispatches, and 2000 ms produces zero additional ticks. |
| Exact 500/450/100-ms scheduling | `useGame.test.ts:512-582` | Request-count deltas at 499+1, 449+1, and 99+1 ms remain present. The 449-ms segment crosses the obsolete 500-ms timer deadline and would expose that interval surviving the first reschedule. |
| Delayed creation-body ownership | `useGame.test.ts:588-718` | Explicit microtask flush and `jsonACalled` barriers precede B's creation in both success and failure cases. A's body then resolves/rejects in the required newer-generation window. |
| Old A automatic completion cannot release pending B tick | `useGame.test.ts:955-1073` | A and B dispatch barriers precede A settlement. Multiple B intervals while B is pending admit no burst; B settlement and subsequent proper interval have explicit request counts. |
| Canonical preview geometry and C/c regression evidence | `frontend/tests/App.test.tsx:194-257`; `useGame.test.ts:91-160` | Seven piece types are parameterized and rendered occupied coordinates compared in both Next/Hold slots. Lowercase and uppercase Hold independently clear request history and require one new request, preserving the earlier fixes. |

## Production source remains consistent with the tests

`frontend/src/hooks/useGame.ts` still uses separate generation queues, ownership checks after both fetch and JSON parsing, synchronous game-ref writes, and disposal guards. The automatic timer captures its generation at line 217, verifies it before admission at 224-228, creates a `{gen,id}` owner at 234-235, and clears only that same owner at 237-244. Session 16 did not change this hook from the source already reviewed after session 12.

The backend production rules remain the previously inspected scoring/line/level/gravity/Hold implementation. The scope of session 16's backend change is verification: complete frozen pre-route state equality. No new game-rule production change is needed from this review.

## Snapshot hashes (SHA-256)

| File | Hash |
| --- | --- |
| `frontend/src/hooks/useGame.ts` | `A3E99960E13271986929D8D3D4BDDFE786B911CF3C7EB7D295811CC2A0E98A37` |
| `frontend/tests/useGame.test.ts` | `F158739FA474C49F01572C06D41192AA5502F8E3D831AD0F71B0D71034828DE4` |
| `frontend/tests/App.test.tsx` | `93DF487F3E5C3CE78864B9D7C968C9B7A7615046CF182C8AB9DEC86E2031E953` |
| `backend/tests/unit/test_qa_iteration1.py` | `7698A0279F1A1382F6D330AE79814ED6E4550CF81720A0EAF5AD53F18161F85A` |

These hashes bind this static review to the current artifacts. A successful CLI exit alone is not counted as independent verification. Attach root's executed full-suite, coverage/build/audit/Sonar and browser evidence before final acceptance.
