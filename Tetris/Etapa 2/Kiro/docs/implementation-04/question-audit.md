# Auditoría de aclaraciones de Kiro

Kiro native assistant operationType=Say only; Reasoning, quoted tool results, requirements questions and automatic tool-approval prompts excluded from actual question counts. Candidate regex is only a review aid; no inferred zero from headless mode. Counts require manual message-ID adjudication.

## 01-specify

Mensajes Say: 6; aclaraciones bloqueantes: 0.

## 02-specify-student

Mensajes Say: 14; aclaraciones bloqueantes: 0.

## 03-native-spec-review

Mensajes Say: 19; aclaraciones bloqueantes: 0.

## 04-implement

Mensajes Say: 105; aclaraciones bloqueantes: desconocido; revisión manual pendiente.

- Candidato `6508c1ac-a626-402e-a30f-c4c1378f21f5-say` (2026-10-22T01:02:49.263Z): Two issues to address:

1. **StrictMode double-mount in tests**: `render(<Probe />)` isn't wrapped in StrictMode for most tests, but the first failure shows the tick fired during the 299ms window — the hook's `restart` on mount likely scheduled with interval 500 by default, but the state's interval is 300. The problem: `intervalRef` starts at 500, and `scheduleTick` reads `intervalRef.current` at schedule time. After `restart` applies state (interval 300), `applyIfCurrent` sets `intervalRef.current = 300` before `scheduleTick`. That should be fine... but the test showed tick was called within 299ms, meaning it scheduled at a shorter interval, OR two overlapping schedulers ran.

Actually the real culprit: `setTimeout`/infinite loop — `vi.advanceTimersByTimeAsync` combined with self-rescheduling ticks creates a loop because each resolved tick schedules another. When I `advanceTimersByTimeAsync(5000)` with a 300ms self-rescheduling tick that resolves synchronously via mock, it reschedules infinitely within the advance window. That's the "Aborting after 10000 timers" error.

The FIFO/stale tests likely fail for the same infinite-tick reason polluting timers. Let me fix the tests to control the tick mock so it doesn't infinitely reschedule, and fix the first test's expectation. The cleaner approach: make `tickGame` return a `game_over` or a controlled deferred so auto-ticks stop, and avoid `runAllTimersAsync` where self-rescheduling loops.

But first — is there a real bug in `useGame`? The infinite rescheduling is expected behavior (gravity keeps ticking while playing). The tests must account for it. Let me also double-check the first test: at mount, `restart` runs, awaits `createGame` → applies state (interval 300), schedules tick at 300ms. Advancing 299 → no tick. That should pass. The failure "got 1 call" within 299 suggests the initial `intervalRef` default 500 scenario isn't it. 

Possibly the StrictMode-free render still had a prior test's timers leaking. More likely: `vi.waitFor` with fake timers advanced real time. Let me rewrite the useGame tests to be robust: use deferred/controlled ticks and avoid `runAllTimersAsync` on self-rescheduling loops. Let me rewrite that test file.

- Candidato `b6140ade-6a42-4ea3-95ad-7094fcda0075-say` (2026-10-22T01:10:34.375Z): These are the exact 6 new violations. All are code-quality findings on code I added (not legacy). They're genuine and fixable without weakening anything:

1. **games.py:61** `python:S8409` — redundant `response_model` on the new `hold_game` route (duplicates return type annotation). Note: the other `response_model` usages on lines 27/35/43/52 are on legacy routes (not flagged as new). Only line 61 (my new hold route) is new. But removing `response_model` from only the new route creates inconsistency with the legacy routes. Hmm — I should check: these are MINOR smells. The cleanest fix for the new route is to remove its redundant `response_model` since FastAPI infers from the return annotation. But that would make the hold route inconsistent with siblings. Actually, since all sibling routes also have it (flagged on legacy but not "new"), consistency argues for keeping it. However the gate counts the new one. I'll remove `response_model` from the new hold route only — FastAPI still produces the correct response model from the `-> GameStateOut` annotation, so behavior is preserved.

Wait — but the legacy routes keep `response_model`, creating an inconsistency. Let me reconsider: the rule S8409 fires because `response_model=GameStateOut` duplicates `-> GameStateOut`. The most defensible, consistent fix is to remove the redundant `response_model` from the new route (the only new-code occurrence). Behavior is identical.

2. **schemas.py:43 and :50** `python:S8396` CRITICAL — optional fields need explicit default. These are `active_piece: Optional[ActivePieceOut]` (line 43, legacy-ish but in rewritten file) and `hold_piece: Optional[PieceType]` (line 50). Only :50 is flagged as new (the new field). Fix: add `= None` default. Wait, the new-code list shows only `:50`. Let me give `hold_piece` an explicit `= None` default (and active_piece too since it's in my rewritten file — but only :50 counts). Adding defaults is safe.

3. **test_scoring.py:57** `python:S5976` — group similar tests into parameterized. Fix: parameterize.

4. **test_stage2_api.py:44** `python:S3415` — unify assertion argument order (expected vs actual). Fix: make consistent.

5. **App.tsx:41** `typescript:S6582` — prefer optional chaining. Fix: use `?.`.

6. **Preview.tsx:37** `typescript:S6759` — mark props read-only. Fix: `Readonly<PreviewProps>`.

These are legitimate quality findings. Since these are implementation-level code-quality fixes (not behavioral defects in the spec), the spec doesn't need revision — the spec describes behavior, and these are stylistic/safety refinements that don't change behavior or acceptance criteria. I'll fix the code directly. Let me address all 6.

First, the backend `games.py` — remove redundant `response_model` from the new hold route. Let me check line 41's App.tsx and line 16 context too.

- Candidato `2a6ac82c-a940-4848-a0f4-0c8a6c4e2365-say` (2026-10-22T01:10:39.614Z): The S6582 flags at App.tsx:16 and :41 relate to `state && state.status`-type expressions where optional chaining (`state?.status`) is preferred. Line 16 is `if (!state || state.status !== "playing")` and line 41 is `!state || state.status !== "playing"` (the holdDisabled). These can't use optional chaining directly in the `!state ||` form, but Sonar suggests `state?.status !== "playing"` which covers the null case. Let me rewrite both to use optional chaining.

Let me apply all 6 fixes now.

- Candidato `b4203362-9cc2-48a0-ae61-1cbdf3aaa0d8-say` (2026-10-22T01:10:58.656Z): Note Board.tsx:36 (S6759) is flagged in the open-issues list but was NOT in the 6 new-code issues — only Preview.tsx:37 is new. But fixing Board.tsx too is harmless and consistent (it was in my scope? Board.tsx is a legacy Stage 1 file I didn't change). Board.tsx was not modified by me, so S6759 there is a pre-existing/legacy smell — fixing it is out of my change scope and not required for the gate. I'll fix only the new-code one (Preview.tsx) to avoid touching legacy files unnecessarily. Actually, both Board.tsx and Preview.tsx use `{ state }: BoardProps` destructuring; Board is legacy. I'll leave Board.tsx unchanged (not a new violation) and fix Preview.

- Candidato `1cfeb1c7-5359-4d1f-bca7-57a7ff997c01-say` (2026-10-22T01:11:49.921Z): The `test_repeated_get_does_not_change_state` uses `assert again == first` and `assert first == ...`? Let me check it. S3415 flags that the file mixes orders. Line 44 was flagged as the location. The `repeated_get` test:

```python
first = client.get(...).json()
again = client.get(...).json()
assert again == first
```
That's `actual == expected` (again vs first) — consistent. 

The real inconsistency is likely the `in` assertions (`assert data["next_piece"] in [...]`) are fine. Let me just find the single expected-first assertion. Let me grep for `is not None` reversed or any `== data`.

- Candidato `13692ab2-ec02-40c3-8a42-7994d7f983d7-say` (2026-10-22T01:15:06.830Z): All 100% consistent (actual-first, expected-second). The S3415 rule in SonarQube 26.x for Python likely has a specific heuristic I can't reverse-engineer perfectly. The dominant convention here is clearly "actual == expected". 

One thing stands out: lines 92 (`assert again == first`) and 116 (`assert second == first`) — here `first` is the *baseline snapshot* (expected) on the right, while `again`/`second` are the fresh values (actual) on the left. That's consistent with actual-first.

But line 149-151: `assert game.active.type == held_before` — here `held_before` (the captured expected) is on the right. Consistent.

Given I cannot determine Sonar's exact trigger by inspection, let me try the one concrete thing the message says: "both actual first and expected first conventions are used." Perhaps Sonar classifies `assert game.hold_type == "O"` (literal right = expected-first/actual-first) differently from `assert set(data.keys()) == {...}`. 

The cleanest guaranteed fix: split this into a form Sonar accepts, OR — since S3415 is about *consistency* — the issue might actually be elsewhere and line 44 is just the "representative" location. Let me check: does test_api.py (legacy) also have S3415? Looking at open issues earlier: test_api.py:26 had S9073 (composite assertion), not S3415. 

Let me try a targeted approach: rewrite the two "variable == variable" assertions (92, 116) which are the most ambiguous (neither side is a literal) by comparing against the captured value explicitly on the right — they already are. 

I'll instead consult the actual Sonar rule to understand the trigger precisely.
