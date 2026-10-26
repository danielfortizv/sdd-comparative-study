# Untouched Stage 1 tests against Stage 2 — researcher evidence

**Provisional while generation 04 is active.** The latest controlled run collected all **39 original Stage 1 tests** and returned pytest exit **1**: **38 passed, 1 failed**, with one inherited anyio/Starlette deprecation warning. No original expectation was changed, skipped, marked xfail or rewritten by the researcher.

## Real import and source provenance

Before pytest collection, the child process explicitly imported `app.main` from:

```text
D:/KEVIN/UNIVERSIDAD/Trabajos/Proyecto/Caso 2-Tetris/Etapa 2/Kiro/backend/app/main.py
```

All loaded `app.*` module paths were verified to be inside that Stage 2 backend. All collected test-function code filenames point at the original `Proyecto/.../Etapa 1/Kiro/backend/tests` source files. Original test SHA-256 values were unchanged before/after:

- `test_api.py`: `C3BF981F0F1F2277ABC83F94ABFD2BBFA10BF97492C55B5B8F6A5BF7B307860D`.
- `test_rules.py`: `3DC7B6921EAD493CCBCA1022B11054C84A1D097B8248364D19118868DA586451`.
- The original `tests/__init__.py` is also hashed in the run JSON.

Stage 2 application hashes were stable during this run. These results must be revalidated if Kiro subsequently changes the application.

## One expectation intentionally conflicts with the new stage

The sole failing case is the original `test_api.py::test_state_payload_shape`, line 86:

```python
assert set(data.keys()) == {"id", "status", "board", "active_piece"}
```

This is a **closed four-key Stage 1 schema assertion**. The frozen Stage 2 seed mandates seven additional state fields: `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_piece`, `hold_piece` and `can_hold`. A conforming Stage 2 response therefore cannot also satisfy this original exact-key equality. The failure is retained unchanged as an expected stage-contract incompatibility; it is not silently counted as a pass or treated as a missing required feature. The other 38 original tests passed without modification.

For S2-19, report **38 unchanged legacy tests passed; one unchanged legacy closed-schema expectation is incompatible with the seven mandatory added fields**. Do not claim 39/39 untouched legacy tests passed. A separate Stage 2 schema test can verify the complete required new contract without altering this archived original evidence.

## Isolation and retained files

Runner: `Etapa 2/shared/check-kiro-original-regressions.py`. It uses the Stage 2 Kiro venv Python, `-B`, `PYTHONDONTWRITEBYTECODE=1`, an empty external `PYTHONPYCACHEPREFIX`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `--import-mode=importlib` and `-p no:cacheprovider`. The external pycache prefix did not exist after execution: neither original bytecode nor pytest cache was written, and old relocated `.pyc` files were not read. Application coverage and the external hook-race reports were not replaced.

- `original-tests-run.json`: argv, cwd, times, exit, controls, test/app hashes before/after.
- `original-tests-results.json`: actual module imports, source filenames, collection and per-case outcomes.
- `stdout.log` and `stderr.log`: raw execution output.
- `previous-runs/`: earlier retained attempt before pycache-read isolation was added; same 38/1 result, not used as the final provenance check.

No Git, Sonar scan, model invocation, power action or application/test/specification edit was performed by this check.
