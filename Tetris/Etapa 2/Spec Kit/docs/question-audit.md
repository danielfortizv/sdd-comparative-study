# Clarification-question audit — Spec Kit Stage 2

closed experiment invocations 01–17 only; pending invocations excluded: (none recorded)

Manual review of **21 unique natural-language messages** found **0 observed blocking clarification questions**. Completed CLI final responses are matched to the retained main text and never counted twice.

A blocking clarification question is emitted main-model natural-language text requesting missing user/researcher input before proceeding. Count requests, not question-mark characters. Self-directed progress statements, completion summaries and workflow-next-step instructions are not clarification questions.

Thoughts, signatures, function/tool content, native-template/specification questions and quoted code/task placeholders are excluded. Full original text remains in the referenced transcripts. Completion self-reports are evidence of emitted text, not proof of their technical claims.

| Invocation | Main natural-language messages | Observed blocking questions | Coverage |
| --- | ---: | ---: | --- |
| 01-specify | 0 | 0 | retained main transcript interval; interrupted without final response, so no claim about unrecorded output |
| 02-specify-retry | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 03-contract-clarification | 0 | 0 | retained main transcript interval; interrupted without final response, so no claim about unrecorded output |
| 04-plan | 3 | 0 | retained main transcript interval and matching completed CLI final response |
| 05-tasks | 3 | 0 | retained main transcript interval and matching completed CLI final response |
| 06-tasks-full-arguments | 0 | 0 | no model startup; zero follows launcher failure evidence |
| 07-tasks-native-expanded | 5 | 0 | retained main transcript interval and matching completed CLI final response |
| 08-implement | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 09-qa-correction | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 10-qa-race-correction | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 11-qa-timer-ownership | 0 | 0 | retained main transcript interval; terminal failure (exit 429) without final response, so no claim about unrecorded output or eventual questions |
| 12-qa-timer-retry | 0 | 0 | retained main transcript interval; terminal failure (exit 1) without final response, so no claim about unrecorded output or eventual questions |
| 13-qa-completion-retry | 0 | 0 | retained main transcript interval; completed CLI response empty, with no emitted main natural-language text; action evidence is separate and process success does not prove completed QA |
| 14-qa-completion-fresh | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 15-qa-frontend-completion | 0 | 0 | retained main transcript interval; completed CLI response empty, with no emitted main natural-language text; action evidence is separate and process success does not prove completed QA |
| 16-qa-final-regressions | 1 | 0 | retained main transcript interval and matching completed CLI final response |
| 17-qa-sonar-style | 4 | 0 | retained main transcript interval and matching completed CLI final response |

Zero observed questions follows manual review of retained emitted text, not headless mode. Interrupted 01/03, failed 11/12 and empty 13/15 emitted no retained natural-language main text; unrecorded output or eventual questions in an unfinished conversation cannot be ruled out. Pending invocations: none recorded. This is an observed count for closed retained intervals, not proof of an absolute absence of unrecorded questions.

## Evidence and excluded candidates

- 07-tasks-native-expanded, session `cf453998-9126-4003-a157-f60f0914f4dd`, response `ae71f8ca-c078-430d-934c-1d4d0dacf803`, 2026-10-20T12:06:37.273Z: `- [ ] [TaskID] [P?] [Story?] Description with file path`. quoted task-format syntax, not an actual question to the user.
- 17-qa-sonar-style, session `5261cb20-f8f5-406e-ab4e-69c6e85031b9`, response `f1c3cf97-bd00-4945-b5a6-b43fb8bf454d`, 2026-10-21T05:37:55.801Z: `activeToken?.gen and pendingTickTokenRef.current?.gen`. quoted optional-chain code syntax, not an actual question to the user.
- Session 02’s report of no `[NEEDS CLARIFICATION]` markers and its `/speckit.plan` handoff are completion/workflow instructions, not requests for missing information.
- Sessions 09/10 each emitted one completion report. Manual review of their complete main text identified no request for clarification. Sessions 11/12 emitted no retained natural-language main text before terminal failures. Session 13 returned an empty CLI response after a topic update; it emitted no natural-language main text.
- Resumed sessions 12/13 contain the synthetic CLI notice `[The previous response was interrupted before it completed.]` with no model/tokens. It is retained as excluded evidence, not attributed as a new model clarification or natural-language answer.

Every reviewed message has response/session IDs, timestamp, text hash, source-copy paths, snippet and manual adjudication in `question-audit.json`. The through-08 audit is preserved unchanged in `question-audit-through08/`; rows 01–08 retain their original evidence.

## Researcher-origin clarifications are separate

Closed attempts contain 10 standalone researcher clarification/correction prompts and 4 workflow-appended clarifications: 14 intended attempts. Complete first-message delivery is verified for 12; 05 was truncated and 06 failed before model startup. Native-template repetition does not create extra external prompts. None was a reply to an observed blocking tool question. Pending attempts (none recorded) are excluded from these closed counts.

| Invocation | Researcher clarification form | Initial-message delivery |
| --- | --- | --- |
| 03-contract-clarification | standalone researcher clarification prompt | verified in retained first input |
| 05-tasks | researcher clarification appended to a native workflow attempt | absent from retained first input; launcher truncation documented |
| 06-tasks-full-arguments | researcher clarification appended to a native workflow attempt | model did not start |
| 07-tasks-native-expanded | researcher clarification appended to a native workflow attempt | verified in retained first input |
| 08-implement | researcher clarification appended to a native workflow attempt | verified in retained first input |
| 09-qa-correction | standalone researcher postimplementation correction prompt | verified in retained first input |
| 10-qa-race-correction | standalone researcher postimplementation correction prompt | verified in retained first input |
| 11-qa-timer-ownership | standalone researcher postimplementation correction prompt | verified in retained first input |
| 12-qa-timer-retry | standalone researcher postimplementation correction prompt | verified in retained first input |
| 13-qa-completion-retry | standalone researcher postimplementation correction prompt | verified in retained matching submitted-prompt input; earlier synthetic/replayed user-like context is excluded |
| 14-qa-completion-fresh | standalone researcher postimplementation correction prompt | verified in retained first input |
| 15-qa-frontend-completion | standalone researcher postimplementation correction prompt | verified in retained first input |
| 16-qa-final-regressions | standalone researcher postimplementation correction prompt | verified in retained first input |
| 17-qa-sonar-style | standalone researcher postimplementation correction prompt | verified in retained first input |

These external prompt attempts are not the count of distinct QA intents or successful corrections. The metrics collector separately records QA intents, retries, process outcomes and tool actions. Session 11 closed with a 429 failure, 12 with a network failure, and 13 with exit zero but no application work. They share QA-3. Opaque shell commands require separate provenance review; this text audit is not a full mutation audit.
