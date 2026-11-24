# Spec Kit — Stage 1 Timing

## Recorded Gemini sessions

| Session | Purpose | Wall time | Agent active | API time | Tool time |
|---|---|---:|---:|---:|---:|
| 001 | Spec Kit planning | 1h 6m 7s | 22m 55s | 11m 40s | 11m 15s |
| 002 | Implementation + validation | 1h 43m 53s | 30m 42s | 23m 25s | 7m 17s |
| 003 | Final validation + implementation correction | 24m 24s | 17m 42s | 8m 26s | 9m 15s |
| 004 | Final implementation validation | 17m 52s | 15m 39s | 12m 43s | 2m 55s |
| 005 | Final documentation / validation work | 1h 10m 14s | 9m 3s | 7m 29s | 1m 33s |

## Aggregate recorded wall time

**4h 42m 30s**

This value is the sum of the recorded Gemini session wall times. It includes waiting between interactions and therefore does not represent pure model computation time or continuous human work.

## Interaction counts

- Total tool calls: **412**
- Successful tool calls: **408**
- Failed tool calls: **4**
- Overall recorded success rate: **99.0%**

## Notes

- Manual browser validation is separate from Gemini session timing.
- SonarQube execution time is also separate from Gemini timing.
- OpenSpec session metrics are intentionally excluded from this file.
- Human correction rounds are recorded separately in `03_corrections.md`.