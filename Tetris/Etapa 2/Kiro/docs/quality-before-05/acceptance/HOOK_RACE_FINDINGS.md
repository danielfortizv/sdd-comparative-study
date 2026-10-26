# External researcher hook-race reproduction — provisional generation 04

These are researcher-authored acceptance checks outside the application's source and generated test directories. They import the real `frontend/src/useGame.ts` and `api.ts`, use the installed Vitest 3.2.7 / Testing Library 16.1.0, and replace only transport `fetch` with independently deferred headers and response bodies. Fake timers force the exact automatic-tick boundary. No application, generated test, specification or application config was edited.

Latest controlled execution: **3 tests executed, 0 passed, 3 failed**, Vitest exit **1**. These failures demonstrate the candidate defects; they are not three successful application acceptance cases. The Python researcher wrapper returns normally after retaining the nonzero Vitest result in `hook-races-run.json`.

## R1 — Restart leaves old identity usable in the new generation

1. Fully load game A.
2. Start restart/create B and prove its fetch remains pending.
3. Trigger Hold before B arrives. Production sends `/api/games/A/hold`.
4. Resolve A Hold headers and prove its `json()` was called, keeping its body pending.
5. Resolve creation B and assert visible game is B.
6. Resolve the old A Hold body, with a valid I→O empty-slot Hold snapshot.

Expected: visible ID stays B. Observed: visible ID becomes **A**. Restart increments the generation but retains the old `idRef` until create completes; input during creation captures the new generation with the old ID.

## R2 — Automatic tick bypasses pending manual work and reverses state

1. Load A with an I piece at row 0.
2. Trigger soft drop, resolve its headers, and prove `json()` is pending.
3. Advance exactly 500 ms. Production sends a concurrent automatic tick.
4. Resolve the tick snapshot at row 2.
5. Resolve the older manual snapshot at row 1.

Expected: the newer visible state is not reversed. Observed: visible row changes **2→1**. Automatic ticks do not share the manual FIFO, and manual input cancels its timeout only after receiving its result.

## R3 — Manual completion clears the guard of an unresolved tick

1. Load A; send a left movement and keep its JSON pending.
2. Advance 500 ms; resolve the automatic tick headers and prove its JSON remains pending.
3. Resolve the manual left movement with a valid column-2 snapshot.
4. Advance one more 500 ms without resolving the first tick body.

Expected: at most one queued/in-flight automatic tick. Observed: **two unresolved automatic tick requests**. The manual completion resets `tickBusyRef` even though an automatic request still owns that guard.

## Provenance and revalidation

Stable production hashes before and after the latest execution:

- `useGame.ts`: `67F340FC713072C81F3A744292D708FA3C290F01EE489D6E3D22EF774184269B`.
- `api.ts`: `4321FAF77B834628E68BD07A7FE471B811B278E005FD0208367BE6966DBA533D`.

`hook-races-run.json` retains exact argv/cwd/timestamps, installed versions, source/config/harness hashes and LCOV hashes before/after. LCOV was unchanged; coverage is disabled in the external config and no coverage argument is passed. `hook-races-observations.json` records actual visible state and transport barriers. `hook-races-vitest.json` retains native assertion failures. Stdout/stderr are preserved separately. Previous completed harness runs are archived under `previous-runs/`; the initial zero-test discovery attempt is explicitly retained as an infrastructure error and is not included in the three executed cases.

Rerun after generation 04 closes using `shared/run-kiro-race-harness.py`. If Kiro changes the source hashes, this result applies only to the earlier candidate and must be revalidated. Any repair must first revise the native Kiro specification and then be implemented by Kiro; this harness does not patch generated code. These researcher checks are separate from counts of Kiro-generated frontend tests.
