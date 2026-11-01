"""Compare intended Kiro prompts with native received user messages, never ACP output."""
from kiro_research import DOCS, digest, interval_records, native_catalog, read, runs, seed_info, stamp, stream_for_run, stream_session_ids, write


def text_fields(text):
    normalized = text.replace("\r\n", "\n")
    return {"raw_utf8_sha256": digest(text), "raw_characters": len(text), "normalized_utf8_sha256": digest(normalized), "normalized_characters": len(normalized)}


def main():
    seed, seed_meta = seed_info()
    measured_at = stamp()
    rows = []
    for run in runs(include_pending=True):
        stream = stream_for_run(run["label"])
        sids = stream_session_ids(stream)
        records, invalid = native_catalog(sids)
        selected = interval_records(run, records, measured_at)
        users = sorted([r for r in selected if r["event"]["payload"].get("type") == "user" and isinstance(r["event"]["payload"].get("content"), str)], key=lambda r: r["event"]["timestamp"])
        intended_path = DOCS / f"{run['label']}.prompt.txt"
        # Preserve intended CRLF; universal-newline source reads erase it.
        intended = intended_path.read_bytes().decode("utf-8-sig") if intended_path.exists() else None
        row = {"label": run["label"], "run_closed": run["run_closed"], "session_ids": sids, "intended_prompt_file": intended_path.name if intended is not None else None, "intended_prompt_file_bytes_sha256": digest(intended_path.read_bytes()) if intended is not None else None, "intended_prompt": text_fields(intended) if intended is not None else None, "intended_seed_present": seed in intended.replace("\r\n", "\n") if intended is not None else None, "effective_user_messages": [], "complete_seed_in_effective_submission": None, "delivery_status": "unverified: native received user-message record unavailable", "invalid_native_lines": invalid, "scope": "closed invocation interval" if run["run_closed"] else "pending invocation input check only; no usage closure"}
        for record in users:
            event = record["event"]
            text = event["payload"]["content"]
            normalized = text.replace("\r\n", "\n")
            row["effective_user_messages"].append({"session_id": record["session_id"], "message_id": event["id"], "timestamp": event["timestamp"], **text_fields(text), "complete_seed_present": seed in normalized, "seed_paragraphs_present": [i+1 for i,p in enumerate(seed.split("\n\n")) if p in normalized], "matches_intended_normalized": intended.strip().replace("\r\n", "\n") in normalized if intended is not None else None, "transcript_copies": sorted(record["paths"]), "conflict": record["conflict"]})
        matches = [r for r in row["effective_user_messages"] if r["matches_intended_normalized"] and not r["conflict"]]
        if matches:
            row["complete_seed_in_effective_submission"] = any(r["complete_seed_present"] for r in matches)
            row["delivery_status"] = "verified full seed in received intended user message" if row["complete_seed_in_effective_submission"] else "received intended message observed but full seed absent"
        reads = [r for r in selected if r["event"]["payload"].get("type") == "tool_result" and isinstance(r["event"]["payload"].get("content"), str) and seed in r["event"]["payload"]["content"].replace("\r\n", "\n")]
        row["complete_seed_tool_reads"] = [{"session_id": r["session_id"], "message_id": r["event"]["id"], "timestamp": r["event"]["timestamp"], "tool_call_id": r["event"]["payload"].get("toolCallId"), "success_flag": r["event"]["payload"].get("success"), "transcript_copies": sorted(r["paths"])} for r in reads]
        rows.append(row)
    result = {"researcher_created": True, "measured_at_utc": measured_at, **seed_meta, "normalization": "Raw hashes/lengths preserve decoded native content; normalized fields replace CRLF with LF only; intended comparison trims outer whitespace", "scope": "Native Kiro messages.jsonl user payloads by session/message ID/timestamp within launcher interval; original/archive duplicates cannot inflate counts; intended prompt alone is not received-input evidence; ACP output does not echo user input", "runs": [r for r in rows if r["run_closed"]], "pending_runs": [r for r in rows if not r["run_closed"]]}
    write(DOCS / "input-audit.json", result)
    print({"closed_runs": len(result["runs"]), "pending": [r["label"] for r in result["pending_runs"]], "verified": [r["label"] for r in rows if r["complete_seed_in_effective_submission"]]})


if __name__ == "__main__":
    main()
