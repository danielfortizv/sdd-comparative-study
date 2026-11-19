"""Runner de la prueba de carga de Shift Bank (Etapa 3, Tarea 20).

design.md §3.1, §3.2 · requirements R9.1, R10.1 · AC-10.

Propósito
---------
Orquestar la prueba de carga Locust end-to-end con la **configuración exacta y no
negociable** (R9.1 / design.md §3.2):

- **30 usuarios** concurrentes.
- **Ramp-up de 5 usuarios/segundo** → el ramp-up tarda 30/5 = **6 s**.
- **60 s de estado estable (steady-state) DESPUÉS de completar el ramp-up.**

El runner:

1. **Aísla ANTES de arrancar la app (R10.1 / AC-10).** Usa `loadtest.isolation`
   (Tarea 18) para fijar `DB_PATH` hacia una DB SQLite sintética desechable y las claves
   de cifrado/auditoría de SOLO carga en el entorno del proceso, y para sembrar la DB de
   forma determinista (saldos/límites amplios). El orden es crítico: el aislamiento ocurre
   ANTES de lanzar uvicorn, de modo que el proceso hijo de uvicorn **herede** `DB_PATH` +
   `SHIFT_*` por entorno y su `lifespan` valide claves y use la DB sintética. Nunca toca la
   DB histórica ni `SEED-3.md`.
2. **Lanza uvicorn como subproceso** enlazado a un puerto local libre, sirviendo la DB
   sintética aislada. **Espera a que el servidor esté sano** (poll a `GET /api/accounts`)
   con un **timeout acotado**; si nunca responde 2xx, FALLA ruidosamente (salida != 0).
3. **Ejecuta Locust HEADLESS** contra `loadtest/locustfile.py` (Tarea 19) con exactamente
   `--users 30 --spawn-rate 5` apuntando al host local de uvicorn. El tiempo total de
   corrida es `ramp_up (6 s) + steady (60 s)`; el runner **registra el instante de inicio
   de la ventana steady** (t0 + ramp) para que los 60 s posteriores al ramp sean
   identificables (el split exacto de p50/p95/p99 por ventana lo hace la Tarea 21).
4. **Tear-down limpio:** detiene Locust y uvicorn y elimina la DB sintética desechable.

Robustez / fail-loud (R9.1, "nunca reportar un servicio no disponible como PASS")
---------------------------------------------------------------------------------
- Timeout acotado de espera de salud: si el servidor nunca queda sano → `RunnerError`
  (salida != 0).
- Si uvicorn o Locust no arrancan, mueren prematuramente, o Locust sale con código != 0
  → `RunnerError` (salida != 0).
- El runner NUNCA emite un resultado "vacío/aprobado" para un servicio inalcanzable.

Parámetros (defaults = contrato exacto)
---------------------------------------
Las duraciones/conteos son parametrizables **solo** para permitir un *smoke* de mecánica
en entornos limitados; los **defaults codifican el contrato exacto 30/5/60**. Un smoke con
duración reducida NO es el baseline oficial (el baseline es la Tarea 23).
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# El aislamiento DEBE importarse y ejecutarse ANTES de cualquier arranque de la app (R10.1).
# `isolation` ya añade `backend/` a sys.path al importarse.
from . import isolation

# --- Localización de rutas del proyecto --------------------------------------
_LOADTEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _LOADTEST_DIR.parent              # .../Kiro
_BACKEND_ROOT = _PROJECT_ROOT / "backend"
_LOCUSTFILE = _LOADTEST_DIR / "locustfile.py"


# --- Contrato de carga exacto (defaults no negociables, R9.1 / design.md §3.2) ---
DEFAULT_USERS = 30
DEFAULT_SPAWN_RATE = 5                 # usuarios/segundo
DEFAULT_STEADY_SECONDS = 60            # estado estable DESPUÉS del ramp-up
# El ramp-up tarda users/spawn_rate segundos (30/5 = 6 s). Se calcula, no se hornea.

# Espera de salud: poll a un endpoint GET con timeout acotado.
DEFAULT_HEALTH_PATH = "/api/accounts"
DEFAULT_HEALTH_TIMEOUT_SECONDS = 30.0
DEFAULT_HEALTH_POLL_INTERVAL_SECONDS = 0.25

# Margen de gracia para apagar subprocesos limpiamente antes de forzar.
_SHUTDOWN_GRACE_SECONDS = 10.0


class RunnerError(RuntimeError):
    """Fallo del arnés de carga. Debe traducirse en salida != 0 (fail-loud)."""


@dataclass
class LoadConfig:
    """Configuración de ejecución del runner.

    Defaults = contrato exacto 30 usuarios / 5 por segundo / 60 s steady-after-ramp.
    """

    users: int = DEFAULT_USERS
    spawn_rate: int = DEFAULT_SPAWN_RATE
    steady_seconds: int = DEFAULT_STEADY_SECONDS
    host: str = "127.0.0.1"
    port: int = 0                      # 0 => elegir un puerto libre
    health_path: str = DEFAULT_HEALTH_PATH
    health_timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS
    health_poll_interval_seconds: float = DEFAULT_HEALTH_POLL_INTERVAL_SECONDS
    results_dir: Path | None = None    # dónde dejar los CSV de Locust (Tarea 21/23)
    is_mechanics_smoke: bool = False   # etiqueta: True si NO es el contrato exacto

    @property
    def ramp_up_seconds(self) -> float:
        """Duración del ramp-up = users / spawn_rate (30/5 = 6 s con los defaults)."""
        if self.spawn_rate <= 0:
            raise RunnerError("spawn_rate debe ser > 0")
        return self.users / self.spawn_rate

    @property
    def total_run_seconds(self) -> float:
        """Tiempo total de corrida de Locust = ramp-up + ventana steady."""
        return self.ramp_up_seconds + self.steady_seconds


@dataclass
class RunResult:
    """Resultado de una corrida del runner (datos que consumirá la Tarea 21)."""

    base_url: str
    users: int
    spawn_rate: int
    ramp_up_seconds: float
    steady_seconds: float
    total_run_seconds: float
    run_started_at: float                 # epoch (time.time) del inicio de Locust
    steady_window_start_at: float         # epoch del inicio de la ventana steady (t0 + ramp)
    steady_window_end_at: float           # epoch del fin de la ventana steady
    locust_exit_code: int
    csv_prefix: Path | None               # prefijo de los CSV de Locust (si se pidieron)
    is_mechanics_smoke: bool
    locust_stdout_tail: str = ""
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Selección de puerto libre
# ---------------------------------------------------------------------------
def _pick_free_port(host: str) -> int:
    """Reserva (brevemente) un puerto efímero libre y lo devuelve.

    Enlaza a puerto 0 para que el SO asigne uno libre, lo lee y cierra el socket. Hay una
    ventana de carrera teórica antes de que uvicorn lo tome; es aceptable para un arnés de
    carga local y el poll de salud detectará un arranque fallido (fail-loud).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))
        return sock.getsockname()[1]


# ---------------------------------------------------------------------------
# Arranque de uvicorn (subproceso que HEREDA DB_PATH + SHIFT_* del entorno)
# ---------------------------------------------------------------------------
def _spawn_uvicorn(config: LoadConfig, log_path: Path | None) -> subprocess.Popen:
    """Lanza uvicorn (vía `loadtest._uvicorn_launcher`) enlazado a host:port.

    El launcher corre en el proceso hijo y **parchea** `config.DB_PATH`/`db.DB_PATH` hacia
    el `DB_PATH` del entorno ANTES de importar la app (R10.1): la app heredada NO lee
    `DB_PATH` del entorno por sí sola (es una constante calculada), por lo que un
    `uvicorn app.main:app` "a secas" usaría la DB histórica. El hijo hereda `DB_PATH` +
    `SHIFT_*` del entorno del runner (ya poblado por `isolation.configure_isolation`).

    La salida del hijo se redirige a `log_path` (archivo), no a un PIPE, para evitar
    bloqueos por buffer de tubería lleno durante corridas largas.
    """
    if not _BACKEND_ROOT.is_dir():
        raise RunnerError(f"No se encontró el backend en {_BACKEND_ROOT}")

    # Sanity: el aislamiento debe haberse aplicado antes de llegar aquí.
    if "DB_PATH" not in os.environ or "SHIFT_ENC_KEYS" not in os.environ:
        raise RunnerError(
            "El aislamiento no está configurado: DB_PATH/SHIFT_* ausentes del entorno. "
            "configure_isolation() debe ejecutarse ANTES de lanzar uvicorn (R10.1)."
        )

    cmd = [sys.executable, "-m", "loadtest._uvicorn_launcher"]
    # El hijo hereda os.environ (incluye DB_PATH + SHIFT_*). Se le pasan host/port por entorno.
    env = dict(os.environ)
    env["SHIFT_LOADTEST_HOST"] = config.host
    env["SHIFT_LOADTEST_PORT"] = str(config.port)
    # PYTHONPATH: la raíz del proyecto (para importar el paquete `loadtest`) y el backend.
    env["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            [str(_PROJECT_ROOT), str(_BACKEND_ROOT), env.get("PYTHONPATH", "")],
        )
    )

    log_handle = open(log_path, "w", encoding="utf-8") if log_path else subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_PROJECT_ROOT),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        if log_path:
            log_handle.close()  # type: ignore[union-attr]
        raise RunnerError(f"No se pudo lanzar uvicorn: {exc}") from exc
    # Guardar el handle/ruta para drenar el log en diagnósticos.
    proc._log_handle = log_handle  # type: ignore[attr-defined]
    proc._log_path = log_path  # type: ignore[attr-defined]
    return proc


def _health_url(config: LoadConfig) -> str:
    return f"http://{config.host}:{config.port}{config.health_path}"


def _wait_until_healthy(config: LoadConfig, proc: subprocess.Popen) -> None:
    """Poll a `GET {health_path}` hasta 2xx o hasta agotar el timeout acotado.

    Falla ruidosamente (`RunnerError`) si:
      - el proceso de uvicorn muere antes de quedar sano, o
      - se agota el timeout sin una respuesta 2xx.

    Nunca trata un servidor inalcanzable como disponible (R9.1).
    """
    url = _health_url(config)
    deadline = time.monotonic() + config.health_timeout_seconds
    last_err: str = "sin respuesta"

    while time.monotonic() < deadline:
        # Si uvicorn murió, abortar de inmediato (fail-loud, no esperar al timeout).
        if proc.poll() is not None:
            tail = _read_log_tail(getattr(proc, "_log_path", None))
            raise RunnerError(
                f"uvicorn terminó prematuramente (exit {proc.returncode}) antes de "
                f"quedar sano. Salida:\n{tail}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if 200 <= resp.status < 300:
                    return
                last_err = f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code}"
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            last_err = f"conexión: {exc}"
        time.sleep(config.health_poll_interval_seconds)

    raise RunnerError(
        f"El servidor nunca quedó sano en {url} dentro de "
        f"{config.health_timeout_seconds:.0f} s (último error: {last_err}). "
        "Se aborta: un servicio no disponible NUNCA se reporta como corrida válida."
    )


# ---------------------------------------------------------------------------
# Ejecución de Locust (headless, configuración exacta)
# ---------------------------------------------------------------------------
def _spawn_locust(config: LoadConfig, log_path: Path) -> subprocess.Popen:
    """Lanza Locust HEADLESS con la configuración exacta contra el host local.

    `--users 30 --spawn-rate 5 --run-time <ramp+steady>s --headless`. Se usa `--csv` si se
    pidió un `results_dir`, para que la Tarea 21/23 lea las estadísticas por ruta.

    La salida de Locust se escribe a `log_path` (archivo), nunca a un PIPE: con corridas
    largas Locust emite mucho texto y un PIPE sin drenar se llenaría y **bloquearía** el
    subproceso (deadlock). El runner lee el archivo tras finalizar.
    """
    if not _LOCUSTFILE.is_file():
        raise RunnerError(f"No se encontró el locustfile en {_LOCUSTFILE}")

    base_url = f"http://{config.host}:{config.port}"
    run_time = f"{int(round(config.total_run_seconds))}s"
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(_LOCUSTFILE),
        "--headless",
        "--host",
        base_url,
        "--users",
        str(config.users),
        "--spawn-rate",
        str(config.spawn_rate),
        "--run-time",
        run_time,
        # Salir con código != 0 si hay cualquier fallo registrado → fail-loud aguas arriba.
        "--exit-code-on-error",
        "1",
        "--loglevel",
        "WARNING",
    ]
    csv_prefix: Path | None = None
    if config.results_dir is not None:
        config.results_dir.mkdir(parents=True, exist_ok=True)
        # Prefijo con timestamp: NO sobrescribir artefactos previos (R9.6; Tarea 23).
        stamp = time.strftime("%Y%m%dT%H%M%S", time.localtime())
        tag = "smoke" if config.is_mechanics_smoke else "run"
        csv_prefix = config.results_dir / f"locust_{tag}_{stamp}"
        cmd += ["--csv", str(csv_prefix)]

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(_PROJECT_ROOT), env.get("PYTHONPATH", "")])
    )
    log_handle = open(log_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_PROJECT_ROOT),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        log_handle.close()
        raise RunnerError(f"No se pudo lanzar Locust: {exc}") from exc
    # Adjuntar metadatos al proceso para recuperarlos luego.
    proc._csv_prefix = csv_prefix  # type: ignore[attr-defined]
    proc._log_handle = log_handle  # type: ignore[attr-defined]
    proc._log_path = log_path  # type: ignore[attr-defined]
    return proc


# ---------------------------------------------------------------------------
# Apagado limpio de subprocesos
# ---------------------------------------------------------------------------
def _terminate(proc: subprocess.Popen | None) -> None:
    """Termina un subproceso de forma limpia (terminate → wait → kill)."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=_SHUTDOWN_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=_SHUTDOWN_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass


def _close_log_handle(proc: subprocess.Popen | None) -> None:
    """Cierra el handle del archivo de log asociado al proceso, si existe."""
    if proc is None:
        return
    handle = getattr(proc, "_log_handle", None)
    if handle is not None and handle is not subprocess.DEVNULL:
        try:
            handle.close()
        except OSError:
            pass


def _read_log_tail(log_path: Path | None, max_chars: int = 4000) -> str:
    """Lee el tail acotado de un archivo de log (salida de un subproceso)."""
    if log_path is None or not Path(log_path).exists():
        return ""
    try:
        data = Path(log_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(data) > max_chars:
        return "...(truncado)...\n" + data[-max_chars:]
    return data


# ---------------------------------------------------------------------------
# Orquestación principal
# ---------------------------------------------------------------------------
def run_load_test(config: LoadConfig | None = None) -> RunResult:
    """Ejecuta la prueba de carga completa y devuelve un `RunResult`.

    Pasos (orden crítico R10.1):
      1. Aislar + sembrar la DB sintética ANTES de arrancar la app.
      2. Elegir puerto libre; lanzar uvicorn (hereda DB_PATH + SHIFT_*).
      3. Esperar salud (timeout acotado) o FALLAR.
      4. Lanzar Locust headless (30/5), medir ventana steady de 60 s tras el ramp.
      5. Teardown: parar Locust, parar uvicorn, borrar la DB sintética.

    Lanza `RunnerError` ante cualquier indisponibilidad (fail-loud).
    """
    config = config or LoadConfig()

    # Validación temprana del contrato exacto (fallar antes de arrancar nada).
    if config.spawn_rate <= 0:
        raise RunnerError("spawn_rate debe ser > 0")
    if config.users <= 0:
        raise RunnerError("users debe ser > 0")
    if config.steady_seconds <= 0:
        raise RunnerError("steady_seconds debe ser > 0")

    db_path: Path | None = None
    uvicorn_proc: subprocess.Popen | None = None
    locust_proc: subprocess.Popen | None = None

    # Rutas de log (archivos, no PIPE) para evitar deadlocks de tubería en corridas largas.
    stamp = time.strftime("%Y%m%dT%H%M%S", time.localtime())
    log_dir = config.results_dir if config.results_dir is not None else _LOADTEST_DIR / "results"
    log_dir.mkdir(parents=True, exist_ok=True)
    uvicorn_log = log_dir / f"uvicorn_{stamp}.log"
    locust_log = log_dir / f"locust_{stamp}.log"

    # Snapshot de la DB histórica para garantizar que NO se toca (R10.1).
    historic_db = _BACKEND_ROOT / "shift_bank.db"
    historic_existed_before = historic_db.exists()
    historic_mtime_before = (
        historic_db.stat().st_mtime if historic_existed_before else None
    )

    try:
        # (1) Aislamiento + siembra ANTES de importar/arrancar la app (R10.1 / AC-10).
        db_path = isolation.setup_loadtest_db()

        # (2) Puerto libre + arranque de uvicorn (hereda DB_PATH + SHIFT_* del entorno).
        if config.port == 0:
            config.port = _pick_free_port(config.host)
        base_url = f"http://{config.host}:{config.port}"
        print(f"[runner] DB sintética: {db_path}")
        print(f"[runner] uvicorn → {base_url} (sirve la DB sintética aislada)")
        uvicorn_proc = _spawn_uvicorn(config, uvicorn_log)

        # (3) Espera de salud acotada (fail-loud si nunca queda sano).
        print(
            f"[runner] esperando salud en {_health_url(config)} "
            f"(timeout {config.health_timeout_seconds:.0f}s)..."
        )
        _wait_until_healthy(config, uvicorn_proc)
        print("[runner] servidor SANO.")

        # (4) Locust headless con la configuración exacta.
        ramp = config.ramp_up_seconds
        total = config.total_run_seconds
        label = "SMOKE de mecánica" if config.is_mechanics_smoke else "corrida"
        print(
            f"[runner] Locust ({label}): users={config.users} spawn-rate={config.spawn_rate} "
            f"ramp-up={ramp:.0f}s steady={config.steady_seconds}s total={total:.0f}s"
        )
        run_started_at = time.time()
        steady_window_start_at = run_started_at + ramp
        steady_window_end_at = steady_window_start_at + config.steady_seconds
        print(
            f"[runner] ventana STEADY: inicia en t0+{ramp:.0f}s "
            f"(epoch {steady_window_start_at:.3f}) y dura {config.steady_seconds}s "
            f"(fin epoch {steady_window_end_at:.3f})"
        )

        locust_proc = _spawn_locust(config, locust_log)
        # Esperar a que Locust complete su --run-time (con margen generoso).
        locust_timeout = total + 60.0
        try:
            locust_proc.wait(timeout=locust_timeout)
        except subprocess.TimeoutExpired as exc:
            raise RunnerError(
                f"Locust no finalizó en {locust_timeout:.0f}s; se aborta."
            ) from exc

        _close_log_handle(locust_proc)
        locust_tail = _read_log_tail(locust_log)
        locust_exit = locust_proc.returncode
        print(f"[runner] Locust finalizó con exit code {locust_exit}.")

        if locust_exit != 0:
            raise RunnerError(
                f"Locust salió con código {locust_exit} (hubo fallos registrados o error "
                f"de arranque). Salida:\n{locust_tail}"
            )

        csv_prefix = getattr(locust_proc, "_csv_prefix", None)
        return RunResult(
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
            is_mechanics_smoke=config.is_mechanics_smoke,
            locust_stdout_tail=locust_tail,
            extra={
                "uvicorn_log": str(uvicorn_log),
                "locust_log": str(locust_log),
            },
        )
    finally:
        # (5) Teardown limpio: Locust, uvicorn, DB sintética. Siempre se ejecuta.
        _terminate(locust_proc)
        _terminate(uvicorn_proc)
        _close_log_handle(locust_proc)
        _close_log_handle(uvicorn_proc)
        if db_path is not None:
            isolation.teardown_synthetic_db(db_path)
            print(f"[runner] teardown: DB sintética eliminada ({db_path}).")

        # Verificar que la DB histórica no fue tocada por el arnés.
        historic_exists_after = historic_db.exists()
        historic_mtime_after = (
            historic_db.stat().st_mtime if historic_exists_after else None
        )
        untouched = (
            historic_existed_before == historic_exists_after
            and historic_mtime_before == historic_mtime_after
        )
        print(f"[runner] DB histórica intacta: {untouched}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_loadtest",
        description=(
            "Runner de carga Locust de Shift Bank (Etapa 3, Tarea 20). "
            "Defaults = contrato exacto 30 usuarios / 5 por segundo / 60 s steady-after-ramp."
        ),
    )
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--spawn-rate", type=int, default=DEFAULT_SPAWN_RATE)
    parser.add_argument(
        "--steady-seconds",
        type=int,
        default=DEFAULT_STEADY_SECONDS,
        help="Segundos de estado estable DESPUÉS del ramp-up (default 60 = contrato).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = elegir puerto libre.")
    parser.add_argument(
        "--health-timeout-seconds", type=float, default=DEFAULT_HEALTH_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=str(_LOADTEST_DIR / "results"),
        help="Directorio donde Locust deja los CSV (con timestamp, sin sobrescribir).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="No escribir CSV de Locust (solo validar la mecánica).",
    )
    parser.add_argument(
        "--mechanics-smoke",
        action="store_true",
        help=(
            "Marca la corrida como SMOKE de mecánica (NO el baseline oficial). "
            "Úsese con duraciones reducidas para validar el arnés en entornos limitados."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI. Devuelve 0 en éxito; != 0 ante cualquier indisponibilidad."""
    args = _build_parser().parse_args(argv)

    # Si el contrato exacto no se respeta, exigir la etiqueta de smoke para no confundir.
    exact_contract = (
        args.users == DEFAULT_USERS
        and args.spawn_rate == DEFAULT_SPAWN_RATE
        and args.steady_seconds == DEFAULT_STEADY_SECONDS
    )
    is_smoke = args.mechanics_smoke or not exact_contract

    config = LoadConfig(
        users=args.users,
        spawn_rate=args.spawn_rate,
        steady_seconds=args.steady_seconds,
        host=args.host,
        port=args.port,
        health_timeout_seconds=args.health_timeout_seconds,
        results_dir=None if args.no_csv else Path(args.results_dir),
        is_mechanics_smoke=is_smoke,
    )

    try:
        result = run_load_test(config)
    except RunnerError as exc:
        print(f"[runner] FALLO: {exc}", file=sys.stderr)
        return 1

    # Resumen (el reporte completo de métricas lo produce la Tarea 21).
    print("=== run_loadtest: RESULT ===")
    print(f"  base_url:            {result.base_url}")
    print(f"  users:               {result.users}")
    print(f"  spawn_rate:          {result.spawn_rate}")
    print(f"  ramp_up_seconds:     {result.ramp_up_seconds:.1f}")
    print(f"  steady_seconds:      {result.steady_seconds:.0f}")
    print(f"  total_run_seconds:   {result.total_run_seconds:.0f}")
    print(f"  steady_window_start: epoch {result.steady_window_start_at:.3f}")
    print(f"  steady_window_end:   epoch {result.steady_window_end_at:.3f}")
    print(f"  locust_exit_code:    {result.locust_exit_code}")
    print(f"  csv_prefix:          {result.csv_prefix}")
    print(f"  mechanics_smoke:     {result.is_mechanics_smoke}")
    if result.is_mechanics_smoke:
        print(
            "  NOTA: corrida marcada como SMOKE de mecánica — NO es el baseline oficial "
            "(el baseline es la Tarea 23)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
