# External queued-manual timer defects after06

Researcher-authored, real production hook/API, fake timers and deferred transport. Stable hook SHA256B75EA8B864F8890B1531B71367EF9410ED138F6A15E5E75B6523A02903667479. No application/test/spec file or LCOV was modified. Independent run193206Z on October23 executed **2 tests,0 passed,2 failed**, actual Vitest exit1; wrapper exit0 only means reports were retained.

Fixtures were serialized by the real Kiro engine at DEFAULT_SEED20260929: canonical O at(18,3), bottom row filled except3/4,9 prior lines. Left is a genuinely blocked no-op; Down locks and clears one row, scores100 and returns level2/gravity450. The terminal variant adds one occupied top cell so the real post-clear queued-O spawn ends the game. Internal board cells use PieceType/None; the actual API snapshots use integer encoding. Source hashes and exact mechanism are in queue-timer-fixtures.json.

## R4 — queued completion leaves its predecessor's timer alive

Queue Left and Down before Left completes. Complete Left at t0; the hook schedules a500ms timer although Down is already waiting. Complete Down at t100 with the real level2/450 snapshot. scheduleTick sees the existing timeout and does not replace it. Advancing449ms after Down (t549) already sends a tick at old t500. The required new450ms period after fresh state would send the first tick at t550.

## R5 — queued terminal completion leaves a game-over tick

Same queue and t0/t100 completion sequence, with the terminal fixture. The first completion creates the timer; the second returns game_over and skips scheduling, but does not cancel the already-created timer. Advancing1000ms dispatches one tick after terminal state. Expected0.

Reports: queued-timer-runs/20261023T193206664724Z/{run.json,vitest.json,stdout.log,stderr.log}. Fresh native JSON, source/config/fixture and LCOV hashes stable. Earlier sandbox attempt193142Z executed0 tests due EPERM on Vite's temporary cache rename; it is an infrastructure error, not a product test failure. Initial researcher fixture preparation errors are also retained separately and excluded from Kiro generation metrics.

Suggested correction scope: reconcile/cancel the exact pending timeout on each current-generation manual result as well as dispatch, including terminal results and interval changes, without clearing an automatic tick guard owned by a queued/in-flight tick. The actual design/fix and generated regression tests belong to Kiro and require native spec revision first. Preserve R1–R3, FIFO, generation isolation, coalescing and StrictMode behavior.
