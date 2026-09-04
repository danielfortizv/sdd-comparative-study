# Methodology

## Study Design

This study compares OpenSpec, GitHub Spec Kit, Tessl, BMad Method, and Kiro + AI-DLC under equivalent conditions. Each approach will be evaluated against the same approved case definitions, functional requirements, acceptance criteria, initial repository state, and evaluation procedure for the applicable scenario.

The study includes both greenfield and brownfield scenarios. The final cases remain pending approval and must be frozen before execution.

## Controlled Inputs

Before each experiment, record and preserve:

- the functional and non-functional requirements;
- acceptance criteria and constraints;
- the initial repository state and commit hash;
- tool, agent, and model versions;
- environment details and relevant configuration;
- the exact prompts and workflow phase.

## Evidence to Preserve

For every experiment, preserve the available artifacts produced during execution:

- prompts;
- specifications;
- plans;
- tasks;
- generated or modified code;
- tests;
- execution logs;
- screenshots;
- human interventions and edits;
- execution time;
- defects and regressions.

Tool-native artifact structures must be retained. Do not normalize away information that is part of a tool's workflow.

## Procedure

1. Freeze the approved case and initial repository state.
2. Record versions, environment metadata, and the experiment identifier.
3. Execute the tool using the documented prompt and workflow procedure.
4. Record clarifications, interventions, elapsed time, artifacts, tests, defects, and regressions.
5. Preserve the resulting commits and evidence without overwriting prior runs.
6. Apply the evaluation criteria consistently.
7. Record observations only when supported by preserved evidence.

No numeric values, scores, rankings, or conclusions are part of the repository until experiments have been executed and analyzed.
