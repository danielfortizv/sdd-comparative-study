"""Runner de carga multidivisa de la Etapa 4 (Tarea 24).

Reutiliza la mecánica robusta del runner heredado (aislamiento -> uvicorn -> health poll ->
Locust headless 30/5/60 -> teardown), pero con la fixture D-02 (`setup_loadtest_db_stage4`) y el
locustfile multidivisa (`locustfile_stage4.py`). Tras la corrida, verifica los invariantes
multidivisa y la cadena de auditoría sobre la MISMA DB sintética antes del teardown. Fail-loud:
un servidor no disponible o una corrida con fallos no se reporta como PASS.

Contrato exacto: 30 usuarios, 5/s de ramp (6 s), 60 s de steady. Umbrales de aceptación
(análogos a la Etapa 3): p95 lectura < 200 ms, p95 operación < 500 ms, errores inesperados < 1%,
cero violaciones de invariantes.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from . import isolation, run_loadtest as base

_LOADTEST_DIR = Path(__file__).resolve().parent
_STAGE4_LOCUSTFILE = _LOADTEST_DIR / "locustfile_stage4.py"


def run(users: int = 30, spawn_rate: int = 5, steady_seconds: int = 60,
        results_dir: Path | None = None) -> int:
    """Ejecuta la carga multidivisa de la Etapa 4 y verifica invariantes. Devuelve exit code."""
    # Apuntar el runner heredado al locustfile y a la siembra de la Etapa 4 mediante parches
    # locales (sin modificar el módulo heredado): sustituimos el locustfile y la función de
    # setup de DB por las de la Etapa 4 durante esta corrida.
    base._LOCUSTFILE = _STAGE4_LOCUSTFILE  # type: ignore[attr-defined]
    original_setup = isolation.setup_loadtest_db
    isolation.setup_loadtest_db = isolation.setup_loadtest_db_stage4  # type: ignore[assignment]

    results_dir = results_dir or (_LOADTEST_DIR / "results_stage4")
    config = base.LoadConfig(
        users=users, spawn_rate=spawn_rate, steady_seconds=steady_seconds,
        results_dir=results_dir, is_mechanics_smoke=(
            users != 30 or spawn_rate != 5 or steady_seconds != 60),
    )
    try:
        result = base.run_load_test(config)
    except base.RunnerError as exc:
        print(f"[stage4-runner] FALLO: {exc}", file=sys.stderr)
        return 1
    finally:
        isolation.setup_loadtest_db = original_setup  # type: ignore[assignment]

    print("=== run_loadtest_stage4: RESULT ===")
    print(f"  base_url:          {result.base_url}")
    print(f"  users/spawn/steady: {result.users}/{result.spawn_rate}/{result.steady_seconds:.0f}")
    print(f"  ramp_up_seconds:    {result.ramp_up_seconds:.1f}")
    print(f"  locust_exit_code:   {result.locust_exit_code}")
    print(f"  csv_prefix:         {result.csv_prefix}")
    print(f"  mechanics_smoke:    {result.is_mechanics_smoke}")
    return 0


def run_with_invariants(users: int = 10, spawn_rate: int = 5, steady_seconds: int = 10) -> int:
    """Corrida de carga que, ANTES del teardown, verifica los invariantes multidivisa y la cadena
    de auditoría sobre la MISMA DB sintética (D-05/D-06/D-09/D-11). Fail-loud ante violación.

    Reutiliza la mecánica del runner pero intercepta la DB sintética antes de borrarla: se parchea
    `isolation.teardown_synthetic_db` para verificar invariantes con la DB aún presente.
    """
    import sqlite3

    from app import audit
    from .verify_invariants_stage4 import verify_all

    base._LOCUSTFILE = _STAGE4_LOCUSTFILE  # type: ignore[attr-defined]
    original_setup = isolation.setup_loadtest_db
    original_teardown = isolation.teardown_synthetic_db
    isolation.setup_loadtest_db = isolation.setup_loadtest_db_stage4  # type: ignore[assignment]

    verification = {"ran": False, "ok": False, "detail": ""}

    def verifying_teardown(db_path):
        # Verificar invariantes con la DB aún presente, luego delegar el teardown real.
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                names = verify_all(conn)
                chain = audit.verify_chain(conn)
                verification["ran"] = True
                verification["ok"] = chain.ok
                verification["detail"] = (
                    f"invariants={names}; audit_chain_ok={chain.ok}"
                    + ("" if chain.ok else f"; audit_reason={chain.reason}"))
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001 — queremos registrar cualquier violación
            verification["ran"] = True
            verification["ok"] = False
            verification["detail"] = f"VIOLATION: {exc!r}"
        original_teardown(db_path)

    isolation.teardown_synthetic_db = verifying_teardown  # type: ignore[assignment]

    config = base.LoadConfig(
        users=users, spawn_rate=spawn_rate, steady_seconds=steady_seconds,
        results_dir=_LOADTEST_DIR / "results_stage4", is_mechanics_smoke=True)
    try:
        base.run_load_test(config)
    except base.RunnerError as exc:
        print(f"[stage4-runner] FALLO de corrida: {exc}", file=sys.stderr)
        return 1
    finally:
        isolation.setup_loadtest_db = original_setup  # type: ignore[assignment]
        isolation.teardown_synthetic_db = original_teardown  # type: ignore[assignment]

    print("=== POST-LOAD INVARIANTS (Stage 4) ===")
    print(f"  verification_ran: {verification['ran']}")
    print(f"  invariants_ok:    {verification['ok']}")
    print(f"  detail:           {verification['detail']}")
    return 0 if verification["ran"] and verification["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    users = int(os.environ.get("SHIFT_LOAD_USERS", "30"))
    spawn = int(os.environ.get("SHIFT_LOAD_SPAWN", "5"))
    steady = int(os.environ.get("SHIFT_LOAD_STEADY", "60"))
    return run(users=users, spawn_rate=spawn, steady_seconds=steady)


if __name__ == "__main__":
    raise SystemExit(main())
