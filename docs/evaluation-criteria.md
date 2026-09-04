# Evaluation Criteria

The following criteria define the observation framework. The operationalization, evidence source, and final scale must be approved before the first experiment. No criterion has a score at this stage.

| Criterion | What to examine | Possible evidence |
| --- | --- | --- |
| Traceability | Links between requirements, specifications, plans, tasks, code, and tests. | Artifact references, commit history, test mapping |
| Persistence of context | Whether relevant decisions and context remain available across phases and sessions. | Native artifacts, prompt history, workflow records |
| Clarification of ambiguity | How the approach identifies and resolves underspecified requirements. | Questions, answers, assumptions, human decisions |
| Human intervention required | Where a person must make decisions, edit artifacts, or repair execution. | Prompt log, edit log, timestamps |
| Adoption effort | Setup, learning, configuration, and workflow overhead. | Setup record, elapsed time, intervention record |
| Artifact consistency | Agreement among specifications, plans, tasks, code, and tests. | Cross-artifact review, discrepancies |
| Validation mechanisms | Support for tests, checks, review, and acceptance validation. | Test results, validation artifacts, logs |
| Portability between agents | Whether artifacts and instructions can be used by another compatible agent or workflow. | Re-execution notes, artifact inspection |
| Suitability for greenfield | Support for starting from an approved case without an existing codebase. | Greenfield artifacts and observations |
| Suitability for brownfield | Support for understanding and changing an existing repository. | Brownfield artifacts and observations |
| Lifecycle coverage | Coverage from requirements through implementation, testing, and maintenance or change. | Workflow phases and native artifacts |
| Retrial and rework | Support for failed attempts, iteration, correction, and regeneration. | Retry records, diffs, defect log |
| Defects and regressions | Functional defects, quality issues, and behavior changes introduced by the workflow. | Tests, issue records, before/after comparison |

## Interpretation Rules

- Describe the operational definition and evidence for each criterion before scoring it.
- Keep observations separate from interpretations and conclusions.
- Report missing or incomparable evidence explicitly.
- Do not infer superiority from a single criterion or isolated observation.
