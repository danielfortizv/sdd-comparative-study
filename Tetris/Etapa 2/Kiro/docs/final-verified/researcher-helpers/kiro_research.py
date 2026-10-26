"""Read-only Kiro ACP/native-session measurement primitives (no model calls)."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parent.parent
ROOT = STAGE / "Kiro"
DOCS = ROOT / "docs"
BASE = STAGE.parent / "Etapa 1" / "Kiro"
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
EXCLUDE = {"node_modules", "venv", ".venv", "dist", "build", "coverage", "__pycache__", ".pytest_cache", "docs", ".sonar", ".sonar-user-home", ".git", ".agents"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load(path, default=None):
    return json.loads(read(path)) if path.exists() else default


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest().upper()


def timestamp(raw):
    raw = re.sub(r"(\.\d{6})\d+", r"\1", raw.replace("Z", "+00:00"))
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def seed_info():
    path = STAGE / "shared/seed.md"
    text = "\n".join(re.sub(r"^> ?", "", line) for line in read(path).splitlines() if line.startswith(">")).strip()
    return text, {"seed_file_sha256": digest(path.read_bytes()), "seed_block_utf8_sha256": digest(text), "seed_block_characters": len(text), "seed_block_scope": "quoted common seed, quote prefixes removed, trimmed, LF, UTF-8 without BOM; file hash covers original complete Markdown bytes"}


def runs(include_pending=False):
    closed = {p.name.removesuffix(".run.json"): p for p in DOCS.glob("*.run.json")}
    pending = {p.name.removesuffix(".started.json"): p for p in DOCS.glob("*.started.json") if p.name.removesuffix(".started.json") not in closed}
    result = []
    for label, path in sorted({**closed, **(pending if include_pending else {})}.items()):
        row = load(path)
        row.update(label=row.get("label", label), run_closed=label in closed, metadata_file=path.name)
        result.append(row)
    return result


def jsonl(path):
    events, invalid = [], []
    for number, line in enumerate(read(path).splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            invalid.append(number)
    return events, invalid


def stream_for_run(label):
    """Select one longest consistent event sequence; never dedup equal text chunks."""
    paths = [DOCS / f"{label}.stdout.jsonl"]
    for item in load(DOCS / "transcripts-archive/manifest.json", []):
        if item.get("kind") == "acp_stream" and item.get("run_label") == label:
            paths.append(DOCS / item["archive"])
    versions = []
    for path in dict.fromkeys(paths):
        if path.exists():
            events, invalid = jsonl(path)
            if events:
                identities = [digest(json.dumps(event, sort_keys=True, separators=(",", ":"))) for event in events]
                versions.append((events, identities, path, invalid))
    if not versions:
        return {"events": [], "paths": [], "invalid_lines": {}, "conflict": False}
    longest = max(versions, key=lambda item: len(item[0]))
    conflict = any(item[1] != longest[1][:len(item[1])] for item in versions)
    return {"events": longest[0], "paths": [str(item[2].relative_to(DOCS)).replace("\\", "/") for item in versions], "selected": longest[2].relative_to(DOCS).as_posix(), "invalid_lines": {item[2].relative_to(DOCS).as_posix(): item[3] for item in versions if item[3]}, "conflict": conflict}


def stream_session_ids(stream):
    return sorted({e.get("data", {}).get("sessionId") for e in stream["events"] if e.get("data", {}).get("sessionId")})


def native_session_paths(session_ids, home=None):
    home = home or Path.home() / ".kiro"
    for folder in (home / "sessions", home / "spec-sessions"):
        if folder.exists():
            for sid in session_ids:
                if not re.fullmatch(r"sess_[A-Za-z0-9-]+", sid):
                    continue
                for path in folder.glob(f"*/{sid}/session.json"):
                    yield sid, path
                direct = folder / sid / "session.json"
                if direct.exists():
                    yield sid, direct


def native_catalog(session_ids):
    paths = [(sid, path.parent / "messages.jsonl") for sid, path in native_session_paths(session_ids)]
    for item in load(DOCS / "transcripts-archive/manifest.json", []):
        if item.get("kind") == "native_messages" and item.get("session_id") in session_ids:
            paths.append((item["session_id"], DOCS / item["archive"]))
    records, invalid = {}, {}
    for sid, path in dict.fromkeys(paths):
        if not path.exists():
            continue
        events, bad = jsonl(path)
        if bad:
            invalid[str(path)] = bad
        for event in events:
            if not event.get("id") or not event.get("timestamp") or not isinstance(event.get("payload"), dict):
                continue
            # Kiro reuses some interaction IDs at different timestamps. Preserve
            # those real events while collapsing identical archive snapshots.
            key = (sid, event["id"], event["timestamp"])
            if key not in records:
                records[key] = {"session_id": sid, "event": event, "paths": set(), "conflict": False}
            record = records[key]
            if record["event"] != event:
                record["conflict"] = True
            record["paths"].add(str(path))
    return list(records.values()), invalid


def native_session_metadata(session_ids):
    values = {}
    # Immutable archive metadata is a fallback if the original session is gone.
    for item in load(DOCS / "transcripts-archive/manifest.json", []):
        if item.get("kind") == "native_session" and item.get("session_id") in session_ids:
            path = DOCS / item["archive"]
            if path.exists():
                value = load(path)
                old = values.get(item["session_id"])
                if not old or value.get("lastModifiedAt", "") >= old.get("lastModifiedAt", ""):
                    values[item["session_id"]] = value
    for sid, path in native_session_paths(session_ids):
        values[sid] = load(path)
    return values


def interval_records(run, records, active_until=None):
    # Interrupted transports may have no observed process end. An explicitly
    # labelled observation bound retains their native records without inventing
    # an end timestamp or elapsed duration. All older run semantics are intact.
    end = run.get("ended") or run.get("observation_end_upper_bound_utc") or active_until
    if not run.get("started") or not end:
        return []
    start, end = timestamp(run["started"]), timestamp(end)
    return [r for r in records if start <= timestamp(r["event"]["timestamp"]) <= end]


def source_paths(root):
    result = {}
    for folder in ("backend", "frontend"):
        if not (root / folder).exists():
            continue
        for path in (root / folder).rglob("*"):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in SOURCE_EXTS and not any(p in EXCLUDE for p in path.relative_to(root).parts):
                result[path.relative_to(root).as_posix()] = path
    return result


def spec_paths(root):
    folder = root / ".kiro/specs"
    return {p.relative_to(root).as_posix(): p for p in folder.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower() in {".md", ".json"}} if folder.exists() else {}


def manifests(root):
    names = ("backend/requirements.txt", "backend/requirements-dev.txt", "frontend/package.json", "frontend/package-lock.json", "backend/pyproject.toml", "backend/poetry.lock", "frontend/pnpm-lock.yaml", "frontend/yarn.lock")
    return {name: root / name for name in names if (root / name).is_file()}


def configurations(root):
    names = ("backend/pytest.ini", "backend/.coveragerc", "frontend/tsconfig.json", "frontend/tsconfig.node.json", "frontend/tsconfig.vitest.json", "frontend/vite.config.ts", "frontend/vitest.config.ts", "sonar-project.properties")
    return {name: root / name for name in names if (root / name).is_file()}


def counts(paths):
    files = {}
    for name, path in sorted(paths.items()):
        text = read(path)
        lines = text.splitlines()
        files[name] = {"lines": len(lines), "nonblank_lines": sum(bool(s.strip()) for s in lines), "characters": len(text), "sha256": digest(path.read_bytes())}
    lines = sum(r["lines"] for r in files.values())
    return {"files": len(files), "lines": lines, "nonblank_lines": sum(r["nonblank_lines"] for r in files.values()), "characters": sum(r["characters"] for r in files.values()), "lines_per_file": round(lines / len(files), 2) if files else 0, "per_file": files}


def changes(before, after):
    added = removed = 0
    names = []
    for name in sorted(before.keys() | after.keys()):
        left = read(before[name]).splitlines() if name in before else []
        right = read(after[name]).splitlines() if name in after else []
        if left == right:
            continue
        names.append(name)
        for tag, a, b, c, d in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
            if tag in ("replace", "delete"):
                removed += b - a
            if tag in ("replace", "insert"):
                added += d - c
    return {"changed_files": names, "changed_file_count": len(names), "added_lines": added, "removed_lines": removed, "net_lines": added - removed, "net_characters": sum(len(read(p)) for p in after.values()) - sum(len(read(p)) for p in before.values()), "definition": "SequenceMatcher noncumulative line diff; characters are net decoded LF-normalized Unicode text size difference, not cumulative editing volume"}


def source_category(name):
    if "/tests/" in name or re.search(r"(?:\.|/)(?:test|spec)\.", name):
        return "tests"
    if name.startswith("backend/app/") or name.startswith("frontend/src/") and not name.endswith(".d.ts"):
        return "production"
    return "configuration_and_support"


def run_measurement(run):
    stream = stream_for_run(run["label"])
    sids = stream_session_ids(stream)
    records, invalid = native_catalog(sids)
    selected = interval_records(run, records)
    payloads = [r["event"]["payload"] for r in selected]
    usage_records = [r for r in selected if r["event"]["payload"].get("type") == "usage_summary"]
    # One terminal summary per execution; retain its latest timestamp if the
    # session emits updates. Archive copies never introduce another charge.
    usage_by_execution = {}
    for record in sorted(usage_records, key=lambda r: r["event"]["timestamp"]):
        payload = record["event"]["payload"]
        key = (record["session_id"], payload.get("executionId") or record["event"]["id"])
        usage_by_execution[key] = record
    usage = list(usage_by_execution.values())
    usage_source = "latest native usage_summary per session/execution within closed launcher interval; native events deduplicated by session/message ID/timestamp"
    if not usage:
        usage = [{"session_id": e["data"].get("sessionId"), "event": {"id": f"acp-{i}", "payload": e["data"]["update"]["_meta"]["kiro"]}} for i, e in enumerate(stream["events"]) if e.get("data", {}).get("update", {}).get("_meta", {}).get("kiro", {}).get("kind") == "turn_completion"]
        usage_source = "invocation ACP turn_completion snapshots; unavailable if stream variants conflict"
        # Repeated completion snapshots represent one summary, not multiple charges.
        usage = list({digest(json.dumps(r["event"]["payload"], sort_keys=True)): r for r in usage}.values())
    safe = bool(usage) and not stream["conflict"] and not any(r.get("conflict") for r in usage)
    credits = []
    request_ids = set()
    elapsed_ms = []
    details = []
    for record in usage:
        payload = record["event"]["payload"]
        summaries = payload.get("promptTurnSummaries", [])
        credited = [s["usage"] for s in summaries if s.get("unit") == "credit" and isinstance(s.get("usage"), (int, float))]
        if credited:
            credits.extend(credited)
        request_ids.update(payload.get("requestIds", []))
        if isinstance(payload.get("elapsedTime"), (int, float)):
            elapsed_ms.append(payload["elapsedTime"])
        details.append({"session_id": record["session_id"], "message_id": record["event"]["id"], "execution_id": payload.get("executionId"), "timestamp": record["event"].get("timestamp"), "status": payload.get("status"), "prompt_turn_summaries": summaries, "elapsed_time_ms": payload.get("elapsedTime"), "recorded_request_ids": payload.get("requestIds", [])})
    tools = {p["toolCallId"]: p for p in payloads if p.get("type") == "tool_call" and p.get("toolCallId")}
    results = {p["toolCallId"]: p for p in payloads if p.get("type") == "tool_result" and p.get("toolCallId")}
    kinds = Counter(e.get("data", {}).get("update", {}).get("sessionUpdate") for e in stream["events"] if e.get("type") == "sessionUpdate")
    if not tools:
        tools = {e["data"]["update"]["toolCallId"]: e["data"]["update"] for e in stream["events"] if e.get("data", {}).get("update", {}).get("sessionUpdate") == "tool_call"}
    finish = [e["data"] for e in stream["events"] if e.get("type") == "runFinished"]
    say = [r for r in selected if r["event"]["payload"].get("type") == "assistant" and r["event"]["payload"].get("operationType") == "Say"]
    context = [e["data"]["update"]["_meta"]["kiro"] for e in stream["events"] if "contextUsage" in e.get("data", {}).get("update", {}).get("_meta", {}).get("kiro", {})]
    session_metadata = []
    for sid, data in native_session_metadata(sids).items():
        session_metadata.append({"session_id": sid, "model_id": data.get("modelId"), "agent_mode": data.get("agentMode"), "created_at": data.get("createdAt"), "scope": "session configuration, not proof of backend resolved model or auxiliary role attribution"})
    result = {"session_ids": sids, "model_invocation_observed": bool(usage or any(p.get("type") == "assistant" for p in payloads) or kinds.get("agent_message_chunk")), "input_tokens": None, "cached_tokens": None, "output_tokens": None, "thought_tokens": None, "token_status": "not exposed as billed input/cache/output/thought counters in observed Kiro ACP/native schema; context breakdown is not token usage", "api_requests": None, "api_errors": None, "api_successful_requests": None, "api_status": "not exposed; requestIds are retained as identifiers only, not attempted/succeeded/error API counters", "credits": sum(credits) if safe and credits else None, "credits_scope": usage_source, "agent_elapsed_seconds": sum(elapsed_ms) / 1000 if safe and elapsed_ms else None, "agent_elapsed_scope": "sum of retained turn elapsedTime milliseconds; distinct from launcher wall duration and entire resumed-session lifetime", "recorded_request_id_count": len(request_ids) if safe else None, "usage_summaries": details, "native_assistant_say_count": len(say) if selected else None, "native_assistant_reasoning_record_count": sum(p.get("type") == "assistant" and p.get("operationType") == "Reasoning" for p in payloads) if selected else None, "recorded_response_count": None, "recorded_response_status": "Kiro Say messages and ACP chunks are not defined as API model responses", "native_user_message_count": sum(p.get("type") == "user" for p in payloads) if selected else None, "tool_call_count": len(tools) if tools else (0 if stream["events"] else None), "tool_result_success_flags": dict(Counter(str(p.get("success")) for p in results.values())), "tool_success_limitation": "wrapper success does not prove command/test/scanner exit success; inspect raw output", "acp_event_count": len(stream["events"]) if stream["events"] else None, "acp_session_update_counts": dict(kinds), "acp_run_finished": [{k: p.get(k) for k in ("status", "stopReason", "finalTextTruncated")} for p in finish], "stream_paths": stream["paths"], "stream_selected": stream.get("selected"), "stream_prefix_conflict": stream["conflict"], "invalid_stream_lines": stream["invalid_lines"], "invalid_native_lines": invalid, "native_record_conflicts": [r["event"]["id"] for r in selected if r.get("conflict")], "native_interval_record_count": len(selected), "session_configuration": session_metadata, "auxiliary_role_usage": None, "auxiliary_role_status": "no per-model/per-role usage counters observed; credits may include internal actions without separate attribution", "latest_context_snapshot": context[-1] if context else None, "context_snapshot_scope": "last context occupancy/composition snapshot only; never summed as cumulative tokens"}

    config_observations = []
    for index, event in enumerate(stream["events"], 1):
        update = event.get("data", {}).get("update", {})
        if update.get("sessionUpdate") == "config_option_update":
            selected = {option.get("id"): option.get("currentValue") for option in update.get("configOptions", []) if option.get("id") in ("mode", "model", "autopilot")}
            config_observations.append({"stream_event_index_1based": index, "session_id": event.get("data", {}).get("sessionId"), "selected_values": selected})
    result["acp_configuration_observations"] = config_observations
    result["observed_mode_selection_values"] = sorted({str(row["selected_values"]["mode"]) for row in config_observations if row["selected_values"].get("mode") is not None})
    result["observed_model_selection_values"] = sorted({str(row["selected_values"]["model"]) for row in config_observations if row["selected_values"].get("model") is not None})
    result["native_assistant_agent_modes"] = sorted({str(p.get("_meta", {}).get("kiro", {}).get("agentMode")) for p in payloads if p.get("type") == "assistant" and p.get("_meta", {}).get("kiro", {}).get("agentMode") is not None})
    result["configuration_attribution_scope"] = "Selected/current configuration and emitted native assistant agentMode are separate from requested flags. Auto configuration is observable; resolved backend/auxiliary models are not established."
    result["native_payload_type_counts"] = dict(Counter(p.get("type", "unknown") for p in payloads))
    known_updates = {"available_commands_update", "config_option_update", "session_info_update", "agent_message_chunk", "agent_thought_chunk", "tool_call", "tool_call_update", "user_message_chunk"}
    result["unrecognized_acp_update_types"] = sorted(str(kind) for kind in kinds if kind not in known_updates)
    return result
