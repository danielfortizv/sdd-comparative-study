# Evidence

This directory stores execution evidence, separated by type:

- [`screenshots/`](screenshots/) for visual evidence;
- [`logs/`](logs/) for tool, agent, test, and execution logs;
- [`metrics/`](metrics/) for measurements and structured metric records.

## Naming Convention

Use the following base convention:

`<tool>_<scenario>_<phase>_<description>`

Use lowercase, stable identifiers and add an experiment or run identifier when needed to prevent collisions. Examples of names are conventions only, not evidence: `openspec_greenfield_planning_context`, `speckit_brownfield_validation_tests`.

Record the file format, source, timestamp or order, and related experiment ID in the corresponding experiment metadata. Never overwrite evidence from an earlier run; create a new uniquely identified file instead.

Do not add screenshots, logs, or metrics until they are produced by an actual experiment.
