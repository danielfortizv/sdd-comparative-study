"""Collect the isolated BMAD full-path rerun without changing baseline metrics."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "Bmad Method Full"
EXCLUDE = {"node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".pytest_cache", ".sonar"}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
TOKEN_KEYS = ("input", "output", "cached", "thoughts", "tool", "total")


def selected_files(path: Path, extensions: set[str]) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        item for item in path.rglob("*")
        if item.is_file()
        and item.suffix.lower() in extensions
        and not any(part in EXCLUDE for part in item.relative_to(path).parts)
    )


def count_text(paths: list[Path]) -> dict[str, int]:
    contents = [path.read_text(encoding="utf-8-sig", errors="replace") for path in paths]
    return {
        "files": len(paths),
        "lines": sum(len(text.splitlines()) for text in contents),
        "nonblank_lines": sum(sum(bool(line.strip()) for line in text.splitlines()) for text in contents),
        "characters": sum(len(text) for text in contents),
    }


def model_events() -> dict[str, object]:
    chat_root = TOOL / "docs" / "gemini-home" / ".gemini" / "tmp"
    transcripts = sorted(chat_root.rglob("*.jsonl")) if chat_root.exists() else []
    responses: dict[str, dict] = {}
    calls: dict[str, int] = {}
    for path in transcripts:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "gemini" or not event.get("id"):
                continue
            if event.get("tokens"):
                responses[event["id"]] = event["tokens"]
            if event.get("toolCalls") is not None:
                calls[event["id"]] = len(event["toolCalls"])
    return {
        "transcript_files": len(transcripts),
        "model_responses": len(responses),
        "tool_calls_observed": sum(calls.values()),
        **{key: sum(int(value.get(key) or 0) for value in responses.values()) for key in TOKEN_KEYS},
    }


def run_events() -> dict[str, object]:
    runs = []
    for path in sorted((TOOL / "docs").glob("*.run.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        runs.append({
            "file": path.name,
            "duration_seconds": value.get("duration_seconds"),
            "exit_code": value.get("exit_code"),
            "seed_sha256": value.get("seed_sha256"),
        })
    return {
        "invocations": len(runs),
        "agent_seconds_including_failed_starts": round(sum(float(item.get("duration_seconds") or 0) for item in runs), 3),
        "runs": runs,
    }


def main() -> None:
    # Count user-facing native planning/specification artifacts. BMAD .memlog.md
    # files are workflow traces, not specifications; disclose them separately.
    all_markdown = selected_files(TOOL / "_bmad-output", {".md"})
    specs = [path for path in all_markdown if not path.name.startswith(".")]
    workflow_traces = [path for path in all_markdown if path.name.startswith(".")]
    sources = [
        path for directory in (TOOL / "backend", TOOL / "frontend")
        for path in selected_files(directory, SOURCE_EXTS)
    ]
    prds = list((TOOL / "_bmad-output").rglob("prd.md"))
    ids = set()
    for path in prds:
        ids.update(re.findall(r"(?:FR|REQ)-[0-9]+", path.read_text(encoding="utf-8-sig", errors="replace")))
    sonar_path = TOOL / "docs" / "sonar-metrics.json"
    sonar = None
    if sonar_path.exists():
        payload = json.loads(sonar_path.read_text(encoding="utf-8-sig"))
        sonar = {item["metric"]: item.get("value") for item in payload["component"]["measures"]}
    result = {
        "run_label": "BMAD 6.12.0 full planning path; separate from original quick path",
        "specification": {**count_text(specs), "paths": [str(path.relative_to(TOOL)) for path in specs], "unique_prd_requirement_ids": len(ids), "excluded_workflow_trace_files": len(workflow_traces)},
        "source": count_text(sources),
        "model": model_events(),
        "execution": run_events(),
        "sonar": sonar,
    }
    destination = ROOT / "shared" / "bmad-full-metrics.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "model"}, ensure_ascii=False, indent=2))
    print("model", json.dumps(result["model"], ensure_ascii=False))


if __name__ == "__main__":
    main()
