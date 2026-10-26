"""Audit BMAD intended/effective inputs, with active input delivery separate from closed usage."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def timestamp(raw):
    raw = re.sub(r"(\.\d{6})\d+", r"\1", raw.replace("Z", "+00:00"))
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def user_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("text", "")
    if isinstance(content, list):
        # Function-response-only user records are not human prompt text.
        return "\n".join(item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str))
    return ""


def transcript_records(docs, seed):
    """Deduplicate user messages and complete seed reads across archive copies."""
    inputs, reads = {}, {}
    for folder in (docs / "gemini-home", docs / "transcripts-archive"):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.jsonl")):
            session = path.stem
            relative_path = path.relative_to(docs).as_posix()
            for line in path.open(encoding="utf-8-sig", errors="replace"):
                try:
                    event = json.loads(line)
                    if event.get("sessionId"):
                        session = event["sessionId"]
                    if event.get("type") != "user":
                        continue
                    when = timestamp(event["timestamp"])
                    content = event.get("content", [])
                    text = user_text(content)
                    if text:
                        identity = (session, event.get("id") or (event["timestamp"], sha256(text)))
                        if identity not in inputs:
                            inputs[identity] = {"when": when, "timestamp": event["timestamp"], "session": session, "message_id": event.get("id"), "text": text, "paths": {relative_path}}
                        else:
                            inputs[identity]["paths"].add(relative_path)
                    if isinstance(content, list):
                        for item in content:
                            response = item.get("functionResponse", {}) if isinstance(item, dict) else {}
                            output = response.get("response", {}).get("output", "")
                            if isinstance(output, str) and seed in output.replace("\r\n", "\n"):
                                identity = (session, event.get("id") or event["timestamp"], response.get("name"), sha256(output))
                                if identity not in reads:
                                    reads[identity] = {"when": when, "timestamp": event["timestamp"], "session": session, "tool": response.get("name"), "paths": {relative_path}}
                                else:
                                    reads[identity]["paths"].add(relative_path)
                except (ValueError, KeyError, TypeError):
                    continue
    return list(inputs.values()), list(reads.values())


def preferred_path(paths):
    return sorted(paths, key=lambda path: (not path.startswith("gemini-home/"), path))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", default="Bmad Method")
    args = parser.parse_args()
    stage = Path(__file__).resolve().parent.parent
    docs = stage / args.tool / "docs"
    seed_path = stage / "shared/seed.md"
    seed = "\n".join(re.sub(r"^> ?", "", line) for line in seed_path.read_text(encoding="utf-8-sig").splitlines() if line.startswith(">")).strip()
    paragraphs = seed.split("\n\n")
    first_inputs, tool_seed_reads = transcript_records(docs, seed)
    rows = []
    measured_at = datetime.now(timezone.utc)
    closed_paths = sorted(docs.glob("*.run.json"))
    closed_names = {path.name.removesuffix(".run.json") for path in closed_paths}
    pending_paths = [path for path in sorted(docs.glob("*.started.json")) if path.name.removesuffix(".started.json") not in closed_names]
    for path in closed_paths + pending_paths:
        run = json.loads(path.read_text(encoding="utf-8-sig"))
        run_closed = path.name.endswith(".run.json")
        if not run_closed:
            run["ended"] = measured_at.isoformat()
        row = {"run_closed": run_closed, "input_interval_scope": "closed run interval" if run_closed else "active input-delivery check only; observed until audit time; no usage closure claim", "observed_interval_end_at_utc": run["ended"] if not run_closed else None, "label": run["label"], "submission_method": run.get("submission_method", "headless slash parser" if run.get("workflow", run.get("category")) != "clarify" else "direct clarification"), "model_started": run.get("model_started")}
        if not run.get("started") or not run.get("ended"):
            row["effective_first_input"] = "no recorded run interval"
            rows.append(row)
            continue
        start, end = timestamp(run["started"]), timestamp(run["ended"])
        matches = [entry for entry in first_inputs if start <= entry["when"] <= end]
        if matches:
            first = min(matches, key=lambda entry: (entry["when"], preferred_path(entry["paths"])))
            raw = first["text"]
            normalized = raw.replace("\r\n", "\n")
            reads = [entry for entry in tool_seed_reads if entry["session"] == first["session"] and start <= entry["when"] <= end]
            row.update({
                "transcript": preferred_path(first["paths"]),
                "transcript_copies": sorted(first["paths"]),
                "session_id": first["session"],
                "effective_first_input_timestamp": first["timestamp"],
                "effective_first_input_sha256": sha256(raw),
                "effective_first_input_characters": len(raw),
                "effective_first_input_raw_utf8_sha256": sha256(raw),
                "effective_first_input_raw_characters": len(raw),
                "effective_first_input_normalized_utf8_sha256": sha256(normalized),
                "effective_first_input_normalized_characters": len(normalized),
                "complete_seed_present": seed in normalized,
                "seed_paragraphs_present": [index + 1 for index, paragraph in enumerate(paragraphs) if paragraph in normalized],
                "complete_seed_tool_reads": [{"timestamp": entry["timestamp"], "tool": entry["tool"], "transcript_copies": sorted(entry["paths"])} for entry in sorted(reads, key=lambda entry: (entry["when"], entry["tool"] or ""))],
            })
        else:
            row["effective_first_input"] = "no transcript input observed"
        prompt_path = docs / f"{run['label']}.prompt.txt"
        if prompt_path.exists():
            intended = prompt_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
            submitted = [entry for entry in matches if intended and intended in entry["text"].replace("\r\n", "\n")]
            row["intended_submission_prompt"] = prompt_path.name
            row["effective_submission_matches"] = [{
                "message_id": entry.get("message_id"), "timestamp": entry["timestamp"], "session_id": entry["session"],
                "transcript_copies": sorted(entry["paths"]),
                "raw_utf8_sha256": sha256(entry["text"]), "raw_characters": len(entry["text"]),
                "normalized_utf8_sha256": sha256(entry["text"].replace("\r\n", "\n")),
                "normalized_characters": len(entry["text"].replace("\r\n", "\n")),
                "complete_seed_present": seed in entry["text"].replace("\r\n", "\n"),
            } for entry in sorted(submitted, key=lambda entry: entry["when"])]
            row["complete_seed_in_effective_submission"] = any(item["complete_seed_present"] for item in row["effective_submission_matches"])
            row["submission_match_scope"] = "Exact normalized intended prompt is contained in an actual user-message record within the invocation interval. Separate from the first user-like record, which may be synthetic CLI context or replayed history during resume. Does not infer omitted records."
        rows.append(row)
    closed_labels = {row["label"] for row in rows if row["run_closed"]}
    result = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest().upper(),
        "seed_sha256_scope": "original bytes of the complete common seed Markdown file",
        "seed_block_utf8_sha256": sha256(seed),
        "seed_block_characters": len(seed),
        "seed_block_scope": "extracted quoted common seed block, trimmed, with LF line endings, encoded as UTF-8 without BOM",
        "effective_input_hash_scope": "decoded JSONL user text before newline normalization; effective_first_input_sha256/characters are aliases of raw fields. Multiple text parts, when present, are joined with LF.",
        "normalization": "CRLF replaced with LF only; normalized hash/character fields are separate from raw decoded text",
        "transcript_scope": "original gemini-home and transcripts-archive fallback; user-message identities and complete seed-read identities deduplicated across snapshots",
        "snapshot_scope": "runs contains closed intervals only; pending_runs separately verifies active input delivery and never supplies usage totals",
        "unclosed_invocation_labels": [path.name.removesuffix(".started.json") for path in sorted(docs.glob("*.started.json")) if path.name.removesuffix(".started.json") not in closed_labels],
        "note": "Checks the first effective user text, not all later context. Complete seed tool reads require an exact normalized seed substring in a string output from the same session within that run interval. Missing records or absent first-message seed do not prove the seed was never available through other context.",
        "runs": [row for row in rows if row["run_closed"]],
        "pending_runs": [row for row in rows if not row["run_closed"]],
    }
    (docs / "input-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
