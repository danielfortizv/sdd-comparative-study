# Infrastructure Events

## Event 001

- Tool: OpenSpec + Gemini CLI
- Stage: Stage 1
- Workflow: `/opsx:explore`
- Result: Failed
- Error: `API Error: Tool call cancelled while in queue`
- Additional symptom: Gemini remained in a `Thinking...` state and rejected another slash command with `Slash commands cannot be queued`.
- Action taken: The request was manually cancelled and the Gemini CLI session was restarted.
- Final result: `/opsx:explore` worked correctly after restarting the session.
- Classification: Infrastructure / agent integration issue
- Counts as correction: No

## Event 002 - Experimental context leakage

- Tool: OpenSpec + Gemini CLI
- Stage: Stage 1
- Workflow: `/opsx:explore`
- Result: Workflow executed successfully.
- Observation: During exploration, the agent explicitly listed the `docs/` directory and read `00_experiment_metadata.md` and `01_seed_prompt.md`.
- Expected behavior: Experimental documentation should not be available as development context.
- Cause: `.geminiignore` did not prevent the agent from explicitly accessing these files through workspace file-reading tools.
- Action taken: Experimental records were moved completely outside the OpenSpec development workspace.
- Code modified: No
- OpenSpec change created: No
- Counts as correction: No
- Classification: Experimental setup / context isolation issue
- Experimental validity: This exploration run is excluded from the comparative results.

### Discarded Session Summary

- Session ID: a7342cd8-6853-4e7f-a17c-1362fee1f802
- Experimental status: Excluded
- Reason: Experimental context leakage from `docs/`
- Tool calls: 10
- Tool-call success rate: 100%
- Wall time: 8m 18s
- Agent active time: 1m 27s
- API time: 1m 04s
- Tool time: 22.8s

#### Model usage

Main experimental model:
- Model: gemini-3.5-flash
- Model requests: 11
- Input tokens: 161,055
- Cache reads: 116,237
- Output tokens: 1,458

Internal utility model:
- Model: gemini-3.1-flash-lite
- Purpose: utility_summarizer
- Requests: 1
- Input tokens: 536
- Output tokens: 11

## Event 003 - OpenSpec validation CLI option mismatch

- Tool: OpenSpec + Gemini CLI
- Stage: Stage 1
- Action: Planning artifact validation
- Attempted command: `openspec validate --change "stage1-requirements"`
- Result: Failed because OpenSpec 1.11.0 does not recognize the `--change` option.
- Error: `unknown option '--change'`
- Recovery: Agent executed `openspec validate` and opened the interactive validation selector.
- Code modified: No
- Counts as correction: No
- Classification: Tool / CLI invocation issue
- Recovery result: Successful
- Final validation result: `Change 'stage1-requirements' is valid`

## Event 004 - PowerShell test-command compatibility during Apply

- Tool: OpenSpec + Gemini CLI
- Stage: Stage 1
- Phase: Apply / Functional verification
- Result: Two test command attempts failed because of shell/PowerShell compatibility.
- First issue: A shell command for testing an incorrect MFA code was blocked because command substitution was detected.
- Second issue: `Invoke-WebRequest` failed because the installed PowerShell version did not support the `-SkipHttpErrorCheck` parameter.
- Recovery: The agent switched to `curl.exe` and successfully verified both incorrect and correct MFA behavior.
- Application code modified because of this event: No
- Counts as correction: No
- Classification: Test infrastructure / shell compatibility issue
- Final result: Recovered successfully; functional verification continued.

## Event 005 - SonarScanner PowerShell argument parsing

- Tool: SonarScanner CLI via Docker
- Stage: Stage 1
- Target: OpenSpec implementation
- Result: Initial scan did not start.
- Error: `Unrecognized option: .projectKey=shift-bank-stage1-openspec`
- Cause: SonarScanner `-D...` properties were not passed correctly through PowerShell.
- Recovery: Re-ran the Docker command with each SonarScanner `-D...` property explicitly quoted.
- Code modified: No
- Counts as correction: No
- Classification: Evaluation infrastructure / command invocation issue