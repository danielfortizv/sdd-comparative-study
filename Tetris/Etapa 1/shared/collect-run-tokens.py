"""Record Gemini input/output traffic per CLI invocation from preserved evidence."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ("OpenSpec", "Spec Kit", "Tessl")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def stats_from_stdout(path: Path) -> dict[str, int] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError):
        return None
    models = data.get("stats", {}).get("models", {})
    if not models:
        return None
    return {
        "input_tokens": sum(int(model.get("tokens", {}).get("prompt") or 0) for model in models.values()),
        "output_tokens": sum(int(model.get("tokens", {}).get("candidates") or 0) for model in models.values()),
        "cached_tokens": sum(int(model.get("tokens", {}).get("cached") or 0) for model in models.values()),
        "model_responses": sum(int(model.get("api", {}).get("totalRequests") or 0) for model in models.values()),
    }


def records_for_tool(tool_root: Path) -> list[tuple[datetime, str, dict[str, int]]]:
    chat_root = tool_root / "docs" / "gemini-home" / ".gemini" / "tmp"
    records: dict[tuple[str, str], tuple[datetime, str, dict[str, int]]] = {}
    for path in chat_root.rglob("*.jsonl") if chat_root.exists() else []:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get("type") != "gemini" or not item.get("tokens"):
                continue
            timestamp = parse_time(item.get("timestamp"))
            if timestamp is None:
                continue
            key = (item.get("id") or "", item.get("timestamp") or "")
            records[key] = (timestamp, str(path.relative_to(tool_root)), item["tokens"])
    return list(records.values())


def main() -> None:
    rows = []
    prior = {}
    output = ROOT / "shared" / "token-sessions.csv"
    if output.exists():
        with output.open(encoding="utf-8", newline="") as file:
            prior = {(row["tool"], row["run"]): row for row in csv.DictReader(file)}
    for tool in TOOLS:
        tool_root = ROOT / tool
        records = records_for_tool(tool_root)
        for run_path in sorted((tool_root / "docs").glob("*.run.json")):
            run = json.loads(run_path.read_text(encoding="utf-8-sig"))
            started, ended = parse_time(run.get("started")), parse_time(run.get("ended"))
            stdout = Path(run["stdout"]) if run.get("stdout") else Path()
            tokens = stats_from_stdout(stdout) if stdout else None
            source = "CLI JSON stats" if tokens else "retained Gemini JSONL"
            if tokens is None and started and ended:
                relevant = [item for item in records if started <= item[0] <= ended]
                if relevant:
                    tokens = {
                        "input_tokens": sum(int(item[2].get("input") or 0) for item in relevant),
                        "output_tokens": sum(int(item[2].get("output") or 0) for item in relevant),
                        "cached_tokens": sum(int(item[2].get("cached") or 0) for item in relevant),
                        "model_responses": len(relevant),
                    }
            if tokens is None:
                archived = prior.get((tool, run_path.name))
                if archived and archived.get("input_tokens"):
                    source = "archived session evidence"
                    tokens = {key: archived[key] for key in ("input_tokens", "output_tokens", "cached_tokens", "model_responses")}
                else:
                    source = "unavailable"
                    tokens = {"input_tokens": None, "output_tokens": None, "cached_tokens": None, "model_responses": None}
            rows.append({
                "tool": tool,
                "run": run_path.name,
                "duration_seconds": run.get("duration_seconds"),
                "exit_code": run.get("exit_code"),
                "source": source,
                **tokens,
            })
    canonical = json.loads((ROOT / "shared" / "bmad-metrics.json").read_text(encoding="utf-8"))
    model = canonical["model"]
    rows.append({
        "tool": "Bmad Method",
        "run": "all 9 invocations (aggregate)",
        "duration_seconds": canonical["execution"]["agent_seconds_including_failed_starts"],
        "exit_code": "mixed; startup failure included",
        "source": "19 retained Gemini JSONL transcripts",
        "input_tokens": model["input"],
        "output_tokens": model["output"],
        "cached_tokens": model["cached"],
        "model_responses": model["model_responses"],
    })
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['tool']:12} {row['run']:44} {row['source']:22} {row['input_tokens']} / {row['output_tokens']}")


if __name__ == "__main__":
    main()
