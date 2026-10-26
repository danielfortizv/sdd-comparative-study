"""Inventory natural Kiro Say messages for explicit clarification adjudication."""
import re

from kiro_research import DOCS, interval_records, load, native_catalog, runs, stamp, stream_for_run, stream_session_ids, write


def main():
    review = load(DOCS / "question-review.json", {})
    rows = []
    for run in runs():
        records, _ = native_catalog(stream_session_ids(stream_for_run(run["label"])))
        interval = interval_records(run, records)
        messages = []
        interactions = []
        for record in sorted(interval, key=lambda r: (r["event"]["timestamp"], r["event"]["id"])):
            event, payload = record["event"], record["event"]["payload"]
            if payload.get("type") == "assistant" and payload.get("operationType") == "Say":
                content = payload.get("content", "")
                verdict = review.get(event["id"])
                messages.append({"session_id": record["session_id"], "message_id": event["id"], "timestamp": event["timestamp"], "content": content, "candidate": bool(re.search(r"\?|\b(?:please (?:choose|clarify|confirm)|could you|would you|which (?:option|approach))\b", content, re.I)), "manual_review": verdict, "transcript_copies": sorted(record["paths"])})
            elif payload.get("type") == "pending_interaction" and payload.get("interactionType") != "tool_approval":
                interactions.append({"session_id": record["session_id"], "message_id": event["id"], "timestamp": event["timestamp"], "interaction_type": payload.get("interactionType"), "question": payload.get("question"), "tool_call_id": payload.get("toolCallId")})
        complete = bool(messages) and all(isinstance(m["manual_review"], dict) and isinstance(m["manual_review"].get("is_blocking_clarification"), bool) for m in messages)
        rows.append({"label": run["label"], "process_exit_code": run.get("exit_code"), "natural_say_messages": messages, "review_complete": complete, "blocking_clarification_questions": sum(m["manual_review"]["is_blocking_clarification"] for m in messages) if complete else None, "nonblocking_review_confirmation_references": sum(bool(m["manual_review"].get("is_nonblocking_review_confirmation_reference")) for m in messages) if complete else None, "non_tool_approval_pending_interactions": interactions, "external_researcher_prompt_count": 1, "external_prompt_scope": "this invocation's explicit input; classification is in metrics, not a question emitted by Kiro"})
    data = {"researcher_created": True, "measured_at_utc": stamp(), "scope": "Kiro native assistant operationType=Say only; Reasoning, quoted tool results, requirements questions and automatic tool-approval prompts excluded from actual question counts. Candidate regex is only a review aid; no inferred zero from headless mode. Counts require manual message-ID adjudication.", "review_contract": "question-review.json maps message IDs to {is_blocking_clarification: true|false, reason: evidence-based note}; review all Say messages, not candidates only", "runs": rows, "pending_labels": [r["label"] for r in runs(include_pending=True) if not r["run_closed"]]}
    write(DOCS / "question-audit.json", data)
    text = ["# Auditoría de aclaraciones de Kiro", "", data["scope"], ""]
    for row in rows:
        count = row["blocking_clarification_questions"]
        text.extend([f"## {row['label']}", "", f"Mensajes Say: {len(row['natural_say_messages'])}; aclaraciones bloqueantes: {count if count is not None else 'desconocido; revisión manual pendiente'}.", ""])
        for message in row["natural_say_messages"]:
            if message["candidate"]:
                text.extend([f"- Candidato `{message['message_id']}` ({message['timestamp']}): {message['content']}", ""])
    (DOCS / "question-audit.md").write_text("\n".join(text), encoding="utf-8")
    print({"closed_runs": len(rows), "manual_review_pending": [r["label"] for r in rows if not r["review_complete"]]})


if __name__ == "__main__":
    main()
