# Post-implementation session statistics and isolated implementation delta

## Raw same-session `/stats` output

```text
Session Stats

Interaction Summary
Session ID:                 2d7e4fb4-4b5f-45a8-9202-a09fdbd6986d
Auth Method:                vertex-ai
Tool Calls:                 50 (49 successful, 1 failed)
Success Rate:               98.0%
User Agreement:             100.0% (50 reviewed)
Code Changes:               +1901 -176

Performance
Wall Time:                  1h 1m 30s
Agent Active:               17m 14s
  API Time:                 12m 35s (73.1%)
  Tool Time:                4m 38s (26.9%)

Model                           Reqs  Input Tokens   Cache Reads  Output Tokens
gemini-3.1-flash-lite              1           873             0             12
  utility_summarizer               1           873             0             12
gemini-3.5-flash                  57     3,283,251     2,582,604         35,454
  main                            57     3,283,251     2,582,604         35,454
gemini-3-flash-preview             1        24,182             0             95
  utility_loop_detector            1        24,182             0             95
```

The formatting separators shown by Gemini as periods in the Spanish/locale-rendered terminal were normalized above as thousands separators, not decimal points.

## Planning checkpoint subtracted

The implementation began after evidence `045-implementation-planning-session-stats.md`. That checkpoint recorded:

| Metric | Checkpoint value |
|---|---:|
| Main-model requests | 25 |
| Main-model input tokens | 134,799 |
| Main-model cached input tokens | 624,539 |
| Main-model output tokens | 15,431 |
| Utility summarizer requests | 1 |
| Utility summarizer input/output | 873 / 12 |
| Tool calls | 20 (19 successful, 1 failed) |
| Agent active time | 501 seconds |
| Wall time | 2,274 seconds |

## Implementation-only delta

Calculated as the post-implementation cumulative value minus the planning checkpoint:

| Metric | Calculation | Implementation-only result |
|---|---|---:|
| Input tokens | `(3,283,251 - 134,799) + 24,182` | **3,172,634** |
| Cached input tokens | `2,582,604 - 624,539` | **1,958,065** |
| Output tokens | `(35,454 - 15,431) + 95` | **20,118** |
| Model requests | `(57 - 25) + 1 loop-detector request` | **33** |
| Tool calls | `50 - 20` | **30** |
| Successful tool calls | `49 - 19` | **30** |
| Failed tool calls | `1 - 1` | **0** |
| Agent time | `1,034 - 501` seconds | **533 seconds (00:08:53)** |
| Wall time | `3,690 - 2,274` seconds | **1,416 seconds (00:23:36)** |

The unchanged utility-summarizer row contributes zero to the implementation delta. The new loop-detector request is included because it appeared after the implementation checkpoint and consumed reported tokens.

## Run-level fields not derived from this delta

- Technical/functional user interactions through first implementation: **14**. The `/stats` command is an operational measurement command and is not counted as an interaction under the protocol.
- Credits: **N/A - not exposed** in the supplied `/stats` output.
- Actual billed cost: **N/A - included in subscription / not directly attributable from supplied evidence**.
- Normalized cost: **N/A - no documented per-credit value and no credit consumption exposed for this Gemini/Vertex AI session**.

