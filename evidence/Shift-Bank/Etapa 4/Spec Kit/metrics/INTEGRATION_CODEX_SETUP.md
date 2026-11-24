# E4 Spec Kit — Native Codex Integration Record

**Date:** 2026-11-16  
**Scope:** Native Spec Kit integration setup only. Gate A remains pending. No specifications or application behavior were authored or changed.

## Before

- `specify integration status`: OK; default `gemini`; installed `gemini`; multi-install safe; modified managed files 0; missing managed files 0; invalid manifest paths 0; unchecked manifests 0.
- `specify integration list`: Codex CLI (`codex`) is available as a built-in integration and marked multi-install safe.
- `.specify/integration.json`: Gemini only, default Gemini; no `.agents/` or `.codex/` project directory.
- `specify integration info codex`: identified as built-in. The CLI attempted to fetch default/community catalogs and received Windows socket permission errors; the local built-in Codex entry remained available.

## Actions and outcomes

1. `specify integration install codex` — succeeded without `--force`. The CLI reported 12 shared infrastructure paths already existed and were not updated. Gemini remained the default after installation.
2. `specify integration use codex` — succeeded without `--force`; Codex became default and Gemini remained installed.
3. Post-change `specify integration status` — OK; default `codex`; installed `gemini, codex`; multi-install safe; modified managed files 0; missing managed files 0; invalid manifest paths 0; unchecked manifests 0; shared templates target alignment `codex`.

## Codex skills and invocation

The Codex manifest installs project-local skills in `.agents/skills/`. The Codex integration setting uses PowerShell (`ps`) and hyphen invocation separator (`-`); skill names therefore use `$speckit-<name>` invocation (for example, `$speckit-clarify` and `$speckit-specify`). Codex CLI skills are file-based; `codex skills --help` returned the general CLI help rather than a skills-management subcommand. No skill was invoked.

Available skills: `speckit-analyze`, `speckit-checklist`, `speckit-clarify`, `speckit-constitution`, `speckit-converge`, `speckit-implement`, `speckit-plan`, `speckit-specify`, `speckit-tasks`, `speckit-taskstoissues`.

## Change inventory and integrity

**Added (11):**

- `.specify/integrations/codex.manifest.json`
- `.agents/skills/speckit-analyze/SKILL.md`
- `.agents/skills/speckit-checklist/SKILL.md`
- `.agents/skills/speckit-clarify/SKILL.md`
- `.agents/skills/speckit-constitution/SKILL.md`
- `.agents/skills/speckit-converge/SKILL.md`
- `.agents/skills/speckit-implement/SKILL.md`
- `.agents/skills/speckit-plan/SKILL.md`
- `.agents/skills/speckit-specify/SKILL.md`
- `.agents/skills/speckit-tasks/SKILL.md`
- `.agents/skills/speckit-taskstoissues/SKILL.md`

**Modified (9), all native Spec Kit integration/configuration:**

- `.specify/init-options.json`
- `.specify/integration.json`
- `.specify/integrations/speckit.manifest.json`
- `.specify/scripts/powershell/check-prerequisites.ps1`
- `.specify/scripts/powershell/common.ps1`
- `.specify/scripts/powershell/setup-tasks.ps1`
- `.specify/templates/checklist-template.md`
- `.specify/templates/plan-template.md`
- `.specify/templates/tasks-template.md`

These changes set Codex/`ai_skills: true`, update managed hashes, and adapt command references to `$speckit-*`. **Deleted:** none.

E4-SK-01 baseline manifest: 105 entries; 96 remain byte-for-byte unchanged; the other 9 are exactly the integration/configuration paths listed above. No baseline paths are missing. No `004-*` feature directory exists. The constitution, Stage 1–3 specs, app code, tests, deployment files, and all 10 original `.gemini/commands/*.toml` files remain unchanged. Codex and Gemini manifest hashes both validate; native integration status reports no modified/missing managed files. E3 and other SDD tools were not modified.

## Environment and limitations

- Spec Kit CLI and integration version: `1.0.6`.
- Codex CLI: `codex-cli 0.168.0` (`codex.cmd --version`).
- Effective model: **N/D**; no measured Codex session/model call was started or inspected.
- No specification generation, tests, application commands, migrations, Docker, load tests, or SonarQube were run.
- Gate A remains pending. Integration activation is not Gate A approval.

## Commands observed

`specify integration --help`; `specify integration status`; `specify integration list`; `specify integration info codex`; `specify integration install --help`; `specify integration use --help`; `specify integration install codex`; `specify integration use codex`; post-change `specify integration status`; `codex.cmd --version`; `codex.cmd skills --help`; manifest/hash comparisons; file inventory.
