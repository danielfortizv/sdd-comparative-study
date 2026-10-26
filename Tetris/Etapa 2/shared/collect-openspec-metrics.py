"""Reproducible Stage 2 OpenSpec measurements from retained local artifacts."""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
BASE = CASE / "Etapa 1" / "OpenSpec"
CURRENT = STAGE / "OpenSpec"
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
EXCLUDE = {"node_modules", "venv", ".venv", "dist", "build", "coverage", ".vitest-tmp", "__pycache__", ".pytest_cache", "docs", ".sonar"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def parse_stamp(value: str) -> datetime:
    # PowerShell writes seven fractional second digits; Python 3.10 accepts six.
    value = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def files(root: Path, relative: str, extensions: set[str]) -> dict[str, Path]:
    start = root / relative
    if not start.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in start.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
        and not any(part in EXCLUDE for part in path.relative_to(start).parts)
    }


def counts(paths: dict[str, Path]) -> dict:
    per_file = {}
    for name, path in sorted(paths.items()):
        value = read(path)
        lines = value.splitlines()
        per_file[name] = {
            "lines": len(lines),
            "nonblank_lines": sum(bool(line.strip()) for line in lines),
            "characters": len(value),
        }
    return {
        "files": len(per_file),
        "lines": sum(item["lines"] for item in per_file.values()),
        "nonblank_lines": sum(item["nonblank_lines"] for item in per_file.values()),
        "characters": sum(item["characters"] for item in per_file.values()),
        "lines_per_file": round(sum(item["lines"] for item in per_file.values()) / len(per_file), 2) if per_file else 0,
        "per_file": per_file,
    }


def changed_lines(before: dict[str, Path], after: dict[str, Path]) -> dict:
    added = removed = 0
    changed_files = []
    for name in sorted(set(before) | set(after)):
        left = read(before[name]).splitlines() if name in before else []
        right = read(after[name]).splitlines() if name in after else []
        if left == right:
            continue
        changed_files.append(name)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
            if tag in {"delete", "replace"}:
                removed += i2 - i1
            if tag in {"insert", "replace"}:
                added += j2 - j1
    return {"changed_files": changed_files, "changed_file_count": len(changed_files), "added_lines": added, "removed_lines": removed}


def complete_sum(values) -> int | None:
    values = list(values)
    return sum(int(value) for value in values) if all(value is not None for value in values) else None


def transcript_catalog() -> dict[str, dict]:
    """Index each response once, including fallback immutable archive copies."""
    catalog = {}
    docs = CURRENT / "docs"
    for folder in (docs / "gemini-home", docs / "transcripts-archive"):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.jsonl")):
            for line in path.open(encoding="utf-8-sig", errors="replace"):
                try:
                    event = json.loads(line)
                    if event.get("type") != "gemini" or not event.get("tokens") or not event.get("id"):
                        continue
                    stamp = parse_stamp(event["timestamp"])
                    identity = event["id"]
                    relative = path.relative_to(docs).as_posix()
                    existing = catalog.get(identity)
                    if existing is None:
                        catalog[identity] = {"event": event, "stamp": stamp, "paths": {relative}}
                    else:
                        existing["paths"].add(relative)
                        score = (stamp, int(event["tokens"].get("total") or 0), len(line))
                        old = existing["event"]
                        old_score = (existing["stamp"], int(old["tokens"].get("total") or 0), len(json.dumps(old, separators=(",", ":"))))
                        if score >= old_score:
                            existing.update(event=event, stamp=stamp)
                except (ValueError, KeyError, TypeError):
                    continue
    return catalog


def response_stats(row: dict, catalog: dict, historical: dict) -> tuple[dict, list]:
    entries = []
    if row.get("started") and row.get("ended"):
        start, end = parse_stamp(row["started"]), parse_stamp(row["ended"])
        entries = [entry for entry in catalog.values() if start <= entry["stamp"] <= end]
    retained_count = len(entries) if entries else None
    # This legacy field in token-audit.json counted observed JSONL responses,
    # not API attempts. Preserve the historical evidence file unchanged.
    historical_count = historical.get("model_requests")
    documented_count = retained_count if retained_count is not None else historical_count
    return {
        "recorded_response_count": retained_count,
        "recorded_response_models": sorted({entry["event"].get("model", "unknown") for entry in entries}),
        "transcript_paths": sorted({path for entry in entries for path in entry["paths"]}),
        "historically_documented_response_count": historical_count,
        "documented_response_count": documented_count,
        "documented_response_origin": "retained JSONL records, deduplicated by response ID and run interval" if retained_count is not None else "historical JSONL-derived capture in docs/token-audit.json; original response records no longer retained" if historical_count is not None else "unavailable",
        "response_scope": "recorded or historically documented token-bearing responses; excludes failed API attempts and may omit auxiliary models; retained and historical counts are not added twice for one run",
    }, [entry["event"] for entry in entries]


def cli_runs() -> list[dict]:
    rows = []
    docs = CURRENT / "docs"
    audit_path = docs / "token-audit.json"
    audited = json.loads(read(audit_path)).get("runs", {}) if audit_path.exists() else {}
    catalog = transcript_catalog()
    for path in sorted(docs.glob("*.run.json")):
        row = json.loads(read(path))
        historical = audited.get(row["label"], {})
        responses, events = response_stats(row, catalog, historical)
        stdout = docs / f"{row['label']}.stdout.json"
        stats = None
        if stdout.exists() and stdout.stat().st_size:
            try:
                models = json.loads(read(stdout)).get("stats", {}).get("models", {})
                if models:
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
                    stats = {
                        "source": "Gemini CLI JSON stats",
                        "models": sorted(models),
                        "input_tokens": complete_sum(model.get("tokens", {}).get("prompt") for model in models.values()),
                        "cached_tokens": complete_sum(model.get("tokens", {}).get("cached") for model in models.values()),
                        "output_tokens": complete_sum(model.get("tokens", {}).get("candidates") for model in models.values()),
                        "thought_tokens": complete_sum(model.get("tokens", {}).get("thoughts") for model in models.values()),
                        **{key: complete_sum(model[key] for model in api_by_model.values()) for key in ("api_requests", "api_errors", "api_successful_requests")},
                        "api_by_model": api_by_model,
                        "api_scope": "all models/roles in completed CLI JSON stats; attempts include API errors",
                        "model_started_observed": True,
                    }
            except (ValueError, UnicodeError):
                pass
        if stats is None and events:
            stats = {
                "source": "Gemini CLI JSONL response records, deduplicated by response id and bounded by run timestamps",
                "models": sorted({event.get("model", "unknown") for event in events}),
                "input_tokens": complete_sum(event["tokens"].get("input") for event in events),
                "cached_tokens": complete_sum(event["tokens"].get("cached") for event in events),
                "output_tokens": complete_sum(event["tokens"].get("output") for event in events),
                "thought_tokens": complete_sum(event["tokens"].get("thoughts") for event in events),
                "model_started_observed": True,
            }
        if stats is None and historical:
            stats = {key: value for key, value in historical.items() if key != "model_requests"}
            stats.setdefault("thought_tokens", None)
            stats["model_started_observed"] = True
            stats["historical_evidence_path"] = "docs/token-audit.json"
        if stats is None:
            stats = {"source": "unavailable", "models": [], "input_tokens": None, "cached_tokens": None, "output_tokens": None, "thought_tokens": None, "model_started_observed": None}
        if "api_requests" not in stats:
            stats.update(api_requests=None, api_errors=None, api_successful_requests=None, api_scope="unknown: response records and historical response captures cannot establish total API attempts/errors")
        rows.append({**row, "tokens": {**stats, **responses}})
    return rows


def main() -> None:
    base_source = files(BASE, "backend", SOURCE_EXTS) | files(BASE, "frontend", SOURCE_EXTS)
    final_source = files(CURRENT, "backend", SOURCE_EXTS) | files(CURRENT, "frontend", SOURCE_EXTS)
    base_spec = files(BASE, "openspec/changes/tetris-stage1-option-a", {".md"})
    stage_spec = files(CURRENT, "openspec/changes/tetris-stage2-option-a", {".md"})
    runs = cli_runs()
    known_duration = round(sum(float(row["duration_seconds"]) for row in runs if row.get("duration_seconds") is not None), 3)
    result = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_scope": "backend and frontend text files with extensions .py, .ts, .tsx, .js, .jsx, .css, .html; tests included; dependencies, builds, generated coverage, lockfiles, docs, and cache excluded",
        "spec_scope": "native markdown artifacts under the Stage 1 and Stage 2 OpenSpec change directories; canonical and archived copies excluded to avoid double counting",
        "text_counting_rules": "UTF-8 text with BOM removed and universal newlines normalized to LF; physical lines use splitlines; deltas compare logical lines and ignore newline-only/BOM-only changes",
        "source_baseline": counts(base_source),
        "source_final": counts(final_source),
        "source_change": changed_lines(base_source, final_source),
        "spec_stage1": counts(base_spec),
        "spec_stage2": counts(stage_spec),
        "stage2_requirement_statements": sum(len(re.findall(r"(?m)^### Requirement:", read(p))) for p in stage_spec.values()),
        "runs": runs,
        "invocation_attempts": len(runs),
        "model_invocations": sum(row["tokens"]["model_started_observed"] is True for row in runs),
        "runs_with_unknown_model_start": [row["label"] for row in runs if row["tokens"]["model_started_observed"] is None],
        "prompt_count": len(runs),
        "prompt_count_note": "backward-compatible alias of invocation_attempts, not an assertion that every attempt reached a model",
        "known_duration_seconds": known_duration,
        "total_duration_seconds": known_duration,
        "duration_scope": "sum of known instrumented invocation durations; unknown durations and external verification work excluded",
        "runs_with_unknown_duration": [row["label"] for row in runs if row.get("duration_seconds") is None],
        "observed_tokens": {
            key: sum(int(row["tokens"].get(key) or 0) for row in runs)
            for key in ("input_tokens", "cached_tokens", "output_tokens", "thought_tokens")
        },
        "token_scope": "partial observed totals: completed CLI JSON statistics include all reported models/roles; retained JSONL and historical captures include only observed responses. Input includes cached tokens; candidate output and thought tokens are separate. Unknown values are not imputed.",
        "runs_with_unknown_token_fields": {key: [row["label"] for row in runs if row["tokens"].get(key) is None] for key in ("input_tokens", "cached_tokens", "output_tokens", "thought_tokens")},
        "known_api_totals": {key: sum(int(row["tokens"][key]) for row in runs if row["tokens"][key] is not None) for key in ("api_requests", "api_errors", "api_successful_requests")},
        "api_totals_scope": "partial: completed CLI API statistics only; excludes runs with unknown API attempts/errors; historical JSONL response counts are never treated as API attempts",
        "runs_without_api_stats": [row["label"] for row in runs if row["tokens"]["api_requests"] is None],
        "recorded_response_count": sum(int(row["tokens"]["recorded_response_count"]) for row in runs if row["tokens"]["recorded_response_count"] is not None),
        "historically_documented_response_count": sum(int(row["tokens"]["historically_documented_response_count"]) for row in runs if row["tokens"]["recorded_response_count"] is None and row["tokens"]["historically_documented_response_count"] is not None),
        "documented_response_count": sum(int(row["tokens"]["documented_response_count"]) for row in runs if row["tokens"]["documented_response_count"] is not None),
        "documented_response_scope": "partial: retained JSONL response IDs plus historical JSONL-derived captures from token-audit.json for runs with no retained records; does not include failed API attempts or unrecorded auxiliary responses",
        "runs_without_documented_response_stats": [row["label"] for row in runs if row["tokens"]["documented_response_count"] is None],
        "runs_without_token_stats": [row["label"] for row in runs if row["tokens"]["source"] == "unavailable"],
    }
    path = CURRENT / "docs" / "metrics.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("source_change", "stage2_requirement_statements", "invocation_attempts", "model_invocations", "known_duration_seconds", "observed_tokens", "known_api_totals", "runs_without_api_stats", "recorded_response_count", "historically_documented_response_count", "documented_response_count", "runs_without_documented_response_stats", "runs_without_token_stats")}, indent=2))


if __name__ == "__main__":
    main()
