# Infrastructure Events

## Event 001 — Spec Kit initialization in non-empty workspace

- Tool: GitHub Spec Kit 1.0.6
- Stage: Stage 1
- Phase: Environment setup
- Initial command:
  `specify init --here --integration gemini --script ps --non-interactive`
- Result: Initialization stopped because the workspace already contained empty `backend/` and `frontend/` directories.
- Error:
  `Current directory is not empty and --non-interactive was set. Re-run with --force to merge into it.`
- Recovery: Re-ran initialization with `--force`.
- Recovery result: Successful.
- Verification: `specify check` reported `Specify CLI is ready to use!`
- Application code modified: No.
- Classification: Experimental setup / CLI initialization.

## Event 002 — Backend launch command mismatch during T036

- Tool: Uvicorn / FastAPI
- Phase: Manual validation
- Attempted command:
  `python -m uvicorn main:app --reload`
- Result: Failed with `Error loading ASGI app. Could not import module "main".`
- Second attempt:
  `python -m uvicorn src.main:app --reload`
- Result: Failed because `src/main.py` imports `api` as a top-level module.
- Working command:
  `python -m uvicorn main:app --app-dir src --reload`
- Working result: Backend started successfully on `http://127.0.0.1:8000`.
- Application source modified: No.
- Classification: Execution/infrastructure documentation discrepancy.

## Event 003 — Vitest / Node 20 ESM compatibility issue

- Tool: Vitest / jsdom
- Phase: Final validation
- Environment: Node `20.17.0`
- Initial result: Frontend test runner failed with `ERR_REQUIRE_ESM`.
- Diagnosis: Installed jsdom 30.x dependency chain was incompatible with the test environment's module-loading path.
- Recovery: Pinned `jsdom` to `26.0.0` and regenerated the frontend lockfile.
- Verification: Frontend tests subsequently passed 5/5.
- Application behavior modified: No.
- Classification: Test infrastructure / dependency compatibility.

## Event 004 — Frontend lint executable unavailable

- Tool: npm / ESLint
- Phase: Final validation
- Initial command: `npm run lint`
- Result: `eslint` was not recognized as a command.
- Recovery: Validation session investigated and corrected the existing validation setup.
- Classification: Validation infrastructure issue.

## Event 005 — Manual MFA validation exposed implementation defects

- Tool: Browser / Shift Bank UI
- Phase: T036 exploratory validation
- Findings:
  - Structured backend errors rendered as `[object Object]`.
  - Expired MFA confirmation did not provide the expected user-visible result.
  - Resuming a pending MFA transfer restarted the timer incorrectly.
  - Expired confirmation was blocked when the timer reached zero.
- Recovery: Findings were checked against the approved Spec Kit artifacts and classified as implementation issues.
- Recovery: Minimum source-code corrections were applied by Gemini.
- Approved specification/planning artifacts modified: No.
- Classification: Implementation correction.

## Event 006 — SonarQube project authorization mismatch

- Tool: SonarQube
- Phase: Final static analysis setup
- Initial condition: A project analysis token was associated with the OpenSpec project rather than the Spec Kit project.
- Result: Analysis could run locally but report upload was rejected with HTTP 403 authorization failure for the Spec Kit project.
- Recovery:
  - Created the dedicated `Shift Bank - Stage 1 - Spec Kit` SonarQube project.
  - Created a project analysis token associated with that project.
  - Loaded the new token into the analysis environment.
- Application source modified: No.
- Classification: Analysis infrastructure / authorization configuration.

## Event 007 — Final SonarQube analysis

- Tool: SonarQube Community Build `26.9.0.129388`
- Deployment: Docker
- Container port: `9000`
- Scanner CLI: `8.1.0.6389`
- Project key: `shift-bank-stage1-speckit`
- Project name: `Shift Bank - Stage 1 - Spec Kit`
- Source directories: `backend`, `frontend`
- Files analyzed: 28
- Result: **ANALYSIS SUCCESSFUL**
- Result: **EXECUTION SUCCESS**
- Quality Gate: **Passed**
- Application source modified by analysis: No.
- Classification: Final static-analysis validation.

### Final SonarQube results

- Security: A — 0 open issues.
- Reliability: C — 6 open issues.
- Maintainability: A — 27 open issues.
- Coverage: 0.0%.
- Duplications: 2.1%.
- Security Hotspots: 0.

### Warnings

The scanner reported warnings for SCM autodetection, Python-version configuration, and missing explicit `sonar.tests` configuration. These warnings did not prevent successful analysis.

SonarQube Community Build also reports limitations in its security analysis.