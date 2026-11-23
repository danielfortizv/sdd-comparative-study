# Shift Bank Stage 3 Kiro — D1 telemetry recovery

Generated 2026-11-17 from the original Kiro session archive and Stage 3 experiment logs. This is a derived metrics record; source evidence was not altered.

## Scope

Stage 3 starts at researcher message 835f6c6d-83ba-4099-97a0-9c89bd220833, timestamp 2026-11-16T19:36:25.080Z, in native Kiro session sess_7f1b54d0-e77f-4cb7-b439-d06e5aa2dca1. The session was created for the parent Shift Bank workspace and includes other stage activity before this boundary. The D1 count filters the message stream at that Stage 3 boundary. Session lastModifiedAt is 2026-11-17T20:59:17.269Z.

## Metrics

See E3_KIRO_D1_METRICAS.csv. The file records value, unit, completeness and calculation/limitation per metric.

Kiro's native usage summaries expose credits and elapsed milliseconds. The 14 summaries total 201.92953451393 credits and 12,417,229 ms. These are partial coverage because the Stage 3 segment contains 15 recorded turns and only 14 usage summaries. The archive has no token totals or USD cost; both are N/D. No token or credit estimate was derived from text length.

The wall-clock span is 25:22:52.189 and includes idle time between turns. Kiro-reported elapsed processing sums to 03:26:57.229 across available summaries; it is distinct from wall-clock time and partial.

There are 15 researcher messages, 459 recorded main-session tool calls, and 36 sub-agent starts matched by 36 completions. Child-agent detailed tool-call events are not available in this archive stream. The event log records 368 pending interactions and 367 resolutions (one remains unmatched). It records 31 unsuccessful tool results, two of which correspond to explicitly denied command requests. A canonical retry counter is absent. The T34 prompt explicitly authorizes one bounded corrective pass; corrective-round count is therefore partial and based on that prompt.

## Reproduction

Parse messages.jsonl as one JSON object per line. Select records whose timestamp is greater than or equal to the Stage 3 opening timestamp above. Count payload.type values and tool-call statuses from the selected records. For elapsed processing, sum payload.elapsedTime for selected usage_summary records. For credits, sum promptTurnSummaries[].usage only where unit equals credit. Compute wall-clock span by subtracting the opening timestamp from session.json.lastModifiedAt. Round no raw telemetry values before calculating; the displayed time values convert summed milliseconds to HH:MM:SS.mmm.

## Evidence boundary

The archive files remain in the user's Kiro profile and are referenced, not copied or rewritten. SHA-256 hashes, exact paths, event IDs, and line references are in E3_KIRO_D1_EVIDENCE_MANIFEST.md. Existing experiment logs are cited as contextual cross-checks, not as substitutes for original Kiro telemetry.

Completeness labels mean:
- complete: count/value is directly present and fully counted within the defined Stage 3 segment.
- partial: source record exists but coverage is incomplete or the interpretation is bounded.
- unavailable: source telemetry does not provide the metric.
- estimated: no metric here is estimated.
