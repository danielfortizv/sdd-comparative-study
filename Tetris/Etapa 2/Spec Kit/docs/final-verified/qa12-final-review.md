# Read-only review after interrupted QA session 12

Review snapshot began 2026-10-21 00:15:57 America/Bogota. Read `docs/12-qa-timer-retry.run.json`, the current hook/tests, and the unchanged researcher clarification `../shared/spec-kit-qa-timer-ownership.txt`. Session 12 ended at `2026-10-20T21:00:41.5090227-05:00`, after 1,513.504 seconds, exit 1. Its stderr reports `exception TypeError: fetch failed sending request`. This is a partially completed correction, not a successful final validation.

The reviewer did not edit application code, generated tests, or native specifications and did not run any suite/server/scanner/Gemini process. Line references identify this snapshot and may move during retry 13.

## Production source

No remaining production defect was identified in the requested hook paths by inspection. The former automatic-tick ownership defect is corrected in `frontend/src/hooks/useGame.ts`:

- Lines 30-31 maintain a generation/request token rather than a global boolean.
- Restart clears the old token at line 57 and creates a new generation-specific queue at line 64.
- Timer callbacks capture `intervalGen` at line 217 and reject obsolete generations at lines 224-228 before admitting work.
- Lines 229-235 admit at most one outstanding automatic tick for that generation.
- The completion handler at lines 237-244 clears only the identical generation/request owner. A completion from A cannot release B's pending marker.
- Restart ownership is checked after response headers and again after JSON parsing (lines 68-79); mutation responses are likewise checked after both awaits (lines 146-164).
- Synchronous `gameRef` updates and per-generation queues preserve the fixes for stale state and an unresolved A operation blocking new game B.

This conclusion is a targeted static audit, not an executed proof of all behavior. No queue garbage collection, styling, or other unrelated work is requested here.

## Meaningful evidence now present

1. **Precise gravity boundaries:** `frontend/tests/useGame.test.ts:512-582` now asserts count deltas at 499+1, 449+1, and 99+1 milliseconds. In particular, advancing from 950 to 1049 ms also crosses the obsolete original timer's 1000-ms deadline, so an uncancelled 500-ms interval would add a request and fail the count assertion. This replaces the earlier historical-call matcher weakness.
2. **Delayed creation bodies actually entered:** R1(a) at lines 588-647 and R1(b) at 649-718 flush microtasks and assert `jsonACalled` before B starts. The promises are explicitly still pending until their later resolver/rejecter is called. These now exercise the intended vulnerable await window.
3. **Old mutation really in flight:** R2(c), lines 720-785, queues A1/A2, flushes, and asserts one A fetch before B starts. A remains unresolved while B's mutation completes, proving the new generation is not blocked by A's queue. R2(d), lines 787-843, likewise asserts an A fetch before B and settles A afterward.
4. **A/B automatic tick race:** lines 917-1035 explicitly flush and assert A's automatic tick has begun before restart and B's tick has begun before A settles. After A settles, three more B timer intervals produce no additional request; after B resolves, another assertion detects any queued burst. This would detect the old unowned-finally implementation. The current source token fix directly addresses it.
5. **Game-over gravity behavior:** lines 1037-1076 return `game_over` from the actual hook's tick response, advance 2000 ms, and require the tick count to remain one.
6. **Real StrictMode wrapper:** lines 1134-1136 now use `React.StrictMode`; start/play assertions at 1140-1152 meaningfully exercise the hook after StrictMode's setup/cleanup cycle. The final unmount assertions still need correction below.
7. **Previously corrected evidence preserved:** separate C/c tests retain fresh request-count assertions, and rendered App tests retain all seven canonical preview-coordinate comparisons in both slots. The actual GET-route random-choice spy remains present at `backend/tests/unit/test_qa_iteration1.py:61-66`.

## Exact remaining necessary test corrections

### T1 — Two unmount assertions expect behavior that unmount does not provide

`useGame.test.ts:1122-1123` and `:1154-1156` expect `result.current.game` to become null after `unmount()`. `renderHook` retains the last returned result. The hook's unmount cleanup marks `disposedRef` at `useGame.ts:25-27` and clears the timer; it does not render a null game. The last valid game is therefore the expected retained snapshot. These assertions are inconsistent with the inspected code; do not change correct disposal behavior merely to force a null result.

Capture the last exposed state before unmount, settle the deferred work after unmount, and assert the exposed result remains unchanged plus no later fetch/queued dispatch occurs. Advance the fake timer to establish cancellation behavior. In the StrictMode test, enqueue meaningful work before final unmount and prove it cannot dispatch afterward. The present tests neither enqueue a second user action behind the pending tick nor verify post-unmount dispatch counts, despite their titles.

### T2 — Complete GET equality still excludes the active piece

`backend/tests/unit/test_qa_iteration1.py:97-112` still compares selected fields after one actual GET; `activePiece` is omitted. This did not change during session 12. Use the complete pre-route serialized snapshot with JSON-compatible values and aliases, e.g. `model_dump(mode='json', by_alias=True)`, and require exact whole-response equality across repeated successful actual GET calls. Preserve the existing real route zero-draw spy and the complete rejection/game-over snapshots.

### T3 — Settling and suppressing queued old work needs one combined causal assertion

R2(c) proves A2 is queued behind A1 but intentionally never resolves A1, so it cannot demonstrate that A2 is discarded after A1 settles. R2(d) resolves A1 after B starts, but never queues an A2 before restart and never asserts the old fetch count remains one afterward.

Complete the existing R2(d) scenario by queuing an additional old action behind the asserted in-flight A1, verify it has not dispatched, restart, settle A1, then require the old-session fetch count to remain one while B remains unchanged. This is the explicit queue-discard evidence already requested in the QA3 clarification, not new product scope.

### T4 — The pending/queued disposal title currently overstates its scenario

Lines 1078-1124 cover one pending automatic tick followed by unmount. They do not test a queued mutation, and they do not enter game over in that scenario. The separate game-over test establishes no further automatic dispatch after a terminal response, but not suppression of an action already queued behind the response that ends the game.

Use the existing targeted pending/queued tests to prove both cases: queue a mutation behind an in-flight operation; for game over, resolve that operation to terminal state and assert no queued dispatch; for unmount, unmount before settlement, settle, and assert unchanged exposed snapshot and no queued/timer dispatch. Do not claim these two precise scenarios are covered by a test that only calls unmount and checks null.

## What can be reported now

The production timer ownership correction is present, and the crucial A/B timer race, creation-body entry barriers, old in-flight queue independence, and exact 500/450/100 boundary assertions were added before the network failure. The complete GET and disposal/queued-work assertions are not yet finished. Final pass counts, coverage, build, audit, and Sonar results must come from coordinated execution after retry 13 closes; session 12's nonzero exit and partially written tests cannot be reported as a successful QA3 completion.
