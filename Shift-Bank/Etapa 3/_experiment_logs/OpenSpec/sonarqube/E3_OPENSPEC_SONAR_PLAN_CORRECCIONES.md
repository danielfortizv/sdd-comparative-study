# Focused correction plan and disposition

Baseline: task `ea27677b-df48-4d54-9b89-25ac686bce41`, analysis `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`. The complete 52-item extraction was reviewed. No Sonar vulnerability was reported; hotspot review remains unavailable because the endpoint returned HTTP 403.

## Selected for the single correction round

1. **Five production Bugs — `typescript:S9011`, MAJOR, `frontend/src/App.tsx`:** keys `d48cd859-5ad5-43c6-9d67-27e349eeca8f`, `1825d55d-c181-4736-b480-8d643469dfea`, `1ca82a68-f8c8-4707-ad9c-198bf1feddbc`, `d1809aca-8c80-4272-ad14-3bfd526a68a1`, `e8ac08b1-6992-40c7-92e2-4af5cba95154`. Buttons inside forms relied on HTML's implicit submit behavior; controls outside forms lacked explicit button behavior. Set intended `submit` or `button` types. Add an AST-based frontend regression asserting every button has an explicit supported type.
2. **Repeated banking literals — `python:S1192`, CRITICAL Code Smell:** keys `1e6268f0-fa9d-4724-a146-38528885f35f`, `de67909b-6e2c-4026-99ae-2129fdb46391`, `3f66e3e4-2f5d-46c6-8bd9-cd871c3f211a`, `ec299677-1768-4ab4-9de1-622a0a640f63`, `e6591e31-265b-4f6f-a7d4-aa4c6f3116ec`, `b265314b-a9dc-491d-90fc-252c295cd272`, `997dc35b-03a8-4800-8fd8-6c2221874067`. Name the established messages, SQL statement, and seed account labels as constants; preserve messages and SQL effects.
3. **Unused ACH helper arguments — `python:S1172`, MAJOR:** keys `7d239fa9-da85-4aab-9192-ba9391a547de` and `fbfce9c8-4f43-483e-a694-085f45d7fb7f`. Remove only the unused `rec` and `bid` parameters from `_accept_ach` and its two calls.
4. **Redundant caught subclasses — `python:S5713`, MINOR:** keys `46209f08-4ad1-40b7-9117-405c1dde34a0`, `c0bc0620-2bec-4dac-bb42-e847e66ca967`, `1d0e7a93-9964-4b5e-88ea-d46eacb5bb07`. Remove subclass members already covered by `ValueError` from exception tuples in audit and encryption parsing; retain fail-closed handling.
5. **OpenAPI error documentation — `python:S8415`, MAJOR:** keys `2575f3b2-6666-4882-8b43-79e2a495e7ee` and `68af842a-d22c-4ba8-83f4-0ecbbc469994`. Document existing 401/404 responses, with a regression against generated OpenAPI. Runtime responses remain unchanged.

## Left unchanged

- Cognitive-complexity findings in audit verification, encryption, banking operations, and the main React component: extracting security- and money-sensitive control flow would have a wider regression surface than this focused pass. Existing integrity, encryption, banking, and lifecycle tests cover these flows; defer decomposition to a separately scoped review.
- CSS contrast findings: require visual color-pair verification across component states; no unverified style change was made.
- Nested ternaries and suggested semantic `<output>`/`<dialog>` conversions: behavior/accessibility semantics need focused UI review.
- `python:S6353` digit-class suggestions: replacing `[0-9]` with `\d` changes accepted Unicode digit behavior in Python, so preserving the inherited ASCII validation contract takes priority.
- Test-only assertion-style and exception-test smells: they do not affect production behavior and broad test cleanup was outside the focused reliability batch.
- Empty-object API fallback smell: behavior is safe and unchanged by this pass.

No finding conflicted with an approved functional requirement. No rule was suppressed, no source was excluded, and no Quality Gate threshold was altered.
