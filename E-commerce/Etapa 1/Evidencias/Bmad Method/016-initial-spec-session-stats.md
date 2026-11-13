# Initial BMAD Specification Session Statistics

- Run ID: `BMAD-S1-OFFICIAL-01`
- Gemini session ID: `d0021d68-5631-4f66-9c77-ad099cacb39f`
- Auth method: Vertex AI
- Model: `gemini-3.5-flash`
- CLI version: `0.60.0`
- Source statistics attachment SHA-256: `C34B612A97E74B005AED87704D915183CA9B2EAB11E1D767FB4D1A3C86C0E0B2`

## Interaction and tool summary

| Metric | Value |
|---|---:|
| Model requests | 25 |
| Model errors | 0 |
| Average latency | 9.7 s |
| Tool calls | 22 |
| Successful tool calls | 22 |
| Failed tool calls | 0 |
| Tool success rate | 100% |
| User agreement | 100% over 22 reviewed operations |
| Protocol-counted user interactions | 4 |

The 25 model requests are provider requests, not protocol-counted user interactions. `/stats` and `/stats model` are operational measurement commands and do not add a functional/technical interaction.

## Token consumption

The CLI uses dots as thousands separators in the pasted display.

| Metric | Value |
|---|---:|
| Uncached input tokens | 534527 |
| Cached input tokens | 406865 |
| Total input including cache | 941392 |
| Thought tokens | 12421 |
| Output tokens | 14364 |
| Total tokens | 968177 |

Reconciliation: `534527 + 406865 + 12421 + 14364 = 968177`.

All 25 requests were attributed to the `main` role using `gemini-3.5-flash`; no auxiliary-model requests were reported.

## Time

| Metric | Value |
|---|---:|
| Wall time | 39m 40s |
| Agent active time | 5m 5s (305 seconds) |
| API time | 4m 2s |
| Tool time | 1m 3s |

## Credits and cost

- Credits: `N/A - not exposed` by the captured Gemini CLI statistics.
- Actual cost: `N/A - not exposed`; requires directly attributable Vertex AI billing evidence.

## Change telemetry

Gemini CLI reported `+746 / -74`. This is retained only as CLI change telemetry and is not application LOC. Independent inspection found no application source code; the generated changes were planning/tracking artifacts.
