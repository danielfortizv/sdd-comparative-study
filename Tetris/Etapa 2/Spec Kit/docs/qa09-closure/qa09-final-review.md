# Read-only review after native correction 09

Review snapshot began at 2026-10-20 20:12:25 America/Bogota. Correction 09 metadata records completion at `2026-10-20T08:55:23.6575215-05:00`, exit 0. This review inspected current source, test bodies, original Stage 1 artifacts, and the retained generation-08 snapshot. No application, generated test, or native specification was edited. No application server, test suite, scanner, or Gemini session was launched by this reviewer. Root's independent execution results must be attached separately; this report does not infer passes from the generator's completion message.

## Remaining production defects

### R1 — A stale creation body can replace the newest game

`frontend/src/hooks/useGame.ts:47-59` checks the restart generation after `fetch` returns at line 48, then awaits `res.json()` at line 53 and applies `activeGenerationRef`, sequence resets, and `setGame` without another ownership check at lines 56-59.

Concrete sequence: start A's fetch returns HTTP headers while generation A is current; its body promise remains pending. Start B then completes its fetch and body and becomes the current displayed game. A's older body subsequently resolves; A unconditionally replaces B and sets the active generation back to A. The catch/finally guards at lines 61/65 do not prevent the success write. Subsequent mutations are blocked because active and requested generations now differ.

Required correction: recheck generation ownership after every asynchronous boundary that precedes state/ref writes, particularly after JSON parsing. Add a deferred-body test, not only deferred-fetch tests. The existing overlapping-start test at `frontend/tests/useGame.test.ts:279-325` defers the fetch response and gives `json()` an immediately resolved promise, so it misses this window.

### R2 — An old pending mutation blocks all gameplay after a successful restart

`frontend/src/hooks/useGame.ts:23` creates one promise queue for the hook lifetime. Mutations chain from that queue at line 86 and replace its tail at line 114. `startGame` does not detach or cancel the old generation's queue. Creating a new session occurs independently of the queue.

Concrete sequence: a move in game A remains pending; restart creates game B successfully. B's moves, ticks, and Hold all join the queue behind A's pending fetch/body. B's UI appears ready but cannot play until A finishes, possibly indefinitely. Generation checks suppress stale writes only after the old operation settles; they do not release the new generation's queue.

Required correction: give each generation its own queue ownership, or abort/detach old pending work while preserving serialization within the new generation. Add a test that leaves A's operation unresolved, restarts to B, and proves a B mutation reaches fetch and updates B before A settles; then settle A and verify B remains unchanged. Existing `useGame.test.ts:219-277` resolves the old move after restart and checks only that it cannot overwrite B; it does not test B's ability to play while A stays pending.

## Remaining verification gaps

- **Canonical preview tests are absent.** Current `App.tsx:8-14` now matches all seven backend template shapes, including T. A read-only AST/literal extraction and normalized coordinate comparison found I/O/T/S/Z/J/L all equal to `backend/app/services/game_engine.py:10-16`. However, `frontend/tests/App.test.tsx:36-85` asserts statistics, panel headings, button state, and click callback only; no test checks occupied preview coordinates, orientation, or all seven types. `specs/002-extend-tetris-stage2/tasks.md:167` marks T041 complete despite this missing assertion.
- **Uppercase C can fail without failing its test.** `frontend/tests/useGame.test.ts:125-136` directly mutates returned game state and then uses `toHaveBeenCalledWith` for the same URL/options already asserted after lowercase c at line 121. There is no call-count delta or other new state assertion proving the uppercase event dispatched a second Hold. Source handlers at `useGame.ts:135-141` do recognize both cases; this is an evidence weakness, not an observed uppercase defect.
- **GET-specific draw/deep-snapshot checks do not invoke GET.** `backend/tests/unit/test_qa_iteration1.py:57-60` reads the session dictionary once. Lines 90-93 compare `session.model_dump()` with the same stored object's dump. These prove nothing about GET endpoint behavior. The external unchanged API checker can supply whole-response immutability evidence, but the generated test must not be described as a GET-route test. Existing integration GET at `test_api_us1.py:74-85` still checks only preview equality.
- **Timer checks do not establish cancellation or delayed-tick behavior.** `frontend/tests/useGame.test.ts:456-510` exercises responses carrying 450 and 100 ms, but it does not check absence of early/duplicate requests, cancellation of the previous interval, or delayed tick serialization. Its final `toHaveBeenCalledWith('/tick', ...)` is already satisfied by earlier ticks and does not prove a new request occurred at 100 ms. Generic move serialization is meaningfully tested at lines 139-217; it should not be reported as delayed gravity/cancellation coverage.
- **No-game source guard is fixed but not directly asserted.** `useGame.ts:72-75` now returns without fetch when no game exists. The additional regression noted after session 08 is corrected by inspection; no dedicated before-start no-op assertion is present in the current hook tests.

## Original QA findings after correction 09

| Finding | Source/test evidence now present | Honest status from this read-only review |
| --- | --- | --- |
| QA-01 production scoring/level/gravity | `backend/tests/unit/test_game_engine_us1.py:128-306` invokes real `tick_session` for zero/one/two rows, boundary transitions and gravity floor; three/four mock only the clear result while invoking real scoring. | Copied-formula issue corrected; execution pending root verification. Three/four remain isolated domain evidence. |
| QA-02 exact random draws | `test_qa_iteration1.py:12-84` patches actual `secrets.choice`, checks creation 2 / lock 1 / empty Hold 1 / occupied swap 0 / rejected Hold 0 / game-over actions 0. | Meaningful production draw assertions added; GET claim remains unsupported by that test body. |
| QA-03 full snapshots | `test_qa_iteration1.py:95-124` compares complete serialized state for rejected Hold and all left/right/down/tick/Hold actions after game over. | Rejection/game-over assertions corrected; route GET evidence still needs independent API output or real route assertions. |
| QA-04 dirty restart | `test_qa_iteration1.py:126-161` dirties all counters/Hold/board, invokes real `create_session`, and checks defaults, full empty board and valid pieces. | Domain reset evidence corrected; root must attach executed results and API restart result. |
| QA-05 bent I fixture | Unit scoring uses canonical horizontal I at `test_game_engine_us1.py:157-162`; integration uses horizontal I plus separate survivor blocks at `test_api_us2.py:13-37`. | Fixture corrected; inherited line-shift assertions preserved. |
| QA-06 restart isolation/serialization | Generation checks and generic serialization are present; pending restart commands return without dispatch. | Partially corrected; R1 and R2 remain actual defects. |
| QA-07 canonical previews/UI evidence | T and all seven source shapes match backend; App tests now cover HUD, empty Hold, click, disabled states. | Source correction present; seven-shape coordinate assertions missing, uppercase test weak. |
| QA-08 preview CSS | `frontend/src/index.css:340-356` defines flex grid/rows. | Source fixed in session 08; browser verification belongs to root. |
| QA-09 timing/race tests | New tests cover generic move serialization, stale pre-restart response, reversed fetch completions, stale creation HTTP failure/loading, pending restart action suppression, rejected mutation recovery, interval changes. | Better evidence, but R1/R2 and exact timer assertions above remain. |

No new production backend rule defect was identified by source inspection. Correct score table, pre-lock multiplier, cumulative lines, level formula, 100-ms floor, draw sites, canonical Hold spawns, and post-game-over early returns remain in `backend/app/services/game_engine.py`.

## Stage 1 test preservation

A read-only AST comparison against all original `Etapa 1/Spec Kit/backend/tests` functions found **18 of 18 inherited tests retained, 68 of 68 original assertions retained**. Seventeen functions are AST-identical. The only changed function is `backend/tests/integration/test_api_us2.py::test_api_line_clear_integration`, which corrects the invalid shape fixture while preserving its five assertions, including response status and four board-cell checks. The two direct `clear_lines_in_board` regression tests remain in US2 with eight assertions. There is no evidence of inherited backend coverage being deleted.

## Provenance and limits of validate_engine.py

The root-level `validate_engine.py` is **inherited unchanged from Stage 1**, not a new Stage 2 validation tool. Both current and original files have SHA-256:

`21B0CB524A77062668817BE665413E83AEBD5E3A3B7EE37E80E6A8CD18B5888C`

The original Stage 1 quickstart describes this script at `specs/001-build-tetris-core/quickstart.md:69-139`. Current script behavior:

- Lines 7-15 assert create HTTP 201 and read/print some fields; they do not assert Stage 2 defaults.
- Lines 17-27 assert left/right HTTP 200; they do not assert piece movement or collision behavior.
- Lines 29-43 print a two-row fixture description, but do not install that fixture. They merely tick an ordinary newly created game once and print two rows. They never assert rows cleared, score, lines, level, or gravity.
- Lines 45-48 perform no request, state mutation, or assertion for game over; they only print success text.
- Lines 58-61 print an all-scenarios-passed message when no earlier exception occurred, and catch failures without re-raising or setting a nonzero exit code.

Consequently this inherited script can support only a narrow HTTP smoke observation for create/left/right/tick, if executed and logged. It cannot establish two-row clearing, game over, Stage 2 behavior, or a passing end-to-end acceptance rate. Preserve its provenance and exclude its printed success claims from the final acceptance evidence. The unchanged shared external checker and executed meaningful production/domain/browser checks are the appropriate sources for that report.

## Required next action

Root should preserve the final-09 snapshot and executed verification results, revise native requirements/tasks for R1/R2 and the remaining targeted assertion gaps, then have Gemini perform any application/test correction. This reviewer made only this researcher report; no generated source was patched.
