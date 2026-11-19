"""Orquestador del PRIMER BASELINE de carga (Etapa 3, Tarea 23).

design.md §3.3, §8 G7 · requirements R9.5, R9.6, R10.4, R10.5, R16.1 · AC-11, AC-16.

Por qué este módulo (y no `run_loadtest.main` directo)
------------------------------------------------------
La Tarea 23 exige, en una sola corrida válida:

  1. Ejecutar el baseline REAL con la configuración exacta D-E3-03 (30 usuarios / 5 por
     segundo / 60 s steady tras el ramp-up de 6 s), reutilizando el arnés existente
     (`isolation` + `_spawn_uvicorn` + `_spawn_locust`).
  2. Verificar los invariantes financieros (Tarea 22) SOBRE LA MISMA DB sintética que
     recibió el tráfico, ANTES del teardown. El runner de la Tarea 20 (`run_load_test`)
     elimina la DB sintética en su `finally`, de modo que no es posible verificar invariantes
     después de él. Este orquestador replica EXACTAMENTE el flujo del runner (mismas funciones
     auxiliares, mismos parámetros) pero intercala la verificación de invariantes ANTES de
     borrar la DB — ningún cambio de mecánica ni de parámetros.
  3. Construir el reporte de métricas (Tarea 21) desde los CSV REALES de Locust y medir la
     distribución real de peticiones (no asumir los pesos de tareas).
  4. Evaluar los SLOs de forma ESTRICTA (p95 lectura < 200 ms, p95 transferencia < 500 ms,
     errores inesperados < 1%, cero violaciones de invariantes) y emitir un veredicto
     PASS/FAIL POR UMBRAL.
  5. Preservar los artefactos crudos (CSV de Locust + JSON del runner) con timestamp, SIN
     sobrescribir, en la carpeta de evidencia de carga.

Reglas duras (R9.5/R9.6/R10.5/R16.1):
  - Números REALES medidos; nunca fabricados.
  - Un servicio caído, una corrida sin métricas o una violación de invariante ⇒ NO es PASS.
  - No se optimiza la aplicación (este es el baseline PREVIO a cualquier optimización, R9.7).
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

# El aislamiento DEBE importarse/ejecutarse ANTES de cualquier arranque de la app (R10.1).
from . import isolation
from . import report as report_mod
from . import run_loadtest as runner
from . import verify_invariants as inv


# El total inicial sembrado (conservación del dinero): suma de saldos de las dos cuentas
# internas. La mezcla de carga usa SOLO transferencias internas (locustfile Tarea 19), que
# conservan el dinero dentro del sistema; no hay ACH en la carga, de modo que el total
# esperado tras la corrida es exactamente la suma sembrada inicial.
EXPECTED_TOTAL_CENTS = (
    isolation.LOADTEST_CHECKING_BALANCE_CENTS + isolation.LOADTEST_SAVINGS_BALANCE_CENTS
)

# Umbrales ESTRICTOS (design.md §3.3; R9.5 / R16.1). "<" estricto, no "<=".
SLO_READ_P95_MS = 200.0
SLO_TRANSFER_P95_MS = 500.0
SLO_UNEXPECTED_ERROR_RATE = 0.01  # 1%


def _preserve(src: Path, dest_dir: Path, stamp: str) -> Path | None:
    """Copia `src` a `dest_dir` con un prefijo de timestamp, sin sobrescribir."""
    if not src.is_file():
        return None
    dest = dest_dir / f"{stamp}__{src.name}"
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{stamp}_{counter}__{src.name}"
        counter += 1
    shutil.copy2(src, dest)
    return dest


def run_baseline(evidence_dir: Path) -> int:
    """Ejecuta el baseline completo T23 y devuelve 0 si TODOS los umbrales pasan, != 0 si no."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.localtime())

    # Configuración EXACTA D-E3-03 (defaults del runner = contrato 30/5/60).
    config = runner.LoadConfig(
        results_dir=runner._LOADTEST_DIR / "results",
        is_mechanics_smoke=False,  # Este ES el baseline oficial.
    )

    # Validación temprana del contrato (fallar antes de arrancar nada).
    assert config.users == 30, config.users
    assert config.spawn_rate == 5, config.spawn_rate
    assert config.steady_seconds == 60, config.steady_seconds

    db_path: Path | None = None
    uvicorn_proc = None
    locust_proc = None

    log_dir = config.results_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    uvicorn_log = log_dir / f"uvicorn_baseline_{stamp}.log"
    locust_log = log_dir / f"locust_baseline_{stamp}.log"

    historic_db = runner._BACKEND_ROOT / "shift_bank.db"
    historic_existed_before = historic_db.exists()
    historic_mtime_before = historic_db.stat().st_mtime if historic_existed_before else None

    inv_report = None
    run_result = None
    service_ok = False
    locust_exit = None

    try:
        # (1) Aislar + sembrar la DB sintética ANTES de arrancar la app (R10.1 / AC-10).
        db_path = isolation.setup_loadtest_db()
        print(f"[baseline] DB sintetica: {db_path}", flush=True)

        # (2) Puerto libre + uvicorn (hereda DB_PATH + SHIFT_* del entorno).
        config.port = runner._pick_free_port(config.host)
        base_url = f"http://{config.host}:{config.port}"
        print(f"[baseline] uvicorn -> {base_url}", flush=True)
        uvicorn_proc = runner._spawn_uvicorn(config, uvicorn_log)

        # (3) Espera de salud acotada: un servicio que nunca queda sano NO es PASS (R9.1).
        print(f"[baseline] esperando salud en {runner._health_url(config)} ...", flush=True)
        runner._wait_until_healthy(config, uvicorn_proc)
        service_ok = True
        print("[baseline] servidor SANO.", flush=True)

        # (4) Locust headless con la configuracion exacta (30/5, ramp 6s, steady 60s).
        ramp = config.ramp_up_seconds
        total = config.total_run_seconds
        print(
            f"[baseline] Locust: users={config.users} spawn-rate={config.spawn_rate} "
            f"ramp={ramp:.0f}s steady={config.steady_seconds}s total={total:.0f}s",
            flush=True,
        )
        run_started_at = time.time()
        steady_window_start_at = run_started_at + ramp
        steady_window_end_at = steady_window_start_at + config.steady_seconds

        locust_proc = runner._spawn_locust(config, locust_log)
        locust_timeout = total + 60.0
        locust_proc.wait(timeout=locust_timeout)
        runner._close_log_handle(locust_proc)
        locust_exit = locust_proc.returncode
        locust_tail = runner._read_log_tail(locust_log)
        print(f"[baseline] Locust exit code {locust_exit}.", flush=True)

        csv_prefix = getattr(locust_proc, "_csv_prefix", None)

        # (5) VERIFICACION DE INVARIANTES sobre la MISMA DB, ANTES del teardown (R10.4/R10.5).
        #     El total inicial sembrado conocido se pasa explicitamente (conservacion fuerte).
        print(
            f"[baseline] verificando invariantes (expected_total={EXPECTED_TOTAL_CENTS})...",
            flush=True,
        )
        inv_report = inv.verify_invariants(
            db_path, expected_total_cents=EXPECTED_TOTAL_CENTS
        )
        print(f"[baseline] invariantes ok={inv_report.ok}", flush=True)

        run_result = runner.RunResult(
            base_url=base_url,
            users=config.users,
            spawn_rate=config.spawn_rate,
            ramp_up_seconds=ramp,
            steady_seconds=float(config.steady_seconds),
            total_run_seconds=total,
            run_started_at=run_started_at,
            steady_window_start_at=steady_window_start_at,
            steady_window_end_at=steady_window_end_at,
            locust_exit_code=locust_exit,
            csv_prefix=csv_prefix,
            is_mechanics_smoke=False,
            locust_stdout_tail=locust_tail,
            extra={"uvicorn_log": str(uvicorn_log), "locust_log": str(locust_log)},
        )
    finally:
        # Teardown limpio: Locust, uvicorn, DB sintetica. Siempre se ejecuta.
        runner._terminate(locust_proc)
        runner._terminate(uvicorn_proc)
        runner._close_log_handle(locust_proc)
        runner._close_log_handle(uvicorn_proc)
        # NB: la DB se borra DESPUES de haber verificado invariantes (arriba).
        if db_path is not None:
            isolation.teardown_synthetic_db(db_path)
            print(f"[baseline] teardown: DB sintetica eliminada ({db_path}).", flush=True)
        historic_exists_after = historic_db.exists()
        historic_mtime_after = (
            historic_db.stat().st_mtime if historic_exists_after else None
        )
        untouched = (
            historic_existed_before == historic_exists_after
            and historic_mtime_before == historic_mtime_after
        )
        print(f"[baseline] DB historica intacta: {untouched}", flush=True)

    # --- A partir de aqui, evaluacion y evidencia (fuera del try/finally) ----

    # Un servicio caido / Locust no finalizado => NO es PASS (R9.1/R9.5).
    if not service_ok or run_result is None:
        print("[baseline] FALLO: servicio no disponible o corrida sin resultados.", file=sys.stderr)
        return 2

    csv_prefix = run_result.csv_prefix
    if csv_prefix is None:
        print("[baseline] FALLO: Locust no produjo CSV; sin metricas => NO PASS.", file=sys.stderr)
        return 2

    # (6) Reporte de metricas desde los CSV REALES (Tarea 21). Fail-loud si faltan.
    metrics = report_mod.build_report(
        csv_prefix,
        run_params={
            "users": run_result.users,
            "spawn_rate": run_result.spawn_rate,
            "steady_seconds": int(run_result.steady_seconds),
            "ramp_up_seconds": int(round(run_result.ramp_up_seconds)),
        },
    )

    # JSON del runner/reporte (artefacto adicional, con timestamp, sin sobrescribir).
    report_json_path = report_mod.write_report_json(
        metrics, config.results_dir, tag="baseline", timestamp=stamp
    )

    # (7) Evaluacion ESTRICTA de SLOs por umbral.
    read_p95 = metrics["latency_ms"]["by_type"]["read"]["p95_ms"]
    transfer_p95 = metrics["latency_ms"]["by_type"]["transfer"]["p95_ms"]
    err_rate = metrics["rejections"]["unexpected_error_rate"]
    unexpected_total = metrics["rejections"]["unexpected_total_including_exceptions"]
    total_requests = metrics["request_counts"]["total"]

    verdicts = {
        "read_p95_lt_200ms": {
            "measured_ms": read_p95,
            "threshold_ms": SLO_READ_P95_MS,
            "pass": read_p95 < SLO_READ_P95_MS,
        },
        "transfer_p95_lt_500ms": {
            "measured_ms": transfer_p95,
            "threshold_ms": SLO_TRANSFER_P95_MS,
            "pass": transfer_p95 < SLO_TRANSFER_P95_MS,
        },
        "unexpected_errors_lt_1pct": {
            "measured_rate": err_rate,
            "measured_count": unexpected_total,
            "total_requests": total_requests,
            "threshold_rate": SLO_UNEXPECTED_ERROR_RATE,
            "pass": err_rate < SLO_UNEXPECTED_ERROR_RATE,
        },
        "invariants_ok": {
            "ok": bool(inv_report.ok) if inv_report is not None else False,
            "expected_total_cents": EXPECTED_TOTAL_CENTS,
            "observed_total_cents": (
                inv_report.observed_total_cents if inv_report is not None else None
            ),
            "violations": (
                [f"[{v.kind}] {v.detail}" for v in inv_report.violations]
                if inv_report is not None
                else ["sin reporte de invariantes"]
            ),
            "pass": bool(inv_report.ok) if inv_report is not None else False,
        },
        "locust_run_clean": {
            "locust_exit_code": locust_exit,
            # El runner usa --exit-code-on-error 1; exit 0 => sin fallos registrados.
            "pass": locust_exit == 0,
        },
    }
    overall_pass = all(v["pass"] for v in verdicts.values())

    # (8) Preservar artefactos crudos (CSV de Locust + JSON) en la evidencia, SIN sobrescribir.
    csv_paths = report_mod._resolve_csv_paths(csv_prefix)
    preserved: dict[str, str] = {}
    for kind, p in csv_paths.items():
        dest = _preserve(Path(p), evidence_dir, stamp)
        if dest is not None:
            preserved[f"locust_csv_{kind}"] = str(dest)
    # JSON del reporte.
    dest_json = _preserve(report_json_path, evidence_dir, stamp)
    if dest_json is not None:
        preserved["runner_report_json"] = str(dest_json)
    # Logs crudos de uvicorn/locust (contexto del arnes).
    for logp in (uvicorn_log, locust_log):
        dest = _preserve(Path(logp), evidence_dir, stamp)
        if dest is not None:
            preserved[f"log_{Path(logp).stem}"] = str(dest)

    # Distribucion real medida (no asumida).
    realized_distribution = metrics["distribution"]["measured_vs_target"]

    # (9) Resumen de veredicto (artefacto JSON de verdicto, con timestamp).
    verdict_doc = {
        "task": "T23 - primer baseline de carga (SLO + invariantes)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "is_mechanics_smoke": False,
        "config_D_E3_03": {
            "users": run_result.users,
            "spawn_rate": run_result.spawn_rate,
            "ramp_up_seconds": run_result.ramp_up_seconds,
            "steady_seconds": run_result.steady_seconds,
            "mix_target_pct": {
                "GET /api/accounts": 60.0,
                "GET /api/transfers": 30.0,
                "POST /api/transfers": 10.0,
            },
        },
        "environment": metrics["environment"],
        "realized_distribution": realized_distribution,
        "request_counts": metrics["request_counts"],
        "latency_ms": metrics["latency_ms"],
        "throughput_rps": metrics["throughput_rps"],
        "rejections": metrics["rejections"],
        "invariants": {
            "ok": bool(inv_report.ok),
            "expected_total_cents": inv_report.expected_total_cents,
            "observed_total_cents": inv_report.observed_total_cents,
            "balances_cents": inv_report.balances_cents,
            "ach_outflow_cents": inv_report.ach_outflow_cents,
            "violations": [f"[{v.kind}] {v.detail}" for v in inv_report.violations],
        },
        "slo_verdicts": verdicts,
        "overall_pass": overall_pass,
        "preserved_artifacts": preserved,
        "report_json_original": str(report_json_path),
    }
    verdict_path = evidence_dir / f"{stamp}__T23_verdict.json"
    counter = 1
    while verdict_path.exists():
        verdict_path = evidence_dir / f"{stamp}_{counter}__T23_verdict.json"
        counter += 1
    verdict_path.write_text(
        json.dumps(verdict_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- Salida legible --------------------------------------------------------
    print("=== T23 BASELINE: VEREDICTO ===")
    print(f"  distribucion real medida:")
    for d in realized_distribution:
        tgt = "n/a" if d["target_pct"] is None else f"{d['target_pct']:.1f}%"
        print(
            f"    {d['route']:22s} count={d['request_count']:>6d}  "
            f"medida={d['measured_pct']:.2f}%  objetivo={tgt}"
        )
    print(f"  read p95:       {read_p95:.1f} ms   (< {SLO_READ_P95_MS:.0f})  "
          f"=> {'PASS' if verdicts['read_p95_lt_200ms']['pass'] else 'FAIL'}")
    print(f"  transfer p95:   {transfer_p95:.1f} ms   (< {SLO_TRANSFER_P95_MS:.0f})  "
          f"=> {'PASS' if verdicts['transfer_p95_lt_500ms']['pass'] else 'FAIL'}")
    print(f"  err inesperado: {err_rate*100:.4f}% ({unexpected_total}/{total_requests})  "
          f"(< 1%)  => {'PASS' if verdicts['unexpected_errors_lt_1pct']['pass'] else 'FAIL'}")
    print(f"  invariantes:    ok={inv_report.ok}  "
          f"=> {'PASS' if verdicts['invariants_ok']['pass'] else 'FAIL'}")
    print(f"  locust exit:    {locust_exit}  "
          f"=> {'PASS' if verdicts['locust_run_clean']['pass'] else 'FAIL'}")
    print(f"  OVERALL:        {'PASS' if overall_pass else 'FAIL'}")
    print(f"  verdict JSON:   {verdict_path}")
    print(f"  report JSON:    {report_json_path}")
    print(f"  artefactos preservados en: {evidence_dir}")

    # El baseline SIEMPRE se preserva para el gate T24, pase o falle. El codigo de salida
    # refleja el veredicto de SLOs (0 solo si todo pasa), pero la corrida fue valida.
    return 0 if overall_pass else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        evidence_dir = Path(argv[0])
    else:
        evidence_dir = (
            runner._PROJECT_ROOT.parent / "_experiment_logs" / "Kiro" / "carga"
        )
    return run_baseline(evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
