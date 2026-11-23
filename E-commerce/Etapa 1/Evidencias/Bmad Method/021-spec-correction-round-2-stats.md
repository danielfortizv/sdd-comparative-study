# BMAD Specification Correction Round 2 Statistics

- Run ID: `BMAD-S1-OFFICIAL-01`
- Session ID: `d0021d68-5631-4f66-9c77-ad099cacb39f`
- Model: `gemini-3.5-flash`
- Auth: Vertex AI
- Source attachment SHA-256: `5D79DCAF68FD5F1A3B622CDDC2A6DE98190E16861C5D291CF6583764463EB67B`

## Cumulative checkpoint after round 2

| Metric | Value |
|---|---:|
| Requests | 36 |
| Errors | 0 |
| Uncached input tokens | 687077 |
| Cached input tokens | 1021942 |
| Total input including cache | 1709019 |
| Thought tokens | 16430 |
| Output tokens | 20920 |
| Total tokens | 1746369 |
| Tool calls | 32 successful, 0 failed |
| Wall time | 1h 1m 49s |
| Agent active time | 8m 13s |
| API time | 7m 10s |
| Tool time | 1m 3s |
| CLI change telemetry | +1114 / -672 |

## Increment attributable to specification correction round 2

Calculated as this cumulative checkpoint minus the initial-specification checkpoint.

| Metric | Round-2 increment |
|---|---:|
| Requests | 11 |
| Errors | 0 |
| Uncached input tokens | 152550 |
| Cached input tokens | 615077 |
| Total input including cache | 767627 |
| Thought tokens | 4009 |
| Output tokens | 6556 |
| Total tokens | 778192 |
| Tool calls | 10 successful, 0 failed |
| Wall time | 22m 9s |
| Agent active time | 3m 8s (188 seconds) |
| API time | 3m 8s |
| Tool time | 0s incremental according to rounded CLI values |
| CLI change telemetry | +368 / -598 |

Credits and actual cost remain `N/A - not exposed`. All 36 cumulative requests were attributed to the main `gemini-3.5-flash` role; no auxiliary model was reported.
