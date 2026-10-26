"""Reproduce the manually adjudicated emitted-text question audit.

This is an evidence collector, not a question classifier. Unknown/changed emitted
messages fail closed until a researcher reads them and records an adjudication.
The original through-08 audit is preserved without rewriting its message rows.
"""

import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path


STAGE = Path(__file__).resolve().parent.parent
DOCS = STAGE / "Spec Kit/docs"
BASELINE = DOCS / "question-audit-through08/question-audit.json"
BASELINE_SHA256 = "10EDDA9E2588EEF45601771F9622F7E9B32CCBB661688B4CADA5F8C98C1335AD"
MAIN_MODEL = "gemini-3.5-flash"
# Manually read complete natural-language text, excluding thoughts/tool output.
REVIEWED = {
    "09-qa-correction": {
        "8798f3e8-3050-48f7-9af2-dcbef2fe3f5d": (
            "3BF1FB87BC74CBA86E1CB366E7EDC073EEACB14EEB8C89C8F15217352F3ACE7F",
            "QA iteration 1 completion self-report; no request for user clarification; its completeness/robustness claims are not endorsed by this question audit",
        ),
    },
    "10-qa-race-correction": {
        "7a9968cb-331f-445a-9cf9-0d428da6dcd5": (
            "242E2C8B00689B9722D22994EF0F2535DCF21756A52DA9F9FD1A06D4D1F1F5B9",
            "QA iteration 2 completion self-report; no request for user clarification; final functional verification remains a separate measure",
        ),
    },
    "11-qa-timer-ownership": {},
    "12-qa-timer-retry": {},
    "13-qa-completion-retry": {},
    "14-qa-completion-fresh": {
        "e9829b62-6aa9-49a4-bca1-e7bdc989375d": (
            "FD7C417D92C9B28FE01EC60FD7A0DB97E1BB991B524EDE273B089BB71A9BEBFA",
            "partial backend-GET correction report and next-step workflow handoff; no request for missing user information; remaining frontend QA is explicitly unfinished",
        ),
    },
    "15-qa-frontend-completion": {},
    "16-qa-final-regressions": {
        "848ba96a-f4b1-4dc2-9fb5-761dd18e7531": (
            "1034A77A35474B09C82D7A7F54283C6A1207BEB78AC2DC0AEADD4C3E6A4D5CCB",
            "QA-3 completion/test-pass self-report; no request for missing user information; independent verification is separate from the tool's claims",
        ),
    },
    "17-qa-sonar-style": {
        "15bc8b4e-bd56-4386-90b6-a3bb3e1ed56c": ("22CDF7DD5833AB88D53914EEC2E1089FEA9D8827E834A97A2661B858AE5578DE", "progress statement about running frontend tests; no request for clarification"),
        "ce238da2-5968-48d4-a8c5-b51d1ad10160": ("C192328C3C8078C7D8ED5CFC31408CF125FA9F1BD2E67F4F5BF6D07B30D90DC8", "progress statement about production build; no request for clarification"),
        "103e69ea-4f3e-4273-aa52-7a0dd82a325f": ("1C8BC5AA28B3EFB8A26C4E48973CAAAF6746829318D85C18060864402A3EC6E0", "progress statement about comprehensive test script; no request for clarification"),
        "f1c3cf97-bd00-4945-b5a6-b43fb8bf454d": ("D1999B2949FCBFCC247A6D001306E7A5DDBE252B7A41B826A9C0565C2F4A3E7F", "QA-4 completion/test-pass self-report; question marks occur only in quoted optional-chain code, not requests for user input"),
    },
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def stamp(text):
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", text.replace("Z", "+00:00"))).astimezone(timezone.utc)


def main_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str) and not item.get("thought"))
    return ""


def records():
    """Retain every path, deduplicating main responses by session/response ID."""
    responses = {}
    notices = {}
    all_main = []
    for folder in (DOCS / "gemini-home", DOCS / "transcripts-archive"):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.jsonl")):
            session = path.stem
            relative = path.relative_to(DOCS).as_posix()
            for line in path.open(encoding="utf-8-sig", errors="replace"):
                try:
                    event = json.loads(line)
                    session = event.get("sessionId", session)
                    if event.get("type") == "gemini" and not event.get("model") and not event.get("tokens") and main_text(event.get("content")).strip():
                        identity = (session, event["id"])
                        if identity not in notices:
                            notices[identity] = {"session_id": session, "response_id": event["id"], "timestamp": event["timestamp"], "when": stamp(event["timestamp"]), "text": main_text(event.get("content")), "paths": {relative}}
                        else:
                            notices[identity]["paths"].add(relative)
                    if event.get("type") != "gemini" or event.get("model") != MAIN_MODEL:
                        continue
                    when = stamp(event["timestamp"])
                    identity = (session, event["id"])
                    text = main_text(event.get("content"))
                    all_main.append((when, event))
                    if identity not in responses:
                        responses[identity] = {"session_id": session, "response_id": event["id"], "timestamp": event["timestamp"], "when": when, "text": text, "paths": {relative}}
                    else:
                        row = responses[identity]
                        row["paths"].add(relative)
                        # A partially captured snapshot cannot replace fuller text.
                        if len(text) > len(row["text"]):
                            row["text"] = text
                except (ValueError, KeyError, TypeError):
                    continue
    return list(responses.values()), all_main, list(notices.values())


def render(data):
    lines = ["# Clarification-question audit — Spec Kit Stage 2", "", data["scope"], "", f"Manual review of **{data['reviewed_unique_natural_language_messages']} unique natural-language messages** found **{data['closed_runs_observed_blocking_question_count']} observed blocking clarification questions**. Completed CLI final responses are matched to the retained main text and never counted twice.", "", data["count_definition"], "", "Thoughts, signatures, function/tool content, native-template/specification questions and quoted code/task placeholders are excluded. Full original text remains in the referenced transcripts. Completion self-reports are evidence of emitted text, not proof of their technical claims.", "", "| Invocation | Main natural-language messages | Observed blocking questions | Coverage |", "| --- | ---: | ---: | --- |"]
    for row in data["runs"]:
        lines.append(f"| {row['label']} | {row['natural_language_message_count']} | {row['tool_requested_blocking_questions_observed']} | {row['coverage']} |")
    lines.extend(["", data["limitation"], "", "## Evidence and excluded candidates", ""])
    for row in data["excluded_question_mark_evidence"]:
        lines.append(f"- {row['label']}, session `{row['session_id']}`, response `{row['response_id']}`, {row['timestamp']}: `{row['snippet']}`. {row['reason']}.")
    summary = data["external_researcher_clarification_summary"]
    lines.extend(["- Session 02’s report of no `[NEEDS CLARIFICATION]` markers and its `/speckit.plan` handoff are completion/workflow instructions, not requests for missing information.", "- Sessions 09/10 each emitted one completion report. Manual review of their complete main text identified no request for clarification. Sessions 11/12 emitted no retained natural-language main text before terminal failures. Session 13 returned an empty CLI response after a topic update; it emitted no natural-language main text.", "- Resumed sessions 12/13 contain the synthetic CLI notice `[The previous response was interrupted before it completed.]` with no model/tokens. It is retained as excluded evidence, not attributed as a new model clarification or natural-language answer.", "", "Every reviewed message has response/session IDs, timestamp, text hash, source-copy paths, snippet and manual adjudication in `question-audit.json`. The through-08 audit is preserved unchanged in `question-audit-through08/`; rows 01–08 retain their original evidence.", "", "## Researcher-origin clarifications are separate", "", f"Closed attempts contain {summary['standalone_closed_prompt_attempts']} standalone researcher clarification/correction prompts and {summary['workflow_appended_clarification_attempts']} workflow-appended clarifications: {summary['intended_attempts_total']} intended attempts. Complete first-message delivery is verified for {summary['complete_delivery_verified_attempts']}; 05 was truncated and 06 failed before model startup. Native-template repetition does not create extra external prompts. None was a reply to an observed blocking tool question. Pending attempts {', '.join(data['pending_run_labels']) or '(none recorded)'} are excluded from these closed counts.", "", "| Invocation | Researcher clarification form | Initial-message delivery |", "| --- | --- | --- |"])
    for row in data["external_researcher_clarifications"]:
        lines.append(f"| {row['label']} | {row['kind']} | {row['delivery_status']} |")
    lines.extend(["", "These external prompt attempts are not the count of distinct QA intents or successful corrections. The metrics collector separately records QA intents, retries, process outcomes and tool actions. Session 11 closed with a 429 failure, 12 with a network failure, and 13 with exit zero but no application work. They share QA-3. Opaque shell commands require separate provenance review; this text audit is not a full mutation audit.", ""])
    return "\n".join(lines)


def main():
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest().upper() != BASELINE_SHA256:
        raise SystemExit("Frozen through-08 baseline hash changed; inspect before continuing")
    data = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
    data["excluded_question_mark_evidence"].append({"label": "17-qa-sonar-style", "session_id": "5261cb20-f8f5-406e-ab4e-69c6e85031b9", "response_id": "f1c3cf97-bd00-4945-b5a6-b43fb8bf454d", "timestamp": "2026-10-21T05:37:55.801Z", "snippet": "activeToken?.gen and pendingTickTokenRef.current?.gen", "reason": "quoted optional-chain code syntax, not an actual question to the user"})
    responses, main_events, notices = records()
    all_runs = [json.loads(path.read_text(encoding="utf-8-sig")) for path in sorted(DOCS.glob("*.run.json"))]
    closed_labels = {row["label"] for row in all_runs}
    new_runs = [row for row in all_runs if int(row["label"][:2]) > 8]
    if any(row["label"] not in REVIEWED for row in new_runs):
        raise SystemExit("New closed invocation requires manual question adjudication before this audit can be regenerated")
    baseline_rows = json.loads(json.dumps(data["runs"]))
    modspec = importlib.util.spec_from_file_location("input_audit", STAGE / "shared/audit-spec-kit-inputs.py")
    module = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(module)
    seed_path = STAGE / "shared/seed.md"
    seed = "\n".join(re.sub(r"^> ?", "", line) for line in seed_path.read_text(encoding="utf-8-sig").splitlines() if line.startswith(">")).strip()
    inputs, _ = module.transcript_records(DOCS, seed)
    excluded_notices = []
    for run in new_runs:
        start, end = stamp(run["started"]), stamp(run["ended"])
        interval = [row for row in responses if start <= row["when"] <= end]
        natural = sorted((row for row in interval if row["text"].strip()), key=lambda row: (row["when"], row["response_id"]))
        for notice in notices:
            if start <= notice["when"] <= end:
                if sha(notice["text"]) != "A1FF6ADEABCBA4ABB8C9C2FECCF6C35076B3EB44375CC722BA5D873A26430641":
                    raise SystemExit(f"Unreviewed unlabeled text in {run['label']}: {notice['response_id']}")
                excluded_notices.append({"label": run["label"], "session_id": notice["session_id"], "response_id": notice["response_id"], "timestamp": notice["timestamp"], "transcript_copies": sorted(notice["paths"]), "snippet": notice["text"], "decoded_text_utf8_sha256": sha(notice["text"]), "reason": "synthetic CLI interruption notice with no model or tokens; excluded from emitted main-model text and blocking-question counts"})
        expected = REVIEWED[run["label"]]
        if {row["response_id"] for row in natural} != set(expected):
            raise SystemExit(f"Unreviewed/absent natural text in {run['label']}: {[row['response_id'] for row in natural]}")
        evidence = []
        for row in natural:
            expected_hash, adjudication = expected[row["response_id"]]
            if sha(row["text"]) != expected_hash:
                raise SystemExit(f"Changed natural text requires review: {run['label']} / {row['response_id']}")
            evidence.append({"response_id": row["response_id"], "session_id": row["session_id"], "timestamp": row["timestamp"], "transcript_copies": sorted(row["paths"]), "decoded_text_utf8_sha256": sha(row["text"]), "characters": len(row["text"]), "snippet": row["text"][:260], "adjudication": adjudication, "blocking_question_count": 0})
        stdout = DOCS / f"{run['label']}.stdout.json"
        final_text = json.loads(stdout.read_text(encoding="utf-8-sig")).get("response", "") if stdout.exists() and stdout.stat().st_size else ""
        final_matches = [row["response_id"] for row in natural if row["text"] == final_text] if final_text else []
        if final_text and not final_matches:
            raise SystemExit(f"Unmatched CLI final response requires review: {run['label']}")
        failed = run.get("exit_code") != 0
        coverage = "retained main transcript interval and matching completed CLI final response"
        if failed:
            coverage = f"retained main transcript interval; terminal failure (exit {run.get('exit_code')}) without final response, so no claim about unrecorded output or eventual questions"
        elif not final_text:
            coverage = "retained main transcript interval; completed CLI response empty, with no emitted main natural-language text; action evidence is separate and process success does not prove completed QA"
        data["runs"].append({"label": run["label"], "started": run["started"], "ended": run["ended"], "exit_code": run.get("exit_code"), "session_ids": sorted({row["session_id"] for row in interval}), "retained_transcript_paths": sorted({path for row in interval for path in row["paths"]}), "natural_language_message_count": len(natural), "tool_requested_blocking_questions_observed": 0, "coverage": coverage, "cli_final_response_matches": final_matches, "message_evidence": evidence})
        prompt_path = DOCS / f"{run['label']}.prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        prefix = prompt.partition(seed)[0].rstrip()
        first = min((entry for entry in inputs if start <= entry["when"] <= end and prefix in entry["text"].replace("\r\n", "\n")), key=lambda entry: entry["when"], default=None)
        raw_first = min((entry for entry in inputs if start <= entry["when"] <= end), key=lambda entry: entry["when"], default=None)
        delivered = bool(first and prefix in first["text"].replace("\r\n", "\n"))
        if not delivered:
            raise SystemExit(f"New external prompt delivery is not verified: {run['label']}")
        data["external_researcher_clarifications"].append({"label": run["label"], "kind": "standalone researcher postimplementation correction prompt", "intended_input_path": prompt_path.name, "clarification_utf8_sha256": sha(prefix), "clarification_hash_scope": "normalized LF researcher prompt prefix preceding the extracted frozen seed block, trimmed at end", "snippet": prefix[:295], "effective_first_input_session_id": first["session"], "effective_first_input_timestamp": first["timestamp"], "effective_first_input_transcript_copies": sorted(first["paths"]), "complete_clarification_in_effective_first_input": delivered, "delivery_status": "verified in retained matching submitted-prompt input; earlier synthetic/replayed user-like context is excluded" if run["label"] == "13-qa-completion-retry" else "verified in retained first input", "reply_to_observed_blocking_tool_question": False})
        clarification = data["external_researcher_clarifications"][-1]
        clarification.update({
            "effective_first_input_session_id": raw_first["session"] if raw_first else None,
            "effective_first_input_timestamp": raw_first["timestamp"] if raw_first else None,
            "effective_first_input_transcript_copies": sorted(raw_first["paths"]) if raw_first else [],
            "complete_clarification_in_effective_first_input": bool(raw_first and prefix in raw_first["text"].replace("\r\n", "\n")),
            "effective_submitted_prompt_session_id": first["session"],
            "effective_submitted_prompt_timestamp": first["timestamp"],
            "effective_submitted_prompt_transcript_copies": sorted(first["paths"]),
            "complete_clarification_in_effective_submission": delivered,
        })
    assert data["runs"][:8] == baseline_rows, "Original 01–08 evidence changed"
    pending = [path.name.removesuffix(".started.json") for path in sorted(DOCS.glob("*.started.json")) if path.name.removesuffix(".started.json") not in closed_labels]
    last = max(closed_labels).split("-", 1)[0]
    data.update({"audited_at_utc": datetime.now(timezone.utc).isoformat(), "scope": f"closed experiment invocations 01–{last} only; pending invocations excluded: {', '.join(pending) or '(none recorded)'}", "closed_run_labels": sorted(closed_labels), "pending_run_labels": pending, "reviewed_unique_natural_language_messages": sum(row["natural_language_message_count"] for row in data["runs"]), "closed_runs_observed_blocking_question_count": sum(row["tool_requested_blocking_questions_observed"] for row in data["runs"]), "coverage_limited_run_labels": ["01-specify", "03-contract-clarification", "11-qa-timer-ownership", "12-qa-timer-retry", "13-qa-completion-retry", "15-qa-frontend-completion"], "limitation": f"Zero observed questions follows manual review of retained emitted text, not headless mode. Interrupted 01/03, failed 11/12 and empty 13/15 emitted no retained natural-language main text; unrecorded output or eventual questions in an unfinished conversation cannot be ruled out. Pending invocations: {', '.join(pending) or 'none recorded'}. This is an observed count for closed retained intervals, not proof of an absolute absence of unrecorded questions.", "preserved_through08_audit": {"path": BASELINE.relative_to(DOCS).as_posix(), "sha256": BASELINE_SHA256, "original_run_rows_preserved": True}, "interval_scope": "Each closed start/end interval is applied before counting, including resumed sessions. Responses appended after an attempt closed are excluded from that attempt even if stored in the same session file. Original/archive copies are deduplicated by session/response identity."})
    data["external_researcher_clarification_summary"].update({"standalone_closed_prompt_attempts": 1 + len(new_runs), "workflow_appended_clarification_attempts": 4, "intended_attempts_total": 5 + len(new_runs), "complete_delivery_verified_attempts": 3 + len(new_runs), "truncated_before_delivery_attempts": 1, "pre_model_launcher_failure_attempts": 1, "pending_prompt_attempt_labels": pending})
    data["excluded_non_model_notices"] = excluded_notices
    names = set(data["interactive_question_tool_crosscheck"]["observed_tool_names"])
    for when, event in main_events:
        if not any(stamp(run["started"]) <= when <= stamp(run["ended"]) for run in all_runs):
            continue
        content = event.get("content")
        for call in event.get("toolCalls", []):
            if call.get("name"):
                names.add(call["name"])
        for part in content if isinstance(content, list) else []:
            call = part.get("functionCall", {}) if isinstance(part, dict) else {}
            if call.get("name"):
                names.add(call["name"])
    data["interactive_question_tool_crosscheck"]["observed_tool_names"] = sorted(names)
    data["interactive_question_tool_crosscheck"]["known_interactive_question_tool_names_observed"] = sorted(name for name in names if name in {"ask_user", "ask_user_question", "request_user_input"})
    (DOCS / "question-audit.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (DOCS / "question-audit.md").write_text(render(data), encoding="utf-8")
    print(json.dumps({"closed_runs": len(data["runs"]), "natural_messages": data["reviewed_unique_natural_language_messages"], "observed_blocking_questions": data["closed_runs_observed_blocking_question_count"], "pending": pending, "external_clarifications": data["external_researcher_clarification_summary"]}, indent=2))


if __name__ == "__main__":
    main()
