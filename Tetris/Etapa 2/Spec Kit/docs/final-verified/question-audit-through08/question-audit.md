# Clarification-question audit — Spec Kit Stage 2

Scope: closed 01–08. Session 09 remains pending and is excluded. This is an audit of emitted main-model text, not a count inferred from headless execution.

Manual review of 13 unique natural-language messages found **0 observed blocking clarification questions**. Original/archive messages were deduplicated by session/response ID; completed CLI final responses matched retained messages and were not double-counted.

Blocking means asking for missing user/researcher information before proceeding. Thoughts, signatures, tool results, function arguments, native-template/specification questions and quoted code/task placeholders are excluded. Progress announcements, completion reports and the instruction to run the next workflow are not counted as user clarification requests.

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

Interrupted sessions 01/03 contain no retained emitted natural-language message. This supports zero **observed** questions, with partial coverage; it does not establish absence of unrecorded output or eventual questions of an unfinished conversation. Session 06 never started a model. The whole-experiment final count is not closed while 09 remains open.

## Evidence and excluded candidates

- Session 07, session ID cf453998-9126-4003-a157-f60f0914f4dd, response ae71f8ca-c078-430d-934c-1d4d0dacf803, 2026-10-20T12:06:37.273Z: '- [ ] [TaskID] [P?] [Story?] Description with file path'. Both question marks are quoted format placeholders.
- Session 02 reports that no '[NEEDS CLARIFICATION]' markers remain and says to run '/speckit.plan'. This is a completion/next-step instruction, not a question asking for input.

Every reviewed message has its response ID, session ID, timestamp, text hash, source-copy paths, snippet and manual adjudication in question-audit.json. Full original text remains in the referenced transcripts; this audit does not reproduce thoughts or opaque signatures.

## Researcher-origin clarifications are a separate measure

One standalone closed clarification prompt exists: 03. Four more workflow attempts 05/06/07/08 contain an appended researcher clarification in the intended input. Complete initial-message delivery is verified for 03/07/08; 05 lost its appended clarification to truncation, and 06 failed before model startup. Native-template repetition does not count as multiple external prompts. None was a reply to an observed blocking tool question. Session 09 is the separately recorded open postimplementation QA prompt and is excluded here.

| Invocation | Researcher clarification form | Initial-message delivery |
| --- | --- | --- |
| 03-contract-clarification | standalone researcher clarification prompt | verified in retained first input |
| 05-tasks | researcher clarification appended to a native workflow attempt | absent from retained first input; launcher truncation documented |
| 06-tasks-full-arguments | researcher clarification appended to a native workflow attempt | model did not start |
| 07-tasks-native-expanded | researcher clarification appended to a native workflow attempt | verified in retained first input |
| 08-implement | researcher clarification appended to a native workflow attempt | verified in retained first input |

This count must not replace the categorized external-correction metric: preimplementation clarification, launcher retry, implementation constraints and postimplementation correction are different categories. No claim of a complete mutation/provenance audit is made here; opaque shell commands require separate review.
