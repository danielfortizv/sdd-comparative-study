# Acceptance evidence mapping — researcher review

Prepared after native session `08-implement`, 2026-10-20 08:00 America/Bogota, while correction 09 was being prepared. This is an evidence plan, not a final pass report. All final results must be rechecked against the completed correction. The reviewer did not edit application code, generated tests, native specifications, the frozen seed, or the shared acceptance catalog/checker, and did not run tests or an app server for this review.

## Evidence categories and reporting rules

- Keep the 20 catalog IDs and numeric expected rules unchanged.
- The unchanged external `../shared/acceptance/check_api.py` emits seven result records, with `S2-03/S2-12` combined. These records touch eight distinct catalog IDs: 01, 02, 03, 10, 11, 12, 15, and 16. A seven-record pass is not a 20-case pass.
- Generated unit/integration tests are tool evidence. Independent external API results, researcher domain fixtures, and browser observations are separate evidence sources; do not relabel one as another.
- Static source inspection establishes where behavior is implemented. It does not establish an executed acceptance pass.
- Record `pass`, `fail`, `blocked`, or `not run` for every catalog ID in the final matrix, with exact test/log/image references and the fixture mechanism.
- Keep domain-only results separate from a user-visible acceptance rate. State the denominator and exclusions explicitly. A catalog completion rate can include domain validation if labeled, but must not be presented as observed manual gameplay.
- SonarQube supplies code quality evidence, not an acceptance or scalability score.

## Reachability of three- and four-row clears

Spec Kit's canonical backend templates in `backend/app/services/game_engine.py:10-16` all span at most two rows. The I piece is horizontal. Normal falling and left/right/soft-drop translate these templates; Hold reintroduces a canonical template. There is no rotation.

After each normal lock, `clear_lines_in_board` removes all complete rows (`game_engine.py:89-102`, called at `:132`). Therefore a settled board reached by ordinary play contains no already complete row before the next lock. Because a locking piece touches at most two distinct rows, it can newly complete at most two rows. Both three- and four-row simultaneous clears are consequently unreachable in ordinary play for this implementation.

Preserve `S2-06` and `S2-07`, validating their 500/800 multipliers through an explicitly isolated domain fixture that invokes the real production scoring path. A controlled cleared-row result supplied to `tick_session`, a controlled board with intentionally pre-completed rows, or a production scoring function actually used by `tick_session` can establish the numeric rule. State which mechanism is used and that the fixture is not a reachable gameplay state. Do not introduce rotation, use a bent/vertical shape labeled I as gameplay evidence, or test a locally copied scoring formula. The catalog explicitly singles out four-row domain validation; this note extends the same honest reachability label to three rows without changing its ID or expected rule.

## Case-by-case mapping

Paths below identify the post-08 snapshot and should be refreshed after correction 09. `unit/us1`, `unit/us2`, and `unit/us3` abbreviate the corresponding `backend/tests/unit/test_game_engine_us*.py` files; `api/us1`, `api/us2`, and `api/us3` abbreviate `backend/tests/integration/test_api_us*.py`.

| ID | Production path / current test targets | Exact evidence required for final acceptance |
| --- | --- | --- |
| S2-01 | `create_session`; `api/us1::test_api_schema_response_keys` | External create response plus executed defaults assertions for every Stage 2 field, full 20x10 board, valid active and preview. Shared API checker covers the primary defaults. |
| S2-02 | GET endpoint returns stored state; `api/us1::test_api_immutable_get` | External whole-response equality before/after two reads; deterministic domain spy demonstrates zero random draws. Existing generated preview-only assertion is insufficient on its own. |
| S2-03 | `tick_session` lock, scoring, queue spawn; `unit/us1::test_tick_falling_and_lock`, `test_next_piece_queue_generation` | Shared combined `S2-03/S2-12` API record plus executed fixture proving counters remain unchanged, preview becomes active at canonical spawn, and exactly one new preview draw occurs. |
| S2-04 | `tick_session` actual scoring path; `unit/us1::test_pre_lock_level_scoring`; `api/us2::test_api_line_clear_integration` | A legal horizontal I or other canonical piece and compatible one-row gap; assert score delta `100 * prior_level`, line delta 1, subsequent level/interval, and cleared-board shape. Retire the bent piece labeled I. |
| S2-05 | `tick_session` actual scoring path | Controlled reachable two-row gap with canonical O, for example; assert score delta `300 * prior_level`, line delta 2, resulting level/interval and board. The existing `clear_lines_in_board` two-row test proves clearing but does not prove scoring. |
| S2-06 | `tick_session` production scoring or a production function used by it | Isolated domain fixture for three cleared rows; assert `500 * prior_level`, line delta 3 and derived state. Label unreachable ordinary gameplay under the fixed templates. |
| S2-07 | Same production scoring path | Isolated domain fixture for four cleared rows; assert `800 * prior_level`, line delta 4 and derived state. Report separately from user-visible acceptance, as required by the catalog. |
| S2-08 | `tick_session` score before level recomputation; `unit/us1::test_pre_lock_level_scoring` | Executed production fixture starting at lines 9/level 1, clearing one row: score delta 100, lines 10, level 2, interval 450. Checking a local `calc_level` function is not evidence. A multi-line crossing is useful additional boundary evidence if generated. |
| S2-09 | `tick_session` derived interval | Executed production fixtures at level 9 and above, including a lock at high line count; returned interval must equal 100 and never fall below it. A locally defined `calc_gravity` is not evidence. |
| S2-10 | `hold_session_piece` empty-slot branch; `unit/us2::test_hold_first_time`; `api/us2::test_api_hold_endpoint_success` | Shared API result for type transfer/cooldown/canonical spawn, plus deterministic draw-count proof of exactly one new preview. |
| S2-11 | `hold_session_piece` cooldown early return; `unit/us2::test_hold_immutable_actions`; `api/us2::test_api_hold_endpoint_rejected` | Shared API complete-state equality plus generated complete snapshot equality and zero draws; comparing only held/active types is insufficient. |
| S2-12 | `tick_session` resets availability, occupied Hold branch; `unit/us2::test_hold_reset_on_lock`, `test_hold_swap` | Shared combined lock/swap record, generated canonical origin/orientation assertions and exact zero draw count for the occupied swap. Preview equality alone could hide extra identical draws. |
| S2-13 | Hold spawn collision branch; `unit/us2::test_hold_obstructed_spawn` | Controlled settled obstruction at held piece's canonical spawn, executed actual Hold path; response/state status game_over and activePiece null. Record fixture and ensure no illegal active cells. |
| S2-14 | Early returns in tick/move/Hold; `unit/us3::test_game_over_ignores_moves_and_ticks`; `api/us3::test_api_game_over_ignores_operations` | Whole-state deep equality after each of tick, left/right/down move, and Hold; zero random draws. Include the Hold endpoint rather than only move/tick origin checks. |
| S2-15 | `create_session` invoked by restart/new-game POST; `api/us3::test_api_restart_creates_fresh_session` | Shared API defaults plus executed restart from dirty score/lines/level/interval/Hold/board. Verify every reset field, full empty board, fresh valid active/preview, and new session ID. Shared checker alone does not dirty all counters. |
| S2-16 | `backend/app/api/endpoints.py`; existing `api/us1`, Hold `api/us2` | Live or TestClient checks for all five successful endpoints with the agreed complete state shape; missing IDs yield 404. Shared checker only checks missing-ID GET/Hold, and exercises tick/create/get/Hold; it does not prove successful move or all missing-ID routes by itself. |
| S2-17 | App panels, PiecePreview, Hold button, keyboard listener; `frontend/src/App.tsx`, `frontend/src/hooks/useGame.ts` | Executed rendered UI assertions and browser screenshots/notes for score, lines, level, canonical seven previews, empty/nonempty Hold, button click, lowercase/uppercase C, disabled Hold, and game-over state. A build or hook-only test cannot prove rendering. |
| S2-18 | Hook gravity scheduling and request/session ownership | Executed fake-timer/deferred-promise tests for 500→450→100 intervals, old timer cancellation, action serialization, old responses/errors/finally around pending restart and overlapping creations; browser observations/screenshots and request timing notes. A screenshot by itself cannot prove stale-response rejection. |
| S2-19 | Backend board/move/collision/lock/clear/game-over; frontend Board/arrows/restart | Executed inherited regression suite plus browser observation of 10x20 board and existing controls. Retain evidence that soft drop grants no points and preserves existing lock behavior. Document any inherited fixture correction. |
| S2-20 | `frontend/package.json` build script and recorded lockfile | Recorded dependency install command/versions and successful `npm run build` log after final source changes. Tie the log to final artifact hash/snapshot. |

## Snapshot gaps awaiting correction and execution

The post-08 formula-copy tests do not establish S2-05/06/07/09. Snapshot equality, restart, request ownership, canonical T preview, and timer scenarios require correction under `docs/QA_FINDINGS.md`. Preview CSS is present after session 08 (`frontend/src/index.css:340-356`); browser output remains to be verified. None of the final acceptance statuses are assigned by this review note.
