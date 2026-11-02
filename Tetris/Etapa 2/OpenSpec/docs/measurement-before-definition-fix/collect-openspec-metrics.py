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


def cli_runs() -> list[dict]:
    rows = []
    audit_path = CURRENT / "docs" / "token-audit.json"
    audited = json.loads(read(audit_path)).get("runs", {}) if audit_path.exists() else {}
    for path in sorted((CURRENT / "docs").glob("*.run.json")):
        row = json.loads(read(path))
        stdout = CURRENT / "docs" / f"{row['label']}.stdout.json"
        stats = None
        if stdout.exists() and stdout.stat().st_size:
            try:
                data = json.loads(read(stdout))
                models = data.get("stats", {}).get("models", {})
                if models:
                    stats = {
                        "source": "Gemini CLI JSON stats",
                        "models": sorted(models),
                        "input_tokens": sum(int(m.get("tokens", {}).get("prompt") or 0) for m in models.values()),
                        "cached_tokens": sum(int(m.get("tokens", {}).get("cached") or 0) for m in models.values()),
                        "output_tokens": sum(int(m.get("tokens", {}).get("candidates") or 0) for m in models.values()),
                        "model_requests": sum(int(m.get("api", {}).get("totalRequests") or 0) for m in models.values()),
                    }
            except (ValueError, UnicodeError):
                pass
        if stats is None and row.get("ended") and row.get("started"):
            start = parse_stamp(row["started"])
            end = parse_stamp(row["ended"])
            events = {}
            for transcript in (CURRENT / "docs" / "gemini-home").rglob("*.jsonl"):
                for line in transcript.open(encoding="utf-8", errors="replace"):
                    try:
                        event = json.loads(line)
                        if event.get("type") != "gemini" or not event.get("tokens") or not event.get("id"):
                            continue
                        stamp = parse_stamp(event["timestamp"])
                        if start <= stamp <= end:
                            events[event["id"]] = event
                    except (ValueError, KeyError, TypeError):
                        continue
            if events:
                stats = {
                    "source": "Gemini CLI JSONL response records, deduplicated by response id and bounded by run timestamps",
                    "models": sorted({event.get("model", "unknown") for event in events.values()}),
                    "input_tokens": sum(int(event["tokens"].get("input") or 0) for event in events.values()),
                    "cached_tokens": sum(int(event["tokens"].get("cached") or 0) for event in events.values()),
                    "output_tokens": sum(int(event["tokens"].get("output") or 0) for event in events.values()),
                    "thought_tokens": sum(int(event["tokens"].get("thoughts") or 0) for event in events.values()),
                    "model_requests": len(events),
                }
        if stats is None and row["label"] in audited:
            stats = audited[row["label"]]
        rows.append({**row, "tokens": stats or {"source": "unavailable", "input_tokens": None, "cached_tokens": None, "output_tokens": None, "model_requests": None}})
    return rows


def main() -> None:
    base_source = files(BASE, "backend", SOURCE_EXTS) | files(BASE, "frontend", SOURCE_EXTS)
    final_source = files(CURRENT, "backend", SOURCE_EXTS) | files(CURRENT, "frontend", SOURCE_EXTS)
    base_spec = files(BASE, "openspec/changes/tetris-stage1-option-a", {".md"})
    stage_spec = files(CURRENT, "openspec/changes/tetris-stage2-option-a", {".md"})
    runs = cli_runs()
    result = {
        "source_scope": "backend and frontend text files with extensions .py, .ts, .tsx, .js, .jsx, .css, .html; tests included; dependencies, builds, generated coverage, lockfiles, docs, and cache excluded",
        "spec_scope": "native markdown artifacts under the Stage 1 and Stage 2 OpenSpec change directories; canonical and archived copies excluded to avoid double counting",
        "source_baseline": counts(base_source),
        "source_final": counts(final_source),
        "source_change": changed_lines(base_source, final_source),
        "spec_stage1": counts(base_spec),
        "spec_stage2": counts(stage_spec),
        "stage2_requirement_statements": sum(len(re.findall(r"(?m)^### Requirement:", read(p))) for p in stage_spec.values()),
        "runs": runs,
        "prompt_count": len(runs),
        "total_duration_seconds": round(sum(float(row.get("duration_seconds") or 0) for row in runs), 3),
        "observed_tokens": {
            key: sum(int(row["tokens"].get(key) or 0) for row in runs)
            for key in ("input_tokens", "cached_tokens", "output_tokens", "model_requests")
        },
        "runs_without_token_stats": [row["label"] for row in runs if row["tokens"]["source"] == "unavailable"],
    }
    path = CURRENT / "docs" / "metrics.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("source_change", "stage2_requirement_statements", "prompt_count", "total_duration_seconds", "observed_tokens", "runs_without_token_stats")}, indent=2))


if __name__ == "__main__":
    main()
