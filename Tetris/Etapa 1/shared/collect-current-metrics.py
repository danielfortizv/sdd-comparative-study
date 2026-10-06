"""Extract reproducible preliminary experiment metrics from local evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC_DIRS = {
    "OpenSpec": ["openspec/changes"],
    "Spec Kit": ["specs"],
    "Bmad Method": ["_bmad-output"],
    "Tessl": ["specs"],
    "Kiro": [".kiro/specs"],
}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
EXCLUDE_DIRS = {"node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".venv", "venv", ".sonar"}
TOKEN_KEYS = ("input", "output", "cached", "thoughts", "tool", "total")
REQUIREMENT_PATTERNS = {
    "OpenSpec": r"(?m)^### Requirement:",
    "Spec Kit": r"(?m)^\s*-\s*\*\*FR-\d{3}\*\*",
    "Bmad Method": r"(?:FR|REQ)-[0-9]+",
    "Tessl": r"(?m)^\s*-\s*\*\*Req-\d+:",
    "Kiro": r"(?m)^### Requirement \d+:",
}


def files_in(directory: Path, extensions: set[str]) -> list[Path]:
    if not directory.exists():
        return []
    return [
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
        and not any(part in EXCLUDE_DIRS for part in path.relative_to(directory).parts)
    ]


def text_counts(paths: list[Path]) -> dict[str, int]:
    counts = {"files": len(paths), "lines": 0, "nonblank_lines": 0, "characters": 0}
    for path in paths:
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        lines = content.splitlines()
        counts["lines"] += len(lines)
        counts["nonblank_lines"] += sum(bool(line.strip()) for line in lines)
        counts["characters"] += len(content)
    return counts


def gemini_tokens(tool_root: Path) -> dict[str, int]:
    chat_root = tool_root / "docs" / "gemini-home" / ".gemini" / "tmp"
    unique: dict[str, dict[str, int]] = {}
    transcript_files = 0
    sessions = []
    if chat_root.exists():
        for path in sorted(chat_root.rglob("*.jsonl")):
            transcript_files += 1
            file_unique: dict[str, dict[str, int]] = {}
            started = None
            for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if started is None:
                    started = record.get("startTime") or record.get("timestamp")
                if record.get("type") != "gemini" or not record.get("tokens"):
                    continue
                request_id = record.get("id")
                if request_id:
                    unique[request_id] = record["tokens"]
                    file_unique[request_id] = record["tokens"]
            sessions.append(
                {
                    "file": str(path.relative_to(tool_root)),
                    "started": started,
                    "model_responses": len(file_unique),
                    **{key: sum(int(tokens.get(key) or 0) for tokens in file_unique.values()) for key in TOKEN_KEYS},
                }
            )
    counts = {key: sum(int(tokens.get(key) or 0) for tokens in unique.values()) for key in TOKEN_KEYS}
    return {"transcript_files": transcript_files, "model_responses": len(unique), **counts, "sessions": sessions}


def run_metadata(tool_root: Path) -> dict[str, object]:
    run_paths = sorted((tool_root / "docs").glob("*.run.json")) if (tool_root / "docs").exists() else []
    runs = []
    for path in run_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        runs.append(
            {
                "file": str(path.relative_to(ROOT)),
                "started": data.get("started"),
                "ended": data.get("ended"),
                "duration_seconds": data.get("duration_seconds"),
                "exit_code": data.get("exit_code"),
                "seed_sha256": data.get("seed_sha256"),
            }
        )
    return {
        "runs": runs,
        "recorded_duration_seconds": round(sum(float(run.get("duration_seconds") or 0) for run in runs), 3),
        "recorded_prompt_count": len(runs),
    }


def main() -> None:
    result = {}
    snapshot_path = ROOT / "shared" / "metrics-preliminary.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else {}
    for tool, spec_dirs in SPEC_DIRS.items():
        tool_root = ROOT / tool
        if tool == "Bmad Method" and (ROOT / "Bmad Method Full").exists():
            tool_root = ROOT / "Bmad Method Full"
        if tool == "Bmad Method":
            canonical = json.loads((ROOT / "shared" / "bmad-metrics.json").read_text(encoding="utf-8"))
            spec = {key: canonical["specification"][key] for key in ("files", "lines", "nonblank_lines", "characters")}
            spec["lines_per_file"] = round(spec["lines"] / spec["files"], 2)
            spec["requirement_statements"] = canonical["specification"]["unique_prd_requirement_ids"]
            model = canonical["model"]
            result[tool] = {
                "specification": spec,
                "source": canonical["source"],
                "gemini_tokens": {"transcript_files": model["transcript_files"], "model_responses": model["model_responses"], **{key: model[key] for key in TOKEN_KEYS}, "sessions": []},
                "runs": canonical["execution"]["runs"],
                "recorded_duration_seconds": canonical["execution"]["agent_seconds_including_failed_starts"],
                "recorded_prompt_count": canonical["execution"]["invocations"],
            }
            docs = tool_root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            (docs / "metrics-preliminary.json").write_text(json.dumps(result[tool], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            continue
        spec_paths = [path for relative in spec_dirs for path in files_in(tool_root / relative, {".md"})]
        source_paths = [
            path
            for relative in ("backend", "frontend")
            for path in files_in(tool_root / relative, SOURCE_EXTS)
        ]
        spec = text_counts(spec_paths)
        source = text_counts(source_paths)
        requirements = 0
        for path in spec_paths:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            requirements += len(re.findall(REQUIREMENT_PATTERNS[tool], content))
        spec["lines_per_file"] = round(spec["lines"] / spec["files"], 2) if spec["files"] else None
        spec["requirement_statements"] = requirements
        tokens = gemini_tokens(tool_root)
        if tokens["transcript_files"] == 0 and tool in snapshot:
            tokens = snapshot[tool]["gemini_tokens"]
        result[tool] = {
            "specification": spec,
            "source": source,
            "gemini_tokens": tokens,
            **run_metadata(tool_root),
        }
        docs = tool_root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "metrics-preliminary.json").write_text(
            json.dumps(result[tool], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (ROOT / "shared" / "metrics-preliminary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
