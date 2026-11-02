# Researcher acceptance harness calibration — HTTP creation status

## Version preservation

The original checkers remain byte-for-byte unchanged because prior OpenSpec/Spec Kit evidence and report verification reference them:

| File | Version | SHA-256 |
| --- | --- | --- |
| `check_api.py` | 1.1 | `8A45D6B0E8EFA52F12605C262664409E51759EF0CCCF12B88D12A3B7FC7ADC4E` |
| `check_contract.py` | 1.0 | `D56C6289EC858B160A467676B44DCEDE45DC4D852D439F9213D63EC109FB45A4` |

The new files are `check_api_v1_2.py` and `check_contract_v1_1.py`. Both accept `--created-status {200,201}`, defaulting to **201**, and check the actual HTTP status for exact equality with that configured expectation. There is no status conversion, silent 2xx acceptance, or application change. The new API checker applies the same configured status to creation and restart, which both use POST `/api/games`.

Each output records the expected create status, actual observed create status(es), `http_status_normalization: false`, measured time, and checker hash. The API output additionally retains every actual HTTP response status. The new contract supplement imports `call`, `check`, and `board_valid` from **the new API checker**, and records its imported file hash. Its controls retain both actual and expected status values, including a failing observation before rethrowing an assertion/network error; the existing atexit mechanism writes overall failure evidence if completion is interrupted by an exception.

## Why Tessl explicitly uses 200

This is a brownfield study. The frozen Stage 2 seed says to keep existing endpoints compatible and starts each tool from its own Stage 1 output; it does not mandate a new creation status. Tessl's original route in `Etapa 1/Tessl/backend/app/controllers/games.py` uses `@router.post("", response_model=GameStateModel)` with the default FastAPI HTTP 200 response. `test_grid_dimensions` and `test_spawning_and_coordinate_calculations` in `backend/tests/test_game.py` explicitly assert 200. Those unchanged tests were re-executed successfully in the fresh Stage 2 baseline (9 backend tests passed; see `Etapa 2/Tessl/docs/baseline-backend-coverage.log`).

Therefore the Tessl run will pass **`--created-status 200`** explicitly, and its acceptance output must retain the actual value **200**. Existing evidence for prior tools remains associated with its original checker version and actual HTTP 201. For any later tool, inspect its own unchanged Stage 1 creation contract before choosing this argument; do not infer its contract from the tool's name.

This calibration changes the researcher harness only. It does not change the frozen seed, require a source/test/specification edit, or excuse a mismatch between Tessl's inherited HTTP 200 contract and its Stage 2 implementation.

## Tessl route and field observations

There is **no route remapping** required for Tessl:

| Operation | Method and route | Expected HTTP status for Tessl |
| --- | --- | ---: |
| Create/restart | POST `/api/games` | 200 |
| Read existing game | GET `/api/games/{id}` | 200 |
| Gravity | POST `/api/games/{id}/tick` | 200 |
| Move | POST `/api/games/{id}/move` | 200 |
| Hold (new Stage 2 route) | POST `/api/games/{id}/hold` | 200 |
| Unknown game | GET or corresponding POST route | 404 |

The existing move payload is `{"direction":"left"|"right"|"down"}`. The inherited active-piece JSON key is **`active_piece`**; the new API checker retains v1.1's existing lookup support for that spelling and Spec Kit's `activePiece`, without changing the raw returned JSON. Tessl's canonical spawn origin is `[0,3]`, within the existing shared top-centered spawn check. No other route or payload adaptation was introduced.

Tessl's inherited Vite development port is **3000**, with `/api` proxied to `http://localhost:8000`. This concerns local browser launch, not the black-box API route contract; the checker `--base-url` points directly at the owned backend origin. The optional GET `/` welcome message is outside the Stage 2 acceptance catalog and is not a replacement for a game endpoint check.

## Execution and scope

Tessl commands to run **after the Stage 2 implementation exists and its owned backend is started**:

```text
python check_api_v1_2.py --base-url http://127.0.0.1:8000 --created-status 200 --output <Tessl/docs/acceptance-api.json>
python check_contract_v1_2.py --base-url http://127.0.0.1:8000 --created-status 200 --output <Tessl/docs/acceptance-contract.json>
```

Only command-line `--help`, syntax parsing and hash preservation were verified while preparing this calibration. Neither checker has been run against an absent Stage 2 implementation, and this document declares no Stage 2 acceptance pass.

The API checker keeps the same **seven records covering eight catalog IDs** as v1.1. The supplemental **nine HTTP controls** remain evidence for **S2-16**, not nine extra catalog requirements. Neither helper alone proves all twenty Stage 2 acceptance cases; deterministic domain, UI, timer/race, build and quality evidence remain separate.
