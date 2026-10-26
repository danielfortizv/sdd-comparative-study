"""Measure Tessl Stage 2 from its own Stage 1 and retained CLI evidence."""

from __future__ import annotations

import difflib
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
BASE = CASE / "Etapa 1" / "Tessl"
CURRENT = STAGE / "Tessl"
DOCS = CURRENT / "docs"
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
SPEC_EXTS = {".md", ".json"}
EXCLUDE = {"node_modules", "venv", ".venv", "dist", "build", "coverage", "__pycache__", ".pytest_cache", "docs", ".sonar", ".sonar-user-home"}
RUN_CATEGORIES = {"01-specify": ("initial_specification", "Gemini-authored requirements using actual Tessl MCP/plugin context; no native Tessl generator command is claimed.")}
QA_INTENTS = {}


def load_classifications():
    global RUN_CATEGORIES, QA_INTENTS
    path = DOCS / "run-classifications.json"
    if path.exists():
        values = json.loads(path.read_text(encoding="utf-8-sig"))
        RUN_CATEGORIES = {label: (item["category"], item["reason"]) for label, item in values.items()}
        QA_INTENTS = {label: {"id": item.get("qa_intent_id"), "retry_of": item.get("retry_of"), "resumed": item.get("resumed", False)} for label, item in values.items()}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def collect(root: Path, folders: list[str], extensions: set[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for folder in folders:
        start = root / folder
        if not start.exists():
            continue
        for path in start.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions and not any(part in EXCLUDE for part in path.relative_to(start).parts):
                result[path.relative_to(root).as_posix()] = path
    return result


def counts(paths: dict[str, Path]) -> dict:
    per_file = {}
    for name, path in sorted(paths.items()):
        value = read(path)
        lines = value.splitlines()
        per_file[name] = {
            "lines": len(lines),
            "nonblank_lines": sum(bool(line.strip()) for line in lines),
            "characters": len(value),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            "modified_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
    total_lines = sum(item["lines"] for item in per_file.values())
    return {
        "files": len(per_file),
        "lines": total_lines,
        "nonblank_lines": sum(item["nonblank_lines"] for item in per_file.values()),
        "characters": sum(item["characters"] for item in per_file.values()),
        "lines_per_file": round(total_lines / len(per_file), 2) if per_file else 0,
        "per_file": per_file,
    }


def diff(before: dict[str, Path], after: dict[str, Path]) -> dict:
    names = []
    added = removed = 0
    for name in sorted(set(before) | set(after)):
        left = read(before[name]).splitlines() if name in before else []
        right = read(after[name]).splitlines() if name in after else []
        if left == right:
            continue
        names.append(name)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
            if tag in {"delete", "replace"}:
                removed += i2 - i1
            if tag in {"insert", "replace"}:
                added += j2 - j1
    before_characters = sum(len(read(path)) for path in before.values())
    after_characters = sum(len(read(path)) for path in after.values())
    return {
        "changed_files": names, "changed_file_count": len(names),
        "added_lines": added, "removed_lines": removed,
        "net_lines": added - removed,
        "before_characters": before_characters,
        "after_characters": after_characters,
        "net_characters": after_characters - before_characters,
        "character_delta_definition": "net change in total decoded Unicode text length, after BOM removal and LF normalization; not cumulative edit volume or an added/removed-character operation count",
    }


def timestamp(raw: str) -> datetime:
    raw = re.sub(r"(\.\d{6})\d+", r"\1", raw.replace("Z", "+00:00"))
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def complete_sum(values) -> int | None:
    values = list(values)
    return sum(int(value) for value in values) if all(value is not None for value in values) else None


def transcript_catalog() -> dict[str, dict]:
    """Keep one final response record per ID across originals and archive copies."""
    events: dict[str, dict] = {}
    for folder in (DOCS / "gemini-home", DOCS / "transcripts-archive"):
        if not folder.exists():
            continue
        for transcript in sorted(folder.rglob("*.jsonl")):
            for line in transcript.open(encoding="utf-8-sig", errors="replace"):
                try:
                    event = json.loads(line)
                    if event.get("type") != "gemini" or not event.get("tokens") or not event.get("id"):
                        continue
                    when = timestamp(event["timestamp"])
                    identity = event["id"]
                    path = transcript.relative_to(DOCS).as_posix()
                    existing = events.get(identity)
                    if existing is None:
                        events[identity] = {"event": event, "when": when, "paths": {path}}
                    else:
                        existing["paths"].add(path)
                        # A JSONL may update an existing response. Prefer its latest,
                        # most complete record; duplicate archive snapshots add no count.
                        score = (when, int(event["tokens"].get("total") or 0), len(line))
                        old = existing["event"]
                        old_score = (existing["when"], int(old["tokens"].get("total") or 0), len(json.dumps(old, separators=(",", ":"))))
                        if score >= old_score:
                            existing.update(event=event, when=when)
                except (ValueError, KeyError, TypeError):
                    continue
    return events


def recorded_responses(row: dict, catalog: dict[str, dict]) -> dict:
    if row.get("model_started") is False:
        return {"recorded_response_count": 0, "recorded_response_models": [], "transcript_paths": [], "transcript_coverage": "model did not start"}
    if not row.get("started") or not row.get("ended"):
        return {"recorded_response_count": None, "recorded_response_models": [], "transcript_paths": [], "transcript_coverage": "run interval unavailable"}
    start, end = timestamp(row["started"]), timestamp(row["ended"])
    entries = [entry for entry in catalog.values() if start <= entry["when"] <= end]
    if not entries:
        return {"recorded_response_count": None, "recorded_response_models": [], "transcript_paths": [], "transcript_coverage": "no token-bearing response records observed in run interval"}
    return {
        "recorded_response_count": len(entries),
        "recorded_response_models": sorted({entry["event"].get("model", "unknown") for entry in entries}),
        "transcript_paths": sorted({path for entry in entries for path in entry["paths"]}),
        "transcript_coverage": "observed token-bearing JSONL responses deduplicated by response ID; does not count failed API attempts or unrecorded auxiliary calls",
        "events": [entry["event"] for entry in entries],
    }


def stats_for_run(row: dict, catalog: dict[str, dict]) -> dict:
    response_stats = recorded_responses(row, catalog)
    response_events = response_stats.pop("events", [])
    resumed_scope = None
    if row.get("model_started") is False:
        return {"source": "local launcher failure before Gemini/model startup", "models": [], "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "thought_tokens": 0, "api_requests": 0, "api_errors": 0, "api_successful_requests": 0, "model_started_observed": False, **response_stats}
    stdout = DOCS / f"{row['label']}.stdout.json"
    if stdout.exists() and stdout.stat().st_size:
        try:
            models = json.loads(read(stdout)).get("stats", {}).get("models", {})
            if models:
                if row.get("resume_requested") or QA_INTENTS.get(row["label"], {}).get("resumed"):
                    main_name = row.get("requested_model", "gemini-3.5-flash")
                    main = models.get(main_name, {})
                    observed = [event for event in response_events if event.get("model") == main_name]
                    unknown_model_events = [event for event in response_events if not event.get("model")]
                    single_model_attribution = set(models) == {main_name} and all(event.get("model") in {None, main_name} for event in response_events)
                    if single_model_attribution:
                        # Empty terminal response records can omit model. Retain
                        # that omission in raw coverage, and validate the entire
                        # single-model interval before attributing CLI counters.
                        observed += unknown_model_events
                    comparisons = {
                        "input_tokens": (main.get("tokens", {}).get("prompt"), complete_sum(event["tokens"].get("input") for event in observed)),
                        "cached_tokens": (main.get("tokens", {}).get("cached"), complete_sum(event["tokens"].get("cached") for event in observed)),
                        "output_tokens": (main.get("tokens", {}).get("candidates"), complete_sum(event["tokens"].get("output") for event in observed)),
                        "thought_tokens": (main.get("tokens", {}).get("thoughts"), complete_sum(event["tokens"].get("thoughts") for event in observed)),
                    }
                    requests, errors = main.get("api", {}).get("totalRequests"), main.get("api", {}).get("totalErrors")
                    successful = requests - errors if requests is not None and errors is not None else None
                    matched = bool(observed) and all(left is not None and left == right for left, right in comparisons.values()) and successful == len(observed)
                    resumed_scope = {
                        "status": "main CLI counters match current invocation interval" if matched else "CLI scope not validated; main JSONL fallback only",
                        "retry_of": QA_INTENTS.get(row["label"], {}).get("retry_of"),
                        "main_model": main_name, "main_recorded_responses": len(observed),
                        "jsonl_records_missing_model": len(unknown_model_events),
                        "model_attribution": "single CLI-reported model; unlabeled interval records included only after exact token/count comparison and absence of conflicting model labels" if unknown_model_events and single_model_attribution else "explicit JSONL model labels",
                        "main_cli_successful_requests": successful,
                        "token_comparisons": {key: {"cli": value[0], "run_interval_jsonl": value[1]} for key, value in comparisons.items()},
                        "definition": "Response IDs are deduplicated across resumed original/archive files and bounded by this run's start/end; prior-attempt responses are excluded. Only matching main counters permit adding completed CLI process totals. Auxiliary roles remain CLI-reported rather than independently present in main JSONL.",
                    }
                    if not matched:
                        models = {}
                if not models:
                    raise ValueError("Resumed CLI counters cannot be attributed to this invocation")
                api_by_model = {}
                for name, model in models.items():
                    api = model.get("api", {})
                    requests, errors = api.get("totalRequests"), api.get("totalErrors")
                    api_by_model[name] = {
                        "api_requests": requests,
                        "api_errors": errors,
                        "api_successful_requests": requests - errors if requests is not None and errors is not None else None,
                        "roles": sorted(model.get("roles", {})),
                    }
                def api_sum(key: str):
                    values = [model[key] for model in api_by_model.values()]
                    return sum(values) if all(value is not None for value in values) else None
                return {
                    "source": "Gemini CLI JSON stats",
                    "models": sorted(models),
                    "input_tokens": complete_sum(m.get("tokens", {}).get("prompt") for m in models.values()),
                    "cached_tokens": complete_sum(m.get("tokens", {}).get("cached") for m in models.values()),
                    "output_tokens": complete_sum(m.get("tokens", {}).get("candidates") for m in models.values()),
                    "thought_tokens": complete_sum(m.get("tokens", {}).get("thoughts") for m in models.values()),
                    "api_requests": api_sum("api_requests"),
                    "api_errors": api_sum("api_errors"),
                    "api_successful_requests": api_sum("api_successful_requests"),
                    "api_by_model": api_by_model,
                    "api_scope": "all models and roles present in completed CLI statistics; requests include failed attempts",
                    "model_started_observed": True,
                    "resumed_scope_verification": resumed_scope,
                    **response_stats,
                }
        except (ValueError, UnicodeError):
            pass
    if response_events:
        if resumed_scope is None and (row.get("resume_requested") or QA_INTENTS.get(row["label"], {}).get("resumed")):
            main_name = row.get("requested_model", "gemini-3.5-flash")
            resumed_scope = {
                "status": "no completed CLI counters; main JSONL interval only",
                "retry_of": QA_INTENTS.get(row["label"], {}).get("retry_of"),
                "main_model": main_name,
                "main_recorded_responses": sum(event.get("model") == main_name for event in response_events),
                "main_cli_successful_requests": None,
                "token_comparisons": None,
                "definition": "No completed CLI API/model statistics were saved. Response IDs are deduplicated across resumed original/archive files and bounded by this run's start/end, excluding prior-attempt responses. Only observed main JSONL tokens are reported; API attempts/errors/successes and unrecorded auxiliary usage remain unknown.",
            }
        return {
            "source": "Gemini CLI JSONL responses, deduplicated by response ID and run interval",
            "models": response_stats["recorded_response_models"],
            "input_tokens": complete_sum(event["tokens"].get("input") for event in response_events),
            "cached_tokens": complete_sum(event["tokens"].get("cached") for event in response_events),
            "output_tokens": complete_sum(event["tokens"].get("output") for event in response_events),
            "thought_tokens": complete_sum(event["tokens"].get("thoughts") for event in response_events),
            "api_requests": None, "api_errors": None, "api_successful_requests": None,
            "api_scope": "unknown: JSONL responses cannot establish failed attempts or auxiliary API totals",
            "model_started_observed": True,
            "resumed_scope_verification": resumed_scope,
            **response_stats,
        }
    return {"source": "unavailable", "models": [], "input_tokens": None, "cached_tokens": None, "output_tokens": None, "thought_tokens": None, "api_requests": None, "api_errors": None, "api_successful_requests": None, "model_started_observed": None, **response_stats}


def process_outcome(row: dict) -> str:
    if "exit_code" not in row:
        return "open"
    if row["exit_code"] == 0:
        return "closed_exit_zero"
    if row["exit_code"] is None:
        return "closed_outcome_unknown"
    return "closed_failed_or_interrupted"


def classification(row: dict) -> dict:
    category, reason = RUN_CATEGORIES.get(row["label"], ("unclassified", "Researcher classification pending; do not infer a correction category from workflow alone."))
    intent = QA_INTENTS.get(row["label"], {})
    return {
        "category": category, "reason": reason,
        "external_postimplementation_correction": category == "postimplementation_external_correction",
        "qa_intent_id": intent.get("id"), "retry_of": intent.get("retry_of"),
        "process_outcome": process_outcome(row),
        "outcome_definition": "closed means the invocation ended, including failure/interruption; exit-zero means process success only, not independently verified correction/acceptance success",
    }


def cli_tool_actions(row: dict) -> dict:
    path = DOCS / f"{row['label']}.stdout.json"
    if path.exists() and path.stat().st_size:
        try:
            tools = json.loads(read(path)).get("stats", {}).get("tools")
            if tools:
                return {
                    "source": "completed CLI stats.tools",
                    "total_calls": tools.get("totalCalls"),
                    "successful_calls": tools.get("totalSuccess"),
                    "failed_calls": tools.get("totalFail"),
                    "by_tool": {name: {key: value.get(key) for key in ("count", "success", "fail")} for name, value in tools.get("byName", {}).items()},
                    "scope": "tool execution statistics inside one external invocation; includes reads and other actions, not just code changes or Sonar scans; never counted as additional external correction prompts. A successful tool wrapper does not establish a shell command/test pass; inspect raw exit codes and logs.",
                }
        except (ValueError, UnicodeError):
            pass
    return {"source": "unavailable", "total_calls": None, "successful_calls": None, "failed_calls": None}


def terminal_failure(row: dict) -> dict | None:
    path = DOCS / f"{row['label']}.stderr.txt"
    if row.get("exit_code") == 429 and path.exists():
        output = read(path)
        if "429" in output and "RESOURCE_EXHAUSTED" in output:
            return {
                "http_status": 429, "kind": "RESOURCE_EXHAUSTED",
                "evidence": path.relative_to(DOCS).as_posix(),
                "scope": "at least one observed terminal HTTP error; not a complete API-attempt/error aggregate and not added as an invented aggregate count",
            }
    if row.get("exit_code") == 1 and path.exists() and "fetch failed sending request" in read(path):
        return {
            "http_status": None, "kind": "network_fetch_failed",
            "evidence": path.relative_to(DOCS).as_posix(),
            "scope": "observed terminal network failure; no HTTP status or complete API-attempt/error aggregate was saved, so no invented aggregate error count is added",
        }
    return None


def correction_counts(runs: list[dict], open_runs: list[dict]) -> dict:
    all_rows = [{**row, "closed": True} for row in runs] + [{**row, "closed": False} for row in open_runs]
    categories = {}
    for row in all_rows:
        key = row["classification"]["category"]
        bucket = categories.setdefault(key, {"closed_attempts": 0, "closed_exit_zero_attempts": 0, "closed_failed_or_interrupted_attempts": 0, "closed_outcome_unknown_attempts": 0, "open_attempts": 0, "model_observed_closed_prompts": 0, "labels": []})
        bucket["closed_attempts" if row["closed"] else "open_attempts"] += 1
        outcome = row["classification"]["process_outcome"]
        if outcome != "open":
            bucket[outcome + "_attempts"] += 1
        if row["closed"] and row["tokens"]["model_started_observed"] is True:
            bucket["model_observed_closed_prompts"] += 1
        bucket["labels"].append(row["label"])
    corrections = [row for row in all_rows if row["classification"]["external_postimplementation_correction"]]
    intents = {}
    for row in corrections:
        intent = row["classification"].get("qa_intent_id")
        if intent:
            item = intents.setdefault(intent, {"attempt_labels": [], "closed_exit_zero_labels": [], "closed_failed_or_interrupted_labels": [], "open_labels": []})
            item["attempt_labels"].append(row["label"])
            outcome = row["classification"]["process_outcome"]
            if outcome in {"closed_exit_zero", "closed_failed_or_interrupted", "open"}:
                item[outcome + "_labels"].append(row["label"])
    return {
        "classification_version": "researcher-reviewed v2; external attempts, distinct QA intents, retries and process outcomes are separate",
        "by_category": categories,
        "postimplementation_external_correction_prompts_started": len(corrections),
        "postimplementation_external_correction_prompts_closed": sum(row["closed"] for row in corrections),
        "postimplementation_external_correction_prompts_open": sum(not row["closed"] for row in corrections),
        "postimplementation_external_correction_prompts_exit_zero": sum(row["classification"]["process_outcome"] == "closed_exit_zero" for row in corrections),
        "postimplementation_external_correction_prompts_failed_or_interrupted": sum(row["classification"]["process_outcome"] == "closed_failed_or_interrupted" for row in corrections),
        "distinct_qa_intents_started": len(intents),
        "qa_intents": intents,
        "postimplementation_external_correction_labels": [row["label"] for row in corrections],
        "unclassified_labels": [row["label"] for row in all_rows if row["classification"]["category"] == "unclassified"],
        "scope": "External correction attempts are separate from initial implementation, preimplementation spec clarification, launcher retries, and automated within-session edits/scans. A retry can share one QA intent. Closed includes failed attempts; exit-zero does not establish functional acceptance. Started counts include open metadata. Unknown future labels remain unclassified until reviewed.",
    }



def integration_observations(row: dict, catalog: dict) -> dict:
    """Actual recorded calls, not tool documentation or claims of activation."""
    if not row.get("started") or not row.get("ended"):
        return {"coverage": "closed interval unavailable", "total_deduplicated_calls": None}
    start, end = timestamp(row["started"]), timestamp(row["ended"])
    calls = {}
    for entry in catalog.values():
        if not start <= entry["when"] <= end:
            continue
        event = entry["event"]
        observed = list(event.get("toolCalls", []))
        content = event.get("content", [])
        if isinstance(content, list):
            observed += [part["functionCall"] for part in content if isinstance(part, dict) and isinstance(part.get("functionCall"), dict)]
        for call in observed:
            name = call.get("name", "unknown")
            identity = call.get("id") or (event["id"], name, json.dumps(call.get("args", {}), sort_keys=True))
            if identity in calls:
                continue
            arguments = call.get("args", {})
            context_read = name in {"read_file", "read_many_files"} and any(".tessl" in str(value).lower() for value in arguments.values()) if isinstance(arguments, dict) else False
            result = call.get("result")
            calls[identity] = {"name": name, "call_id": call.get("id"), "response_id": event["id"], "timestamp": call.get("timestamp", event["timestamp"]), "wrapper_status": call.get("status", "not_recorded"), "result_recorded": result is not None, "result_json_utf8_sha256": hashlib.sha256(json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest().upper() if result is not None else None, "tessl_named_call": "tessl" in name.lower(), "vendored_context_read": context_read, "transcript_copies": sorted(entry["paths"])}
    items = list(calls.values())
    return {"coverage": "actual recorded call IDs inside the closed run interval, deduplicated across original/archive snapshots", "total_deduplicated_calls": len(items), "observed_tool_names": sorted({item["name"] for item in items}), "tessl_named_call_count": sum(item["tessl_named_call"] for item in items), "vendored_context_read_count": sum(item["vendored_context_read"] for item in items), "calls": items, "limitation": "A call name or successful wrapper alone does not prove plugin activation, wrapped command success or useful returned context. Raw retained outputs are authoritative; unavailable/unrecorded calls are not inferred failures."}


def prepare_corpus(label, stage2_folder, unclosed):
    if not re.fullmatch(r"[a-z0-9-]+", label):
        raise ValueError("Use a lowercase corpus label")
    if label == "final" and unclosed:
        raise ValueError("Final corpus requires every invocation closed")
    snapshot = DOCS / label / "files"
    source_root = snapshot if snapshot.exists() else CURRENT
    markdown = collect(source_root, [stage2_folder], {".md"})
    if not markdown:
        raise ValueError("No Tessl Stage 2 native Markdown found")
    destination = DOCS / "bertopic-corpus" / label
    if destination.exists():
        raise FileExistsError("Refusing to replace a corpus snapshot")
    destination.mkdir(parents=True)
    items, pieces = [], []
    for name, path in sorted(markdown.items()):
        value = read(path)
        out = destination / "by-file" / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(value, encoding="utf-8", newline="")
        items.append({"source": name, "corpus_path": out.relative_to(destination).as_posix(), "source_byte_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(), "normalized_utf8_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest().upper(), "lines": len(value.splitlines()), "characters": len(value)})
        pieces.append(value)
    unified = "\n\n".join(pieces)
    (destination / "unified.md").write_text(unified, encoding="utf-8", newline="")
    manifest = {"label": label, "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "status": "source snapshot after closed invocations; final acceptance must be verified separately" if label == "final" else "intermediate source snapshot; not final", "source_root": str(source_root), "scope": "Tessl specs/stage2/*.md recursively only; copied Stage 1 specs, JSON, researcher docs, transcripts, plugin context and application excluded", "normalization": "UTF-8 without BOM; LF; complete files sorted by path and joined by two LF; no inserted labels, translation, chunking or topic modelling", "analysis_status": "corpus preparation only; no BERTopic model or comparison score", "files": items, "markdown_file_count": len(items), "unified_characters": len(unified), "unified_utf8_sha256": hashlib.sha256(unified.encode("utf-8")).hexdigest().upper()}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return {"label": label, "path": str(destination), "markdown_file_count": len(items), "status": manifest["status"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-corpus")
    args = parser.parse_args()
    load_classifications()
    now = datetime.now(timezone.utc)
    frozen = json.loads(read(DOCS / "baseline-metrics.json"))
    stage2_folder = "specs/stage2"
    base_source = collect(BASE, ["backend", "frontend"], SOURCE_EXTS)
    current_source = collect(CURRENT, ["backend", "frontend"], SOURCE_EXTS)
    spec_names = sorted(frozen["specification"]["per_file"])
    base_spec = {name: BASE/name for name in spec_names if (BASE/name).exists()}
    copied_spec = {name: CURRENT/name for name in spec_names if (CURRENT/name).exists()}
    stage2_spec = collect(CURRENT, [stage2_folder], SPEC_EXTS)
    dep_names = sorted(set([item["path"] for item in frozen["dependency_manifests"]] + ["backend/requirements.txt", "backend/requirements-dev.txt", "backend/poetry.lock", "backend/uv.lock"]))
    before_deps = {name: BASE/name for name in dep_names if (BASE/name).exists()}
    after_deps = {name: CURRENT/name for name in dep_names if (CURRENT/name).exists()}
    integration_names = ["tessl.json", ".gemini/settings.json", ".tessl/RULES.md"]
    catalog = transcript_catalog()
    runs = []
    for path in sorted(DOCS.glob("*.run.json")):
        row = json.loads(read(path))
        runs.append({**row, "classification": classification(row), "terminal_failure_observation": terminal_failure(row), "cli_tool_actions": cli_tool_actions(row), "integration_observations": integration_observations(row, catalog), "tokens": stats_for_run(row, catalog)})
    closed = {row["label"] for row in runs}
    open_runs = []
    for path in sorted(DOCS.glob("*.started.json")):
        if path.name.removesuffix(".started.json") in closed:
            continue
        row = json.loads(read(path))
        observed = any(timestamp(row["started"]) <= item["when"] <= now for item in catalog.values())
        open_runs.append({**row, "classification": classification(row), "model_started_observed": True if observed else None})
    unclosed = [row["label"] for row in open_runs]
    source_before, source_after = counts(base_source), counts(current_source)
    inherited_before, inherited_after = counts(base_spec), counts(copied_spec)
    baseline_hash_mismatches = [name for name,item in frozen["source"]["per_file"].items() if name not in source_before["per_file"] or source_before["per_file"][name]["sha256"] != item["sha256"]]
    baseline_hash_mismatches += [name for name,item in frozen["specification"]["per_file"].items() if name not in inherited_before["per_file"] or inherited_before["per_file"][name]["sha256"] != item["sha256"]]
    known_duration = round(sum(row.get("duration_seconds") or 0 for row in runs),3)
    requirement_file = CURRENT / stage2_folder / "requirements.md"
    requirements = read(requirement_file) if requirement_file.exists() else ""
    identifiers = sorted(set(re.findall(r"\b(?:S2[-_]Req[-_]\d+|S2[-_]\d+|Req[-_]\d+|FR[-_]\d+)\b", requirements)))
    result = {"researcher_created": True, "tool": "Tessl", "measured_at_utc": now.isoformat(), "feature_directory": stage2_folder,
        "source_scope": "backend/frontend .py/.ts/.tsx/.js/.jsx/.css/.html including tests and source-like config; dependencies/builds/coverage/caches/docs excluded", "source_attribution_scope": "own inherited Tessl Stage 1 plus Gemini-generated app/test changes; researcher helpers/evidence excluded; text counts alone do not prove authorship", "spec_scope": "original Tessl specs/requirements.md and specs/session_notes.md separately from new specs/stage2 Markdown/JSON; no other tool feature content", "text_counting_rules": "UTF-8 BOM removal and LF normalization; physical lines use splitlines; original byte hashes retained; line deltas compare logical lines; net characters are state-size differences, not cumulative edit volume", "density_definition": "physical lines / files, rounded to two decimals; not a quality or scalability score", "snapshot_scope": "only closed *.run.json intervals contribute usage/time/attempt totals; open metadata separate; source/spec counts reflect collection time", "unclosed_invocation_labels": unclosed, "open_invocation_metadata": open_runs,
        "source_baseline": source_before, "source_current": source_after, "source_change": diff(base_source,current_source), "spec_stage1": inherited_before, "spec_stage1_copy": inherited_after, "spec_stage1_copy_change": diff(base_spec,copied_spec), "spec_stage2": counts(stage2_spec), "spec_stage2_change_from_empty": diff({},stage2_spec), "stage2_spec_delta_scope": "new specs/stage2 measured against empty directory; original inherited native docs measured separately", "dependency_manifests_baseline": counts(before_deps), "dependency_manifests_current": counts(after_deps), "dependency_manifests_change": diff(before_deps,after_deps), "integration_manifests_current": counts({name:CURRENT/name for name in integration_names if (CURRENT/name).exists()}),
        "baseline_integrity": {"reference":"baseline-metrics.json", "original_stage1_hash_mismatches":baseline_hash_mismatches, "original_stage1_unchanged":not baseline_hash_mismatches}, "stage2_requirement_ids":identifiers, "stage2_identifier_scope":"unique identifier-pattern candidates in Stage 2 requirements.md; not independently adjudicated atomic-requirement or acceptance counts", "runs":runs,
        "invocation_attempts":len(runs), "model_invocations":sum(row["tokens"]["model_started_observed"] is True for row in runs), "closed_process_outcomes":{key:sum(row["classification"]["process_outcome"]==key for row in runs) for key in ["closed_exit_zero","closed_failed_or_interrupted","closed_outcome_unknown"]}, "runs_with_unknown_model_start":[row["label"] for row in runs if row["tokens"]["model_started_observed"] is None], "correction_counts":correction_counts(runs,open_runs),
        "known_duration_seconds":known_duration, "known_model_invocation_duration_seconds":round(sum(row.get("duration_seconds") or 0 for row in runs if row["tokens"]["model_started_observed"] is True),3), "total_duration_seconds":known_duration, "prompt_count":len(runs), "prompt_count_note":"compatibility alias for closed launcher attempts, including proven pre-model failures; not actual model prompts", "duration_scope":"known instrumented CLI invocation duration, including failed attempts; unknown durations and all external researcher work excluded", "runs_with_unknown_duration":[row["label"] for row in runs if row.get("duration_seconds") is None],
        "observed_tokens":{key:sum(row["tokens"].get(key) or 0 for row in runs) for key in ["input_tokens","cached_tokens","output_tokens","thought_tokens"]}, "runs_with_unknown_token_fields":{key:[row["label"] for row in runs if row["tokens"].get(key) is None] for key in ["input_tokens","cached_tokens","output_tokens","thought_tokens"]}, "token_scope":"completed CLI stats include all reported model/roles; JSONL fallback only observed responses. Input means prompt including cache; candidates/thoughts separate; unknowns not imputed", "usage_provenance_limit":"Gemini CLI experiment including reported auxiliary roles only; excludes Codex/researcher orchestration, reviews, helper authoring, setup, Drive/UI and independent verification. Not total project tokens/cost", "known_api_totals":{key:sum(row["tokens"].get(key) or 0 for row in runs) for key in ["api_requests","api_errors","api_successful_requests"]}, "api_totals_scope":"known completed CLI counters and proven pre-model zeroes; unknown intervals excluded", "runs_without_api_stats":[row["label"] for row in runs if row["tokens"]["api_requests"] is None], "observed_terminal_api_failures":[{"label":row["label"],**row["terminal_failure_observation"]} for row in runs if row["terminal_failure_observation"]], "recorded_response_count":sum(row["tokens"].get("recorded_response_count") or 0 for row in runs), "recorded_response_scope":"token-bearing JSONL response IDs deduplicated across originals/archives and bounded by each run interval; distinct from API attempts and may omit auxiliary responses", "runs_without_recorded_response_stats":[row["label"] for row in runs if row["tokens"]["recorded_response_count"] is None], "runs_without_token_stats":[row["label"] for row in runs if row["tokens"]["source"]=="unavailable"],
        "researcher_setup_incident_files":[name for name in ["baseline-shared-python-failed-result.json","baseline-shared-python-failed-coverage.log","baseline-python-setup-commands.json"] if (DOCS/name).exists()], "researcher_setup_scope":"environment setup/replication and its failures are not Gemini model invocation attempts or token usage", "integration_scope":"actual Tessl MCP/plugin context workflow; no native Tessl spec/build generator command is claimed"}
    config_path=DOCS/"measurement-config.json"
    if config_path.exists():
        config=json.loads(read(config_path));label=config.get("initial_implementation_snapshot")
        if label and re.fullmatch(r"[a-z0-9-]+",label) and (DOCS/label/"files").exists():
            root=DOCS/label/"files"
            result["qa_change_from_initial_implementation"]={"snapshot":label,"source":diff(collect(root,["backend","frontend"],SOURCE_EXTS),current_source),"spec_stage2":diff(collect(root,[stage2_folder],SPEC_EXTS),stage2_spec),"scope":"current state vs explicitly configured own initial implementation snapshot; includes open changes when present, not cumulative edit volume"}
    if args.prepare_corpus:
        result["corpus_preparation"]=prepare_corpus(args.prepare_corpus,stage2_folder,unclosed)
    result["corpus_snapshots"]=[{"label":json.loads(read(path))["label"],"manifest":path.relative_to(DOCS).as_posix()} for path in sorted((DOCS/"bertopic-corpus").glob("*/manifest.json"))]
    (DOCS/"metrics.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ["tool","invocation_attempts","model_invocations","unclosed_invocation_labels","source_change","spec_stage1_copy_change","known_duration_seconds","observed_tokens","known_api_totals","runs_without_api_stats","recorded_response_count","baseline_integrity"]},indent=2))


if __name__ == "__main__":
    main()
