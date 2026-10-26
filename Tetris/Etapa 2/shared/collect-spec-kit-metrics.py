"""Measure Spec Kit Stage 2 from copied Stage 1 sources and retained CLI runs."""

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
BASE = CASE / "Etapa 1" / "Spec Kit"
CURRENT = STAGE / "Spec Kit"
DOCS = CURRENT / "docs"
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
SPEC_EXTS = {".md", ".json"}
EXCLUDE = {"node_modules", "venv", ".venv", "dist", "build", "coverage", "__pycache__", ".pytest_cache", "docs", ".sonar", ".sonar-user-home"}
RUN_CATEGORIES = {
    "01-specify": ("initial_specification_attempt", "Initial native specification invocation; arguments were lost by the launcher."),
    "02-specify-retry": ("specification_launcher_retry", "Retry of specification after argument loss; not a post-implementation correction."),
    "03-contract-clarification": ("preimplementation_specification_correction", "Explicit contract/latency clarification before application generation."),
    "04-plan": ("native_planning", "Native plan generation before implementation."),
    "05-tasks": ("native_task_generation", "Initial task generation; appended arguments were lost."),
    "06-tasks-full-arguments": ("task_launcher_retry", "Attempt to preserve multiline arguments; failed before model startup."),
    "07-tasks-native-expanded": ("task_launcher_retry", "Task-generation retry with complete native arguments; preimplementation alignment."),
    "08-implement": ("initial_implementation", "Initial implementation invocation; automated actions within this run are not separate external correction prompts."),
    "09-qa-correction": ("postimplementation_external_correction", "First explicit external QA correction prompt after generation 08."),
    "10-qa-race-correction": ("postimplementation_external_correction", "Second explicit external QA correction prompt for remaining restart races and targeted acceptance gaps after correction 09."),
    "11-qa-timer-ownership": ("postimplementation_external_correction", "Third explicit external QA correction prompt for timer ownership, deterministic race barriers and complete route/UI assertions after correction 10."),
    "12-qa-timer-retry": ("postimplementation_external_correction", "Explicit resumed retry of failed attempt 11 after terminal Vertex 429; same QA-3 intent, not a fourth distinct QA intent."),
    "13-qa-completion-retry": ("postimplementation_external_correction", "Explicit resumed retry of failed attempt 12 after terminal network fetch failure; same QA-3 intent, not a fourth distinct QA intent."),
    "14-qa-completion-fresh": ("postimplementation_external_correction", "Fresh-session retry after resumed 13 returned empty with only a topic update; same QA-3 intent."),
    "15-qa-frontend-completion": ("postimplementation_external_correction", "Continuation of unfinished frontend QA-3 after 14 closed with a backend-only correction and next-step handoff; same QA-3 intent."),
    "16-qa-final-regressions": ("postimplementation_external_correction", "Fresh-session continuation of unfinished QA-3 regression assertions after partial 15; same QA-3 intent."),
    "17-qa-sonar-style": ("postimplementation_external_correction", "New QA-4 quality-remediation intent after exact generation-16 Sonar gateERROR with five minor style findings; native spec/tasks must precede the five targeted changes."),
}
QA_INTENTS = {
    "09-qa-correction": {"id": "QA-1", "retry_of": None},
    "10-qa-race-correction": {"id": "QA-2", "retry_of": None},
    "11-qa-timer-ownership": {"id": "QA-3", "retry_of": None},
    "12-qa-timer-retry": {"id": "QA-3", "retry_of": "11-qa-timer-ownership", "resumed": True},
    "13-qa-completion-retry": {"id": "QA-3", "retry_of": "12-qa-timer-retry", "resumed": True},
    "14-qa-completion-fresh": {"id": "QA-3", "retry_of": "13-qa-completion-retry", "resumed": False},
    "15-qa-frontend-completion": {"id": "QA-3", "retry_of": "14-qa-completion-fresh", "resumed": True},
    "16-qa-final-regressions": {"id": "QA-3", "retry_of": "15-qa-frontend-completion", "resumed": False},
    "17-qa-sonar-style": {"id": "QA-4", "retry_of": None, "resumed": False},
}


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
                if QA_INTENTS.get(row["label"], {}).get("resumed"):
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
                        "retry_of": QA_INTENTS[row["label"]]["retry_of"],
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
        if resumed_scope is None and QA_INTENTS.get(row["label"], {}).get("resumed"):
            main_name = row.get("requested_model", "gemini-3.5-flash")
            resumed_scope = {
                "status": "no completed CLI counters; main JSONL interval only",
                "retry_of": QA_INTENTS[row["label"]]["retry_of"],
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


def prepare_corpus(label: str, stage2_folder: str, unclosed: list[str]) -> dict:
    if label == "final" and unclosed:
        raise ValueError("Final corpus cannot be prepared while invocations remain open: " + ", ".join(unclosed))
    source_root = DOCS / "generation-08" / "files" if label == "generation-08" else CURRENT
    markdown = collect(source_root, [stage2_folder], {".md"})
    if not markdown:
        raise ValueError("No native Stage 2 Markdown corpus found at " + str(source_root))
    destination = DOCS / "bertopic-corpus" / label
    if destination.exists():
        raise FileExistsError("Refusing to overwrite corpus snapshot: " + str(destination))
    destination.mkdir(parents=True)
    items, pieces = [], []
    for name, path in sorted(markdown.items()):
        value = read(path)
        target = destination / "by-file" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8", newline="")
        items.append({
            "source": name, "corpus_path": target.relative_to(destination).as_posix(),
            "source_byte_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            "normalized_utf8_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest().upper(),
            "lines": len(value.splitlines()), "characters": len(value),
        })
        pieces.append(value)
    unified = "\n\n".join(pieces)
    (destination / "unified.md").write_text(unified, encoding="utf-8", newline="")
    manifest = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "label": label,
        "status": "frozen generation 08 before external QA; not final" if label == "generation-08" else "final snapshot prepared after all invocation metadata closed; model fitting not performed",
        "source_root": str(source_root), "scope": "native Stage 2 .md artifacts only; copied Stage 1 specs, JSON/OpenAPI schema, tool templates, research docs, transcripts and application source excluded",
        "normalization": "UTF-8 without BOM, LF newlines; no prose removed, stemmed, translated, chunked or deduplicated across different artifacts. Native task/checklist/research/contract text is retained. The shared seed is not injected as a separate document.",
        "unified_definition": "lexicographically sorted source paths; complete normalized per-file texts joined by exactly two LF characters; no researcher headings or filenames inserted into corpus text",
        "analysis_status": "corpus preparation only; no BERTopic model, embeddings, topic labels or comparison scores generated",
        "files": items, "markdown_file_count": len(items),
        "unified_characters": len(unified), "unified_utf8_sha256": hashlib.sha256(unified.encode("utf-8")).hexdigest().upper(),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"label": label, "path": str(destination), "markdown_file_count": len(items), "status": manifest["status"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-corpus", choices=("generation-08", "final"))
    args = parser.parse_args()
    measured_at = datetime.now(timezone.utc)
    feature_dirs = sorted(path for path in (CURRENT / "specs").glob("002-*") if path.is_dir())
    stage2_folder = feature_dirs[0].relative_to(CURRENT).as_posix() if feature_dirs else "specs/002-tetris-stage2-option-a"
    base_source = collect(BASE, ["backend", "frontend"], SOURCE_EXTS)
    current_source = collect(CURRENT, ["backend", "frontend"], SOURCE_EXTS)
    stage1_spec = collect(BASE, ["specs/001-build-tetris-core"], SPEC_EXTS)
    copied_stage1_spec = collect(CURRENT, ["specs/001-build-tetris-core"], SPEC_EXTS)
    stage2_spec = collect(CURRENT, [stage2_folder], SPEC_EXTS)
    dependency_names = ["backend/requirements.txt", "frontend/package.json", "frontend/package-lock.json"]
    dependency_before = {name: BASE / name for name in dependency_names if (BASE / name).exists()}
    dependency_after = {name: CURRENT / name for name in dependency_names if (CURRENT / name).exists()}
    runs = []
    catalog = transcript_catalog()
    for path in sorted(DOCS.glob("*.run.json")):
        row = json.loads(read(path))
        runs.append({**row, "classification": classification(row), "terminal_failure_observation": terminal_failure(row), "cli_tool_actions": cli_tool_actions(row), "tokens": stats_for_run(row, catalog)})
    closed_labels = {row["label"] for row in runs}
    open_runs = []
    for path in sorted(DOCS.glob("*.started.json")):
        if path.name.removesuffix(".started.json") in closed_labels:
            continue
        row = json.loads(read(path))
        observed = any(timestamp(row["started"]) <= entry["when"] <= measured_at for entry in catalog.values()) if row.get("started") else False
        open_runs.append({**row, "classification": classification(row), "model_started_observed": True if observed else None})
    unclosed = [row["label"] for row in open_runs]
    known_duration = round(sum(float(row["duration_seconds"]) for row in runs if row.get("duration_seconds") is not None), 3)
    model_duration = round(sum(float(row["duration_seconds"]) for row in runs if row.get("duration_seconds") is not None and row["tokens"]["model_started_observed"] is True), 3)
    spec_path = CURRENT / stage2_folder / "spec.md"
    spec_text = read(spec_path) if spec_path.exists() else ""
    result = {
        "measured_at_utc": measured_at.isoformat(),
        "feature_directory": stage2_folder,
        "source_scope": "backend/frontend .py/.ts/.tsx/.js/.jsx/.css/.html files, including tests; dependencies, build, generated coverage and caches excluded",
        "source_attribution_scope": "current source totals include inherited Stage 1 source plus tool-generated application/test changes; researcher helpers and evidence are excluded. Text counts alone do not establish authorship.",
        "spec_scope": "Native .md and .json artifacts in each Spec Kit feature directory; copied Stage 1 artifacts counted separately",
        "text_counting_rules": "UTF-8 text with BOM removed and universal newlines normalized to LF; physical lines use splitlines; raw file SHA-256 uses original bytes. Line deltas compare logical lines. CRLF/LF encoding and BOM-only differences are normalized; net character lengths still count LF codepoints, including a final LF when present.",
        "density_definition": "lines_per_file = total physical lines / included file count, rounded to two decimals; a textual density measure, not requirement density, quality, maintainability, or scalability",
        "snapshot_scope": "closed *.run.json invocations only; active or otherwise unclosed started metadata is excluded from all invocation/token/time totals; source and spec counts reflect files at collection time",
        "unclosed_invocation_labels": unclosed,
        "open_invocation_metadata": open_runs,
        "source_baseline": counts(base_source),
        "source_current": counts(current_source),
        "source_change": diff(base_source, current_source),
        "spec_stage1": counts(stage1_spec),
        "spec_stage1_copy": counts(copied_stage1_spec),
        "spec_stage1_copy_change": diff(stage1_spec, copied_stage1_spec),
        "spec_stage2": counts(stage2_spec),
        "spec_stage2_change_from_empty": diff({}, stage2_spec),
        "stage2_spec_delta_scope": "This tool creates a new Stage 2 feature directory, so native Stage 2 artifact growth is measured against an empty directory; inherited Stage 1 specs and their unchanged-copy check remain separate.",
        "dependency_manifests_baseline": counts(dependency_before),
        "dependency_manifests_current": counts(dependency_after),
        "dependency_manifests_change": diff(dependency_before, dependency_after),
        "stage2_requirement_ids": sorted(set(re.findall(r"\bFR-\d+\b", spec_text))),
        "runs": runs,
        "invocation_attempts": len(runs),
        "model_invocations": sum(row["tokens"]["model_started_observed"] is True for row in runs),
        "closed_process_outcomes": {key: sum(row["classification"]["process_outcome"] == key for row in runs) for key in ("closed_exit_zero", "closed_failed_or_interrupted", "closed_outcome_unknown")},
        "runs_with_unknown_model_start": [row["label"] for row in runs if row["tokens"]["model_started_observed"] is None],
        "prompt_count": len(runs),
        "prompt_count_note": "backward-compatible alias of invocation_attempts, including launcher failures before model startup",
        "external_prompt_scope": "invocation_attempts counts closed CLI launcher attempts, including the pre-model failure; model_invocations counts closed attempts with model evidence. Open attempts are metadata only and excluded from closed usage totals.",
        "correction_counts": correction_counts(runs, open_runs),
        "known_duration_seconds": known_duration,
        "known_model_invocation_duration_seconds": model_duration,
        "total_duration_seconds": known_duration,
        "duration_scope": "sum of known instrumented invocation durations only, including local launcher failures; unknown durations and external verification work excluded",
        "runs_with_unknown_duration": [row["label"] for row in runs if row.get("duration_seconds") is None],
        "observed_tokens": {key: sum(int(row["tokens"].get(key) or 0) for row in runs) for key in ("input_tokens", "cached_tokens", "output_tokens", "thought_tokens")},
        "runs_with_unknown_token_fields": {key: [row["label"] for row in runs if row["tokens"].get(key) is None] for key in ("input_tokens", "cached_tokens", "output_tokens", "thought_tokens")},
        "token_scope": "completed CLI stats include every reported model/role; fallback JSONL includes only recorded responses. Input includes cached tokens; output means candidate tokens; thought tokens are separate. Unknown values are not imputed.",
        "usage_provenance_limit": "usage totals cover the Gemini CLI experiment and its reported auxiliary roles only. Codex/researcher orchestration, read-only review agents, researcher-helper authoring, Drive/UI work, and other external verification effort are not included; these are not total project token/cost figures.",
        "known_api_totals": {key: sum(int(row["tokens"][key]) for row in runs if row["tokens"][key] is not None) for key in ("api_requests", "api_errors", "api_successful_requests")},
        "api_totals_scope": "known completed CLI API statistics and proven pre-model launcher zeroes only; excludes runs whose attempt/error totals are unknown",
        "runs_without_api_stats": [row["label"] for row in runs if row["tokens"]["api_requests"] is None],
        "observed_terminal_api_failures": [{"label": row["label"], **row["terminal_failure_observation"]} for row in runs if row["terminal_failure_observation"]],
        "recorded_response_count": sum(int(row["tokens"]["recorded_response_count"]) for row in runs if row["tokens"]["recorded_response_count"] is not None),
        "recorded_response_scope": "unique token-bearing JSONL response IDs within each closed run interval, deduplicated across original/archive snapshots; not interchangeable with API request attempts and may omit auxiliary models",
        "runs_without_recorded_response_stats": [row["label"] for row in runs if row["tokens"]["recorded_response_count"] is None],
        "runs_without_token_stats": [row["label"] for row in runs if row["tokens"]["source"] == "unavailable"],
    }
    snapshot_root = DOCS / "generation-08" / "files"
    if snapshot_root.exists():
        snapshot_source = collect(snapshot_root, ["backend", "frontend"], SOURCE_EXTS)
        snapshot_spec = collect(snapshot_root, [stage2_folder], SPEC_EXTS)
        result["qa_change_from_generation08"] = {
            "scope": "current text state versus frozen generation-08/files; includes any open QA invocation and is not a final or cumulative edit-volume claim",
            "source": diff(snapshot_source, current_source),
            "spec_stage2": diff(snapshot_spec, stage2_spec),
        }
    if args.prepare_corpus:
        result["corpus_preparation"] = prepare_corpus(args.prepare_corpus, stage2_folder, unclosed)
    result["corpus_snapshots"] = []
    for manifest_path in sorted((DOCS / "bertopic-corpus").glob("*/manifest.json")):
        manifest = json.loads(read(manifest_path))
        result["corpus_snapshots"].append({
            "label": manifest["label"], "manifest": manifest_path.relative_to(DOCS).as_posix(),
            "status": manifest["status"], "markdown_file_count": manifest["markdown_file_count"],
            "analysis_status": manifest["analysis_status"],
        })
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {key: result[key] for key in ("source_change", "spec_stage1_copy_change", "invocation_attempts", "model_invocations", "unclosed_invocation_labels", "known_duration_seconds", "runs_with_unknown_duration", "observed_tokens", "known_api_totals", "runs_without_api_stats", "recorded_response_count", "runs_without_token_stats")}
    summary["stage2_requirement_count"] = len(result["stage2_requirement_ids"])
    summary["correction_counts"] = result["correction_counts"]
    if "corpus_preparation" in result:
        summary["corpus_preparation"] = result["corpus_preparation"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
