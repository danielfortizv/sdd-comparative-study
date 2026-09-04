# Reproducibility

Experiments must be repeatable from a documented starting point and procedure. Each run receives a unique identifier and preserves its own evidence.

## Required Controls

Use the same, approved:

- functional requirements;
- acceptance criteria;
- constraints and non-functional requirements;
- tool version;
- agent and model where possible;
- initial repository state;
- evaluation procedure.

Record the environment, operating system, runtime versions, dependencies, configuration, and relevant service settings. Preserve the initial and final commit hashes, together with any intermediate commits needed to explain the run.

## Evidence Policy

Store exact prompts, generated artifacts, code changes, tests, logs, screenshots, metrics, human interventions, elapsed time, defects, and regressions according to the conventions in this repository. Never overwrite evidence from a previous experiment. A rerun creates a new experiment record, even when it uses the same tool and scenario.

When a control cannot be held constant, record the deviation and explain its potential effect on comparability. Missing evidence must be identified as missing rather than reconstructed from memory.

## Repeatability Checklist

- [ ] Case and acceptance criteria are approved and unchanged.
- [ ] Initial repository commit is recorded.
- [ ] Tool, agent, model, and environment versions are recorded.
- [ ] Prompts and workflow phases are preserved.
- [ ] Human interventions are recorded.
- [ ] Final commit and test results are preserved.
- [ ] Evidence uses a unique run identifier and is not overwritten.
