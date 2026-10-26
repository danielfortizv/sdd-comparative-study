"""Collect Tessl Stage 2 emitted text and reproduce a manual question audit.

Standalone researcher infrastructure: reads Tessl run metadata/transcripts only;
never imports another tool's app/specifications or runs the coding agent. Default
execution writes Tessl/docs/question-audit.json and .md. Exit 2 means a closed
interval requires manual review; its candidate text is still saved for review.

After reading every candidate in a closed interval, enter its run metadata hash,
candidate signature and explicit per-message decisions in REVIEWED_RUNS. Unknown
or changed text never inherits a zero question count. Open intervals are pending.
Researcher prompt classification is separately reviewed and bound to prompt hash;
the run's phase name is never used to infer clarification or corrective intent.
"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


STAGE = Path(__file__).resolve().parent.parent
DOCS = STAGE / "Tessl/docs"
DEFAULT_MAIN_MODEL = "gemini-3.5-flash"
SYNTHETIC_CLI_NOTICES = {
    "[The previous response was interrupted before it completed.]",
}

# Manually adjudicated closed intervals only. A review entry has this structure:
# "01-specify": {
#   "run_metadata_sha256": "...", "candidate_signature_sha256": "...",
#   "reviewed_at_utc": "...", "reviewer": "researcher",
#   "coverage_note": "Describe retained coverage and partial/failed limits.",
#   "messages": {
#     "session/response": {
#       "selected_text_sha256": "...", "blocking_question_count": 0,
#       "classification": "emitted_main_text", "reason": "Manual decision ..."
#     }
#   }
# }
# Classifications: emitted_main_text; quoted_or_template_only;
# synthetic_cli_notice; not_main_model_text. The latter three require count 0.
# Empty intervals also require an explicit reviewed run with messages={}.
REVIEWED_RUNS = {
    "01-specify": {
        "run_metadata_sha256": "427B7205B22BB778ED21B86E7E106EE5CFB41850BE8CD815AF5C9BAC9593638C",
        "candidate_signature_sha256": "3126FC1B9FE30C993816F842DC453F893620A58068EA5085255273B237ABE4E4",
        "reviewed_at_utc": "2026-10-21T14:39:57Z",
        "reviewer": "researcher",
        "coverage_note": "Read the complete 3,072-character emitted main text. One unique natural-language report is retained in identical original/archive copies and exactly matches completed CLI response. Seventeen main response IDs include tool-only/empty-text events, which are not natural-language messages. This is observed retained coverage, not a guarantee about unrecorded output.",
        "messages": {
            "08c8cdbc-c131-4ede-9b86-b365f410cbd7/15d2c984-3c44-4d65-87a3-bd63ad5a2ef1": {
                "selected_text_sha256": "92B373765739C5521AA375B021AC24CBF5D9B2989172F4CD4EAD0501C739B35A",
                "blocking_question_count": 0,
                "classification": "emitted_main_text",
                "reason": "Specification completion/design-resolution self-report followed by a workflow handoff to the later implementation phase; no request for missing user information. The closing readiness statement is not a blocking clarification question. Claims about files, tests, integration/authentication or mathematical reachability are not endorsed or independently verified by this text audit.",
            },
        },
    },
}

# This complete intended prompt was manually read on 2026-10-21. Its workflow
# clarification preserves Tessl's own brownfield contract; it is not a response
# to a model question or a postimplementation correction. Delivery is audited
# separately, and is not established by an intended prompt's presence.
RESEARCHER_PROMPT_REVIEWS = {
    "01-specify": {
        "prompt_sha256": "BFF90383515B217A2FAB69C2732D48B6CFF185EDFDE9D5C108236B3B8103AF00",
        "kind": "initial specification request with recorded workflow clarification",
        "clarification_bearing": True,
        "corrective_intent": False,
        "reply_to_model_blocking_question": False,
        "reviewed_at_utc": "2026-10-21T14:36:16Z",
        "reason": "Initial specification-only request includes a researcher-origin workflow clarification of inherited contract, terminal draws, domain fixtures and deterministic acceptance. It is not a later fix or a reply to an emitted model question.",
    },
}


# Additional manual reviews are data, hash-bound by review_run below; never infer
# a zero count from a run label or silently inherit a review after text changes.
_extra_review_file = DOCS / "question-review.json"
if _extra_review_file.exists():
    _extra_reviews = json.loads(_extra_review_file.read_text(encoding="utf-8-sig"))
    REVIEWED_RUNS.update(_extra_reviews.get("runs", {}))
    RESEARCHER_PROMPT_REVIEWS.update(_extra_reviews.get("prompts", {}))


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest().upper()


def json_sha(data):
    return sha(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def time_key(value):
    """Integer nanoseconds preserve PowerShell's seven-digit interval boundaries."""
    match = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)", value)
    if not match:
        raise ValueError("Expected timezone-qualified ISO timestamp")
    fraction = match[2] or ""
    if len(fraction) > 9 and any(c != "0" for c in fraction[9:]):
        raise ValueError("Timestamp precision exceeds nanoseconds")
    seconds = datetime.fromisoformat(match[1] + match[3].replace("Z", "+00:00"))
    return int(seconds.timestamp()) * 1_000_000_000 + int(fraction[:9].ljust(9, "0"))


def main_text(content):
    """Only emitted content text; never thoughts, signatures or call arguments."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict) and isinstance(content.get("parts"), list):
        content = content["parts"]
    if not isinstance(content, list):
        return ""
    parts = []
    for part in content:
        if not isinstance(part, dict) or part.get("thought") or part.get("type") in {"thought", "reasoning"}:
            continue
        if any(key in part for key in ("functionCall", "functionResponse", "toolCall", "toolResponse")):
            continue
        if isinstance(part.get("text"), str):
            parts.append(part["text"])
    return "\n".join(parts)


def embedded_messages(event):
    if isinstance(event.get("messages"), list):
        yield from (item for item in event["messages"] if isinstance(item, dict))
    update = event.get("$set", {})
    if isinstance(update, dict) and isinstance(update.get("messages"), list):
        yield from (item for item in update["messages"] if isinstance(item, dict))


def collect_records():
    events, sources, warnings, unassigned = [], [], [], []
    for folder in (DOCS / "gemini-home", DOCS / "transcripts-archive"):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.jsonl")):
            relative = path.relative_to(DOCS).as_posix()
            if not path.resolve().is_relative_to(DOCS.resolve()):
                warnings.append({"path": relative, "reason": "resolved transcript escapes Tessl docs; excluded"})
                continue
            raw = path.read_bytes()
            sources.append({"path": relative, "bytes_read": len(raw), "sha256": sha(raw), "snapshot_scope": "bytes observed by this audit; an active source may append later"})
            session = None
            lines = raw.decode("utf-8-sig", errors="replace").splitlines()
            for line_number, line in enumerate(lines, 1):
                try:
                    event = json.loads(line)
                except ValueError:
                    warnings.append({"path": relative, "line": line_number, "reason": "unparseable JSONL line; possibly partial active write", "line_sha256": sha(line)})
                    continue
                if not isinstance(event, dict):
                    continue
                session = event.get("sessionId") or session
                for container, message in [("event", event), *(("embedded_messages", item) for item in embedded_messages(event))]:
                    if message.get("type") != "gemini":
                        continue
                    text = main_text(message.get("content"))
                    local_session = message.get("sessionId") or session
                    identity = message.get("id")
                    timestamp = message.get("timestamp")
                    row = {
                        "session_id": local_session, "response_id": identity,
                        "timestamp": timestamp, "model": message.get("model"),
                        "tokens_present": bool(message.get("tokens")), "text": text,
                        "source_location": {"path": relative, "line": line_number, "container": container},
                        "tool_names": sorted({call.get("name") for call in message.get("toolCalls", []) if isinstance(call, dict) and isinstance(call.get("name"), str)}),
                    }
                    content = message.get("content")
                    for part in content if isinstance(content, list) else []:
                        call = part.get("functionCall", {}) if isinstance(part, dict) else {}
                        if isinstance(call, dict) and isinstance(call.get("name"), str):
                            row["tool_names"].append(call["name"])
                    try:
                        row["when"] = time_key(timestamp)
                    except (ValueError, TypeError):
                        if text.strip():
                            unassigned.append({key: value for key, value in row.items() if key not in {"tool_names"}})
                        continue
                    if not local_session or not identity:
                        if text.strip():
                            unassigned.append({**row, "reason": "missing session or response ID; no guessed identity"})
                        continue
                    events.append(row)
    return events, sources, warnings, unassigned


def read_runs(observed_at):
    closed, pending = [], []
    closed_labels = set()
    for path in sorted(DOCS.glob("*.run.json")):
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
        label = path.name.removesuffix(".run.json")
        if value.get("label") != label or time_key(value["ended"]) < time_key(value["started"]):
            raise ValueError(f"Invalid closed interval metadata: {path.name}")
        closed.append({**value, "metadata_path": path.name, "metadata_sha256": sha(raw), "state": "closed"})
        closed_labels.add(label)
    for path in sorted(DOCS.glob("*.started.json")):
        label = path.name.removesuffix(".started.json")
        if label in closed_labels:
            continue
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
        if value.get("label") != label:
            raise ValueError(f"Mismatched active metadata label: {path.name}")
        time_key(value["started"])
        pending.append({**value, "metadata_path": path.name, "metadata_sha256": sha(raw), "state": "pending", "observed_until": observed_at})
    return closed, pending


def candidates_for_run(run, events):
    start = time_key(run["started"])
    end = time_key(run["ended"] if run["state"] == "closed" else run["observed_until"])
    interval = [row for row in events if start <= row["when"] <= end]
    main_model = run.get("requested_model", DEFAULT_MAIN_MODEL)
    grouped, excluded = {}, []
    for row in interval:
        if not row["text"].strip():
            continue
        key = (row["session_id"], row["response_id"])
        grouped.setdefault(key, []).append(row)
    candidates = []
    for (session, response), copies in sorted(grouped.items(), key=lambda item: (min(r["when"] for r in item[1]), item[0])):
        variants = {}
        for row in copies:
            text_hash = sha(row["text"])
            variant = variants.setdefault(text_hash, {"text": row["text"], "decoded_text_utf8_sha256": text_hash, "characters": len(row["text"]), "models": set(), "timestamps": set(), "tokens_present": False, "locations": []})
            variant["models"].add(row["model"])
            variant["timestamps"].add(row["timestamp"])
            variant["tokens_present"] |= row["tokens_present"]
            if row["source_location"] not in variant["locations"]:
                variant["locations"].append(row["source_location"])
        choices = []
        for value in variants.values():
            value["models"] = sorted(value["models"], key=lambda x: x or "")
            value["timestamps"] = sorted(value["timestamps"], key=time_key)
            value["locations"] = sorted(value["locations"], key=lambda x: (x["path"], x["line"], x["container"]))
            choices.append(value)
        choices.sort(key=lambda x: (x["characters"], x["decoded_text_utf8_sha256"]), reverse=True)
        longest = choices[0]
        models = {model for row in copies for model in [row["model"]] if model}
        evidence = {
            "candidate_id": f"{session}/{response}", "session_id": session,
            "response_id": response, "timestamp": min((r["timestamp"] for r in copies), key=time_key),
            "models_observed": sorted(models), "attribution": "main_model" if main_model in models else "other_labeled_model" if models else "unlabeled_requires_review",
            "text": longest["text"], "snippet": longest["text"][:500],
            "decoded_text_utf8_sha256": longest["decoded_text_utf8_sha256"],
            "characters": longest["characters"], "text_variants": choices,
            "variant_conflict": not all(longest["text"].startswith(value["text"]) for value in choices),
            "transcript_copies": sorted({r["source_location"]["path"] for r in copies}),
            "manual_adjudication": None,
        }
        if not models and not any(row["tokens_present"] for row in copies) and all(value["text"] in SYNTHETIC_CLI_NOTICES for value in choices):
            evidence["exclusion_reason"] = "exact known synthetic CLI interruption notice, with neither model label nor tokens; not emitted main-model text"
            excluded.append(evidence)
        elif models and main_model not in models:
            evidence["exclusion_reason"] = "explicitly labeled other/auxiliary model, excluded from main-text question count"
            excluded.append(evidence)
        else:
            candidates.append(evidence)
    stdout_path = DOCS / f"{run['label']}.stdout.json"
    final = {"path": stdout_path.name, "state": "not completed", "matches": []}
    if run["state"] == "closed":
        if stdout_path.exists() and stdout_path.stat().st_size:
            raw = stdout_path.read_bytes()
            final.update({"sha256": sha(raw), "bytes": len(raw)})
            try:
                text = json.loads(raw.decode("utf-8-sig")).get("response", "")
            except (ValueError, AttributeError):
                text = None
            if isinstance(text, str) and text.strip():
                final["matches"] = [row["candidate_id"] for row in candidates if any(v["text"] == text for v in row["text_variants"])]
                final["state"] = "matched retained candidate; not counted twice" if final["matches"] else "unmatched final response; manual attribution required"
                if not final["matches"]:
                    candidates.append({"candidate_id": f"cli-final/{sha(text)}", "session_id": None, "response_id": None, "timestamp": run["ended"], "models_observed": [], "attribution": "unmatched_cli_final_requires_review", "text": text, "snippet": text[:500], "decoded_text_utf8_sha256": sha(text), "characters": len(text), "text_variants": [{"text": text, "decoded_text_utf8_sha256": sha(text), "characters": len(text)}], "variant_conflict": False, "transcript_copies": [], "cli_source_path": stdout_path.name, "manual_adjudication": None})
            else:
                final["state"] = "empty final response" if isinstance(text, str) else "invalid or non-string final response"
        else:
            final["state"] = "absent or empty stdout; coverage limited"
    signature = json_sha([{"id": row["candidate_id"], "attribution": row["attribution"], "variants": sorted(v["decoded_text_utf8_sha256"] for v in row["text_variants"]), "conflict": row["variant_conflict"]} for row in candidates])
    return candidates, excluded, final, signature, interval


def researcher_prompt(run):
    path = DOCS / f"{run['label']}.prompt.txt"
    result = {"label": run["label"], "run_state": run["state"], "phase_metadata": run.get("phase", run.get("workflow")), "intended_input_path": path.name, "classification_status": "unreviewed", "kind": None, "clarification_bearing": None, "corrective_intent": None, "reply_to_model_blocking_question": None, "delivery_scope": "intended prompt only; no claim of complete effective delivery, no inference from phase name; separate input audit is authoritative"}
    if not path.exists():
        result["reason"] = "No intended prompt file retained"
        return result
    raw = path.read_bytes()
    result["intended_prompt_sha256"] = sha(raw)
    review = RESEARCHER_PROMPT_REVIEWS.get(run["label"])
    if review and review.get("prompt_sha256") == sha(raw):
        result.update(review)
        result["classification_status"] = "manually reviewed intended prompt"
    elif review:
        result["reason"] = "Intended prompt changed since manual classification; review required"
    return result


def review_run(run, candidates, signature):
    if run["state"] != "closed":
        return "pending_active_interval", None, None
    review = REVIEWED_RUNS.get(run["label"])
    if not review:
        return "manual_review_required", None, None
    if review.get("run_metadata_sha256") != run["metadata_sha256"] or review.get("candidate_signature_sha256") != signature:
        return "changed_metadata_or_text_requires_review", None, None
    decisions = review.get("messages", {})
    if set(decisions) != {row["candidate_id"] for row in candidates} or not all(review.get(key) for key in ("reviewed_at_utc", "reviewer", "coverage_note")):
        return "incomplete_manual_review", None, None
    count, natural = 0, 0
    for row in candidates:
        decision = decisions[row["candidate_id"]]
        classification = decision.get("classification")
        question_count = decision.get("blocking_question_count")
        hashes = {variant["decoded_text_utf8_sha256"] for variant in row["text_variants"]}
        if classification not in {"emitted_main_text", "quoted_or_template_only", "synthetic_cli_notice", "not_main_model_text"} or type(question_count) is not int or question_count < 0 or not decision.get("reason") or decision.get("selected_text_sha256") not in hashes:
            return "invalid_manual_review", None, None
        if classification != "emitted_main_text" and question_count != 0:
            return "invalid_exclusion_count", None, None
        row["manual_adjudication"] = decision
        count += question_count
        natural += classification == "emitted_main_text"
    return "manually_reviewed_retained_interval", count, natural


def render(data):
    lines = ["# Clarification-question audit — Tessl Stage 2", "", data["status"], "", data["count_definition"], "", f"Closed-interval observed count: **{data['closed_runs_observed_blocking_question_count'] if data['closed_runs_observed_blocking_question_count'] is not None else 'not established'}**. Active intervals: **{', '.join(data['pending_run_labels']) or 'none recorded'}**. Unknown counts are not zeros.", "", "| Invocation | State | Candidate texts | Manual review | Observed blocking questions |", "| --- | --- | ---: | --- | ---: |"]
    for run in data["runs"]:
        count = run["tool_requested_blocking_questions_observed"]
        lines.append(f"| {run['label']} | {run['state']} | {len(run['candidate_messages'])} | {run['review_status']} | {count if count is not None else 'pending'} |")
    lines.extend(["", data["limitation"], "", "## Candidate evidence for manual review", "", "Complete emitted text, variants, hashes, timestamps, session/response IDs and source locations are retained in question-audit.json. Content is evidence of what was emitted, not endorsement of technical claims.", ""])
    for run in data["runs"]:
        lines.extend([f"### {run['label']}", "", f"Run metadata SHA-256: `{run['metadata_sha256']}`. Candidate signature: `{run['candidate_signature_sha256']}`.", ""])
        for row in run["candidate_messages"]:
            snippet = row["snippet"].replace("\n", " ")
            lines.extend([f"- Session `{row['session_id']}`, response `{row['response_id']}`, {row['timestamp']}; SHA-256 `{row['decoded_text_utf8_sha256']}`. {row['attribution']}. Snippet: {snippet}"])
        if not run["candidate_messages"]:
            lines.append("No candidate emitted text retained in this observed interval. An active/empty/unreviewed interval has no inferred zero count.")
        for row in run["excluded_candidates"]:
            lines.append(f"- Excluded candidate `{row['candidate_id']}`: {row['exclusion_reason']} (hash `{row['decoded_text_utf8_sha256']}`).")
        lines.append("")
    lines.extend(["## Researcher-origin prompts are separate", "", "Classification is manually bound to each intended prompt hash. Clarification-bearing instructions are not model questions; phase metadata does not establish corrective intent. Effective delivery belongs to the separate input audit.", "", "| Invocation | Review | Kind | Clarification-bearing | Corrective intent |", "| --- | --- | --- | --- | --- |"])
    for row in data["external_researcher_prompts"]:
        lines.append(f"| {row['label']} | {row['classification_status']} | {row['kind'] or 'unreviewed'} | {row['clarification_bearing']} | {row['corrective_intent']} |")
    lines.extend(["", "The collector does not count question-mark characters, infer an absence from headless execution, equate prompts with distinct QA intents, or treat process exit zero as verified implementation success. Tool-call names are a crosscheck only, not emitted natural-language questions.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-candidates", action="store_true", help="Print saved candidate text for manual review")
    args = parser.parse_args()
    observed_at = datetime.now(timezone.utc).isoformat()
    events, sources, warnings, unassigned = collect_records()
    closed, pending = read_runs(observed_at)
    rows = []
    for run in sorted(closed + pending, key=lambda value: (time_key(value["started"]), value["label"])):
        candidates, excluded, final, signature, interval = candidates_for_run(run, events)
        status, count, natural = review_run(run, candidates, signature)
        names = sorted({name for event in interval for name in event["tool_names"]})
        rows.append({"label": run["label"], "state": run["state"], "started": run["started"], "ended": run.get("ended"), "observed_until": run.get("observed_until"), "exit_code": run.get("exit_code"), "metadata_path": run["metadata_path"], "metadata_sha256": run["metadata_sha256"], "main_model": run.get("requested_model", DEFAULT_MAIN_MODEL), "review_status": status, "candidate_signature_sha256": signature, "natural_language_message_count": natural, "tool_requested_blocking_questions_observed": count, "candidate_messages": candidates, "excluded_candidates": excluded, "cli_final_response": final, "recorded_main_response_count": len({(e['session_id'], e['response_id']) for e in interval if e['model'] == run.get('requested_model', DEFAULT_MAIN_MODEL)}), "observed_tool_names": names, "interactive_question_tool_names_observed": [name for name in names if name in {"ask_user", "ask_user_question", "request_user_input"}], "manual_interval_review": REVIEWED_RUNS.get(run["label"]), "coverage": "retained timestamp-bounded text only; original/archive copies deduplicated by session/response identity before counting. Failed, empty, unrecorded or active output does not prove an absolute absence of questions."})
    reviewed = [row for row in rows if row["state"] == "closed" and row["review_status"] == "manually_reviewed_retained_interval"]
    unreviewed = [row["label"] for row in rows if row["state"] == "closed" and row["review_status"] != "manually_reviewed_retained_interval"]
    # A malformed/truncated source cannot silently preserve a prior zero. This
    # also covers a partially written active line; rerun after it is complete.
    established = bool(closed) and not unreviewed and not unassigned and not warnings
    count = sum(row["tool_requested_blocking_questions_observed"] for row in reviewed) if established else None
    prompts = [researcher_prompt(run) for run in sorted(closed + pending, key=lambda value: value["label"])]
    status = "Pending: no closed invocation has been manually audited." if not closed else "Manual adjudication required before closed-run question totals can be established." if not established else "Closed retained intervals manually audited; active intervals remain pending." if pending else "Closed retained intervals manually audited."
    data = {"audited_at_utc": observed_at, "status": status, "tool": "Tessl Stage 2", "count_definition": "A blocking clarification question is emitted main-model natural-language text requesting missing user/researcher input before proceeding. Count requests, not punctuation; quoted/template-only questions are excluded by manual adjudication.", "closed_run_labels": [r["label"] for r in closed], "pending_run_labels": [r["label"] for r in pending], "manual_review_required_closed_labels": unreviewed, "closed_runs_observed_blocking_question_count": count, "all_started_runs_observed_blocking_question_count": count if established and not pending else None, "reviewed_unique_natural_language_messages": sum(row["natural_language_message_count"] for row in reviewed) if reviewed else None, "runs": rows, "source_files": sources, "source_read_warnings": warnings, "unassigned_text_requires_review": unassigned, "interval_definition": "Timezone-qualified start/end nanoseconds are applied before deduplication, including resumed history appended to an older session. Active intervals end at this audit's observation timestamp. Timestamped embedded/replayed messages retain their original timestamp.", "deduplication": "session ID plus response ID; every text variant and source-copy location retained. Longer prefix-complete text is displayed, conflicting variants require an explicit reviewed selected hash. Matching completed CLI response is never counted again.", "exclusions": ["thoughts/reasoning/signatures", "function/tool calls, arguments and results", "user/native-template text", "exact unlabeled/no-token synthetic CLI notices", "explicitly labeled auxiliary-model text"], "external_researcher_prompts": prompts, "external_researcher_prompt_summary": {"scope": "one intended prompt per recorded invocation; manually reviewed classification only, not input-delivery proof or count of QA intents", "closed_manually_classified_clarification_bearing_attempts": sum(p["run_state"] == "closed" and p["clarification_bearing"] is True for p in prompts), "pending_manually_classified_clarification_bearing_attempts": sum(p["run_state"] == "pending" and p["clarification_bearing"] is True for p in prompts), "unclassified_labels": [p["label"] for p in prompts if p["classification_status"] == "unreviewed"]}, "limitation": "Unknown/unreviewed counts remain null. Active sessions are pending, even when no natural-language text has yet been retained. A zero observed count requires a hash-bound manual review of a closed retained interval and cannot establish that no unrecorded question exists. This audit does not assess implementation correctness or input delivery."}
    (DOCS / "question-audit.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOCS / "question-audit.md").write_text(render(data), encoding="utf-8")
    if args.show_candidates:
        print(json.dumps([{"label": row["label"], "candidates": row["candidate_messages"]} for row in rows], ensure_ascii=False, indent=2))
    print(json.dumps({"closed_runs": len(closed), "pending": data["pending_run_labels"], "manual_review_required": unreviewed, "observed_blocking_questions": count, "source_files": len(sources), "unassigned_text_candidates": len(unassigned)}))
    return 2 if unreviewed or unassigned or warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
