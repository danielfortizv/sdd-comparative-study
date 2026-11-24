# Stage 4 / Spec Kit — Copilot preparation packet

The authoritative common seed in this packet was extracted verbatim from the `SEED-4` appendix paragraph of `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx`. Its original standalone master `SEED-4(1).md` was **not** available among the supplied local files; compare it if present in the repository before use.

**Extracted seed SHA-256 (UTF-8 file with final newline):** `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`

This packet contains:

1. `01_COPILOT_PROMPT_PREPARATION.md` — paste verbatim to GitHub Copilot Chat Agent to perform **preparation only**.
2. `SEED-4.md` — common Stage 4 Option A seed, unchanged from the appendix paragraph except for a normal final file newline; do not append tool instructions inside it.
3. `02_D01_D14_REFERENCE.md` — English **summaries** of post-seed business decisions; require full original approval records before declaring equivalence.
4. `03_BASELINE_METRICS_CHECKLIST.md` — researcher review gates, baseline safety requirements, and D1–D5 evidence contract.

## Suggested local placement

Inside the repository, place the packet under `Shift-Bank/Etapa 4/_preparacion_investigador/` or another researcher-owned untracked workspace (not a native Spec Kit specs folder). Open the **repo root** in VS Code to let Copilot inspect E3, E4 and shared guides. Only after review should the agent create `Shift-Bank/Etapa 4/Spec Kit/` by a safe copy of the finished E3 Spec Kit implementation.

Do not record preparation-only files as formal SDD specifications or include them in the D3 specification-file counts. Respect research rules for excluding auxiliary docs from official Git history.

## Critical conflict to resolve before authoring specifications

Your completed Spec Kit E3 source references accounts and thresholds in **COP**. The E4 historical D-02/D-07 decision reference assumes **USD-based** inherited balances/limits with USD, EUR and GBP accounts. This is not an instruction to silently migrate or convert. A researcher-approved prospective reconciliation is mandatory.

The GitHub Copilot preparer is **not** the measured Stage 4 agent unless explicitly designated. Record any setup interaction separately from SDD experimentation and do not attribute its work to Gemini CLI or Codex.
