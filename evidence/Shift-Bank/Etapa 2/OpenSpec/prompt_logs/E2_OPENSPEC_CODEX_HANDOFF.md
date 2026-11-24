# Shift Bank Etapa 2 — Codex Handoff

## First-session working directory

```text
C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\OpenSpec
```

The destination is an independent copy of Stage 1 OpenSpec. It has no symlinks, junctions, or same-file identities with the source. Its Python virtual environment and frontend dependencies are local to the destination.

## Handoff state

- OpenSpec CLI 1.9.0 is initialized in this directory.
- The inherited specs `bank-accounts`, `mfa`, `transaction-history`, and `transfers` are accessible.
- The archived Stage 1 change `2026-09-29-stage1-requirements` is preserved.
- Codex integration files are available under `.agents/skills`; six OpenSpec skills and the `codex` target marker are present.
- Codex CLI 0.168.0 launches from this directory.
- No active OpenSpec change exists.
- No Stage 2 business specifications or feature implementation have been created.
- The inherited `.gemini` configuration is retained from the source snapshot; do not interpret it as the experiment's selected agent.

## Methodological note

The Stage 2 experiment is to use OpenSpec with **OpenAI Codex**, not the Gemini CLI described by the original research protocol. Record this as a methodological deviation in the final comparison.

No Codex session was opened during preparation. CLI account authentication and live skill discovery remain untested. The next session should start in the directory above; this handoff does not authorize beginning a Stage 2 proposal or implementation before the experiment is ready.
