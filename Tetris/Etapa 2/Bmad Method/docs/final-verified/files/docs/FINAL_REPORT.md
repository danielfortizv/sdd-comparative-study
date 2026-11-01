# BMAD Stage2 option A — verified local result

Researcher report. Code and native specs were generated via BMAD6.12.0 / GeminiCLI0.60.0 with unchanged commonseed and requested3.5Flash. No commits/push.

Exact Sonar analysis `0b7d51b5-586c-4af2-8c0f-221a07a197d3`: **OK**, baseline1.0/candidate2.0. Source and both canonical coverage hashes still match the analysis.

## Independent final checks

Backend 18/18 passed; original13tests/52assertions preserved. Production backend coverage 92.74% (166/179).
Frontend generated 14/14; external 11/11; domain/API24/24; clean npmci/build; npm and targetvenv audit0. Frontend v8 statements89.71%,branches77.53%,functions100%,lines95.54%; allsrc inclmain.
Common catalog18/18ordinary+2/2isolateddomain; 3/4rowclears are not claimed ordinaryreachable. APIadapterv1.3 onlynormalizes observation shape/objectcoordinates, preservingrawHTTP201responses; supplementalcontractv1.2unchanged9controls.

## CLI usage — retained observed counters

| Run | seconds | exit | input inclcache | cache | output | thoughts | API/errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 01-prd | 235.503 | 0 | 1,557,313 | 1,304,035 | 9,758 | 11,370 | 34/0 |
| 02-design-stories | 423.88 | 0 | 3,808,691 | 2,971,386 | 20,830 | 25,045 | 60/1 |
| 03-planning-completion | 417.211 | 0 | 5,259,143 | 4,587,288 | 15,433 | 18,262 | 74/3 |
| 04-implementation | 624.327 | 53 | 6,585,008 | 5,217,489 | 21,681 | 28,882 | unknown |
| 05-correction | 581.356 | 53 | 5,964,506 | 5,208,068 | 8,372 | 30,475 | unknown |
| 06-quality-completion | 771.706 | 53 | 5,939,693 | 4,878,238 | 22,197 | 25,486 | unknown |
| 07-six-sonar-findings | 509.1 | 0 | 4,315,349 | 3,340,029 | 11,012 | 17,142 | 74/9 |

Closed CLI walltime 3563.083s; recordedtokens {'input_tokens': 33429703, 'cached_tokens': 27506533, 'output_tokens': 109283, 'thought_tokens': 156662}. Cache is a subset of input, never additive. APIknownsums {'api_requests': 242, 'api_errors': 13, 'api_successful_requests': 229}, excludedunknownruns ['04-implementation', '05-correction', '06-quality-completion']. Fullseeddeliveryaudited7/7; questions0observedretainedclosedintervals; externalQAintentBMAD-QA-01,3attempts05–07.

## Measured artifacts

Source baseline9files/1036lines/31549chars -> final12files/2040lines/61593chars; density115.11->170.00. Includes tests and source-likeconfig; excludesdependencies/build/cache/researcherevidence.
InheritedsixMD1120lines/68220chars remain unchanged. NewnativeprincipalStage2MD8/977lines/78537chars; density122.12. Reviews/memlogs/YAMLtrackedseparately.24declarednewFRIDs,4epics/12stories; no automaticatomicity/qualityscore inferred.

## Run the local app

Backend from toolroot: `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020`.
Frontend from toolroot: `node frontend/node_modules/vite/bin/vite.js --config docs/acceptance/vite.browser.config.mjs`. Browser http://127.0.0.1:5174/. Current researcher runtime seeded20260929; optional fixtures declared in runtime metadata and affect firstcreateonly. Subsequent newgames use original create.

## Limits and deviations

- Sequential native reviews were performed in same session; not independent reviewers.
- 04,05,06 reached80turnlimit; JSONLtokens are observed retained usage, API totals for those runs are unavailable. Known API sums exclude them. Codex orchestrator/account usage not measured or queried.
- Model-written docs/build-07/*results.txt are transcriptions, not raw subprocess captures. RawCLItranscripts and independent docs/validation/*.log+metadata are authoritative.
- Sprint YAML marks4optionalretrospectives done but no corresponding retrospective artifacts were verified; do not count them executed. last_updated remains an earlier authored timestamp, not completion timing.
- Original13ASTassertions are preserved, while fixture setup was adapted for queuedpiece semantics. New isolated3/4rowfixtures use canonicalO, not ordinaryplay.
- Early API-based left observation became inconclusive after activepiece changed; preserved failed observation and verified actual horizontal shift via uninterrupted DOM-backed browser observation instead.
- Native main.test asserts root existence only; realbootstrap separately verified in browser. Coverage percentage is not proof of assertion quality or scalability.
- 12legacySonarsmells and1legacyrandom.choice finding remain visible; newviolations0. No exclusions/gate weakening/falsepositive resolution.
- Quota task/script and Codexheartbeat remain disabled; noquotaqueries or poweractions.
- Native07Sonar initially consumed pre-extraction backendXML177statements. Researcher preserved that analysis, rebound freshly executed179statement coverage and repeated scan/CE/gate; finalanalysis above supersedes d649734f. No application source changes or extra model calls.
- One Python audit JSON filename collided with recorder metadata; audit rerun with separate pip-audit-report.json retained0vulnerabilities/50packages. Relative executable127 retry and earlier sandbox errors are infrastructure, not application failures.

Native sourcestatus and self-reports are evidence, not independent acceptance. No further model calls were made after07; root authored only researcherinfrastructure, fixtures, metrics and documentation.
