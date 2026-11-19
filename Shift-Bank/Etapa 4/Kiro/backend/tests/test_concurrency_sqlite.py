"""Concurrencia real de SQLite: lector/escritor (WAL) y multiproceso (Etapa 3, Tarea 16).

Verifica el modelo de concurrencia del diseño (design.md §2.8 y §6; requisitos R8.3, R8.4,
R17.1, R17.2):

1. **Lector/escritor en WAL (misma máquina, dos conexiones).** Dos conexiones SEPARADAS al MISMO
   archivo SQLite (no `:memory:`): un escritor que ejecuta transferencias internas vía la capa de
   servicio (dentro de `financial_transaction` / `BEGIN IMMEDIATE`) y un lector que consulta
   saldos/historial. Se comprueba que, bajo WAL, el lector NO queda bloqueado innecesariamente
   por el único escritor (puede leer un snapshot consistente mientras el escritor mantiene el
   lock de escritura) y que ningún `database is locked` aborta una secuencia de escritura
   correctamente serializada. La prueba es DETERMINISTA: usa bucles acotados y un pequeño
   handshake por eventos; NO asevera tiempos de reloj, sino RESULTADOS (saldos finales,
   integridad de la cadena, lecturas no bloqueadas).

2. **Correctitud bajo concurrencia (hilos, conexiones separadas).** Varias transferencias
   internas concurrentes (hilos con conexiones propias) y, al terminar, se asevera:
   conservación del dinero (la suma de saldos se conserva frente al nº de transferencias
   COMPLETED), exactamente-una-vez (sin duplicado/pérdida), `verify_chain` íntegra, `seq`
   contiguo (sin huecos) y ancla coherente.

3. **Multiproceso independiente (procesos reales).** Al menos DOS procesos independientes
   (`subprocess` lanzando `tests._concurrency_worker` con el intérprete del `.venv`), cada uno
   con su propia conexión al mismo archivo, que transfieren/leen de forma concurrente. Tras unir,
   se asevera que la DB no está corrupta, el dinero se conserva y `verify_chain` es íntegra (la
   serialización de un único escritor por `BEGIN IMMEDIATE` mantiene la cadena sin huecos entre
   procesos). Se propagan `DB_PATH` y las claves `SHIFT_*` de prueba al entorno del hijo.

Aislamiento: la DB es un archivo desechable bajo `tmp_path` (nunca la DB histórica ni
`SEED-3.md`). El escritor usa montos muy por debajo del umbral MFA para completar directo, y
alterna la dirección checking↔savings para conservar la suma de saldos.

Determinismo frente a flakiness: se fija `PRAGMA busy_timeout` en todas las conexiones para
absorber la contención transitoria del único escritor y se reintenta de forma ACOTADA ante
`database is locked`; nunca se asevera un tiempo de pared. Un escritor serializado DEBE terminar
con éxito; nunca se enmascara un fallo real como éxito.

_Requisitos: R8.3, R8.4, R17.1, R17.2_ · _Diseño: §2.8, §6_ · _AC: AC-09_
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

import app.audit as audit
import app.db as db
import app.repository as repository
import app.service as service

# Monto por transferencia muy por debajo del umbral MFA (1.000.000 COP) → completa directo, sin
# MFA ni rechazos de límite. 50.000,00 COP = 5.000.000 centavos.
_AMOUNT_RAW = "50000.00"
_AMOUNT_CENTS = 5_000_00

# `busy_timeout` por conexión (ms): absorbe la contención del único escritor sin flakiness.
_BUSY_TIMEOUT_MS = 5000

# Ruta del worker multiproceso (módulo auxiliar junto a este archivo).
_WORKER_MODULE = "tests._concurrency_worker"


# --- Infraestructura: DB de ARCHIVO compartida, migrada y sembrada ------------

def _open_conn(db_path: Path) -> sqlite3.Connection:
    """Abre una conexión al archivo con los MISMOS PRAGMAs que `db.get_connection` + busy_timeout.

    `db.get_connection` fija WAL y foreign_keys (design.md §2.8). Se añade `busy_timeout` por
    conexión para que la contención transitoria del único escritor se resuelva por espera acotada
    del propio driver (las lecturas en WAL no se bloquean).
    """
    conn = db.get_connection(db_path)
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    return conn


@pytest.fixture()
def shared_db(tmp_path, monkeypatch):
    """Crea un archivo SQLite compartido (no `:memory:`) ya migrado y sembrado.

    Replica la secuencia de arranque de `main._initialize_database`
    (init_schema → migrate → migrate_encryption → seed → seed_limits) sobre un archivo bajo
    `tmp_path`, sin lanzar el scheduler. Parchea `config.DB_PATH`/`db.DB_PATH` hacia ese archivo
    para que cualquier `get_connection()` por defecto también apunte a la DB aislada. Devuelve la
    ruta del archivo (compartible por hilos y por procesos hijos).
    """
    import app.config as config
    import app.seed as seed

    db_file = tmp_path / "shift_bank_concurrency.db"
    monkeypatch.setattr(config, "DB_PATH", db_file, raising=True)
    monkeypatch.setattr(db, "DB_PATH", db_file, raising=True)

    conn = _open_conn(db_file)
    try:
        db.init_schema(conn)
        db.migrate(conn)
        db.migrate_encryption(conn)
        seed.seed(conn)
        seed.seed_limits(conn)
        # WAL es persistente a nivel de archivo; confirmamos que quedó activo.
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"se esperaba WAL, se obtuvo {mode!r}"
    finally:
        conn.close()

    return db_file


def _total_balance(conn: sqlite3.Connection) -> int:
    """Suma de saldos de las dos cuentas propias (invariante de conservación del dinero)."""
    checking = repository.get_account(conn, "checking")
    savings = repository.get_account(conn, "savings")
    assert checking is not None and savings is not None
    return checking.balance_cents + savings.balance_cents


def _completed_internal_count(conn: sqlite3.Connection) -> int:
    """Nº de transferencias internas COMPLETED creadas durante la prueba (excluye históricas).

    Las dos transferencias históricas sembradas están COMPLETED pero con `requires_mfa=0` y una
    `description` fija; las creadas por los workers llevan `description` con prefijo conocido. Se
    cuentan por descripción para distinguir las de la prueba de las sembradas.
    """
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM transfer "
        "WHERE status = 'COMPLETED' AND type = 'internal' "
        "AND (description LIKE 'thread-%' OR description LIKE 'worker-%' OR description LIKE 'rw-%')"
    ).fetchone()
    return int(row["n"])


def _assert_chain_and_seq(conn: sqlite3.Connection) -> int:
    """Asevera cadena íntegra, `seq` contiguo sin huecos y ancla coherente. Devuelve nº de filas.

    `verify_chain` ya comprueba contigüidad de `seq`, encadenado HMAC y coherencia del ancla;
    además se verifica aquí de forma independiente que los `seq` presentes son 1..N sin huecos,
    para dejar explícita la invariante de "sin huecos" pedida por la tarea.
    """
    result = audit.verify_chain(conn)
    assert result.ok is True, f"cadena de auditoría rota: {result.reason} (seq={result.failed_seq})"

    seqs = [int(r["seq"]) for r in conn.execute(
        "SELECT seq FROM audit_log ORDER BY seq ASC").fetchall()]
    n = len(seqs)
    assert seqs == list(range(1, n + 1)), f"seq con huecos o no contiguo: {seqs}"

    anchor = conn.execute(
        "SELECT last_seq FROM audit_anchor WHERE id = 1").fetchone()
    if n == 0:
        assert anchor is None or int(anchor["last_seq"]) == 0
    else:
        assert anchor is not None and int(anchor["last_seq"]) == n, (
            f"ancla incoherente: last_seq={anchor['last_seq'] if anchor else None}, N={n}")
    return n


def _run_writer_transfers(db_path: Path, iterations: int, *, prefix: str) -> int:
    """Ejecuta `iterations` transferencias internas alternando dirección con su propia conexión.

    Reintenta de forma acotada ante `database is locked`; un escritor serializado por
    `BEGIN IMMEDIATE` termina con éxito. Devuelve el nº de transferencias COMPLETED.
    """
    conn = _open_conn(db_path)
    completed = 0
    try:
        for i in range(iterations):
            from_kind, to_kind = (("checking", "savings") if i % 2 == 0
                                  else ("savings", "checking"))
            attempt = 0
            while True:
                try:
                    res = service.create_transfer(
                        conn, from_kind=from_kind, to_kind=to_kind,
                        amount_raw=_AMOUNT_RAW, description=f"{prefix}-{i}")
                    if res.status == "COMPLETED":
                        completed += 1
                    break
                except sqlite3.OperationalError as exc:
                    assert "locked" in str(exc).lower(), f"error inesperado: {exc!r}"
                    attempt += 1
                    assert attempt <= 100, "lock no resuelto tras reintentos acotados (fallo real)"
    finally:
        conn.close()
    return completed


# --- 1) Lector/escritor en WAL: lecturas no bloqueadas por el escritor ---------

def test_reader_not_blocked_by_writer_holding_write_lock(shared_db):
    """Bajo WAL, un lector lee un snapshot consistente mientras el escritor mantiene el lock.

    El escritor abre explícitamente `BEGIN IMMEDIATE` (adquiere el lock de escritor), aplica un
    débito pero NO confirma todavía; en ese instante el lector —en OTRA conexión— lee los saldos
    y DEBE obtener el snapshot previo al commit (aislamiento) SIN bloquearse. Es determinista: el
    orden se coordina por `threading.Event`, no por `sleep`, y se asevera el RESULTADO (la lectura
    devuelve el estado pre-commit y no lanza `database is locked`), no un tiempo de pared.
    """
    writer_conn = _open_conn(shared_db)
    reader_conn = _open_conn(shared_db)

    lock_held = threading.Event()
    reader_done = threading.Event()
    reader_result: dict = {}

    before_total = _total_balance(reader_conn)

    def _writer():
        # Transacción de escritura cruda (no vía servicio) para controlar el instante del commit.
        writer_conn.execute("BEGIN IMMEDIATE")
        writer_conn.execute(
            "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = 'checking'",
            (_AMOUNT_CENTS,))
        writer_conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = 'savings'",
            (_AMOUNT_CENTS,))
        # El lock de escritor está tomado y hay cambios sin confirmar.
        lock_held.set()
        # Esperar (acotado) a que el lector haya leído su snapshot antes de confirmar.
        reader_done.wait(timeout=10)
        writer_conn.commit()

    def _reader():
        # Esperar (acotado) a que el escritor tenga el lock y cambios sin confirmar.
        assert lock_held.wait(timeout=10), "el escritor no tomó el lock a tiempo"
        try:
            checking = reader_conn.execute(
                "SELECT balance_cents FROM account WHERE kind = 'checking'").fetchone()
            savings = reader_conn.execute(
                "SELECT balance_cents FROM account WHERE kind = 'savings'").fetchone()
            reader_result["total"] = checking["balance_cents"] + savings["balance_cents"]
            reader_result["blocked_error"] = None
        except sqlite3.OperationalError as exc:  # pragma: no cover - solo si WAL fallara
            reader_result["blocked_error"] = repr(exc)
        finally:
            reader_done.set()

    tw = threading.Thread(target=_writer)
    tr = threading.Thread(target=_reader)
    tw.start()
    tr.start()
    tw.join(timeout=15)
    tr.join(timeout=15)
    assert not tw.is_alive() and not tr.is_alive(), "deadlock/timeout entre lector y escritor"

    writer_conn.close()

    # El lector NO se bloqueó (sin 'database is locked') y vio el snapshot PRE-commit.
    assert reader_result.get("blocked_error") is None, (
        f"el lector fue bloqueado por el escritor bajo WAL: {reader_result.get('blocked_error')}")
    assert reader_result["total"] == before_total, (
        "el lector no vio un snapshot consistente pre-commit")

    # Tras el commit, el total sigue conservado (movimiento interno entre cuentas propias).
    after_conn = _open_conn(shared_db)
    try:
        assert _total_balance(after_conn) == before_total
    finally:
        after_conn.close()


def test_serialized_writer_sequence_never_locked_out(shared_db):
    """Una secuencia de transferencias correctamente serializada completa sin quedar bloqueada.

    Un lector concurrente lee saldos/historial en bucle mientras el escritor ejecuta N
    transferencias vía la capa de servicio. Se asevera que todas completan (ningún `database is
    locked` aborta el escritor) y que las lecturas concurrentes nunca se bloquean.
    """
    iterations = 12
    before_total = None

    setup_conn = _open_conn(shared_db)
    try:
        before_total = _total_balance(setup_conn)
    finally:
        setup_conn.close()

    reader_stop = threading.Event()
    reader_stats = {"reads": 0, "error": None}

    def _reader_loop():
        rconn = _open_conn(shared_db)
        try:
            while not reader_stop.is_set():
                try:
                    repository.get_account(rconn, "checking")
                    repository.get_account(rconn, "savings")
                    _ = service.list_history(rconn)
                    reader_stats["reads"] += 1
                except sqlite3.OperationalError as exc:  # pragma: no cover
                    reader_stats["error"] = repr(exc)
                    break
        finally:
            rconn.close()

    writer_completed = {"n": 0, "error": None}

    def _writer_loop():
        try:
            writer_completed["n"] = _run_writer_transfers(
                shared_db, iterations, prefix="rw")
        except Exception as exc:  # noqa: BLE001
            writer_completed["error"] = repr(exc)
        finally:
            reader_stop.set()

    tr = threading.Thread(target=_reader_loop)
    tw = threading.Thread(target=_writer_loop)
    tr.start()
    tw.start()
    tw.join(timeout=30)
    reader_stop.set()
    tr.join(timeout=10)

    assert writer_completed["error"] is None, f"escritor falló: {writer_completed['error']}"
    assert writer_completed["n"] == iterations, (
        f"no todas las transferencias completaron: {writer_completed['n']}/{iterations}")
    assert reader_stats["error"] is None, (
        f"el lector fue bloqueado bajo WAL: {reader_stats['error']}")
    assert reader_stats["reads"] > 0, "el lector no completó ninguna lectura concurrente"

    verify_conn = _open_conn(shared_db)
    try:
        # Conservación del dinero: movimientos internos no cambian la suma total.
        assert _total_balance(verify_conn) == before_total
        # Exactamente-una-vez: tantas filas COMPLETED (de la prueba) como transferencias.
        assert _completed_internal_count(verify_conn) == iterations
        # Cadena íntegra, seq contiguo, ancla coherente. Cada COMPLETED directo → 1 entrada.
        n = _assert_chain_and_seq(verify_conn)
        assert n == iterations
    finally:
        verify_conn.close()


# --- 2) Correctitud bajo concurrencia (hilos con conexiones separadas) ---------

def test_concurrent_threads_money_conserved_and_chain_intact(shared_db):
    """Múltiples hilos concurrentes transfieren; invariantes financieros y de auditoría se mantienen.

    Cada hilo usa su PROPIA conexión. Tras unir: conservación del dinero, exactamente-una-vez
    (nº de COMPLETED == total de transferencias emitidas), cadena íntegra, `seq` contiguo (sin
    huecos) y ancla coherente.
    """
    n_threads = 4
    per_thread = 8
    total_transfers = n_threads * per_thread

    setup_conn = _open_conn(shared_db)
    try:
        before_total = _total_balance(setup_conn)
    finally:
        setup_conn.close()

    results: dict[int, int] = {}
    errors: dict[int, str] = {}

    def _worker(idx: int):
        try:
            results[idx] = _run_writer_transfers(
                shared_db, per_thread, prefix=f"thread-{idx}")
        except Exception as exc:  # noqa: BLE001
            errors[idx] = repr(exc)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert all(not t.is_alive() for t in threads), "algún hilo no terminó (posible deadlock)"

    assert not errors, f"errores en hilos concurrentes: {errors}"
    assert sum(results.values()) == total_transfers, (
        f"transferencias completadas {sum(results.values())} != esperadas {total_transfers}")

    verify_conn = _open_conn(shared_db)
    try:
        assert _total_balance(verify_conn) == before_total, "el dinero no se conservó"
        assert _completed_internal_count(verify_conn) == total_transfers, (
            "nº de transferencias COMPLETED no coincide (duplicado o pérdida)")
        n = _assert_chain_and_seq(verify_conn)
        # Cada transferencia interna directa (sin MFA) produce exactamente una entrada COMPLETED.
        assert n == total_transfers, (
            f"nº de entradas de auditoría {n} != transiciones {total_transfers}")
    finally:
        verify_conn.close()


# --- 3) Multiproceso independiente (procesos reales) --------------------------

def _child_env(db_path: Path) -> dict:
    """Entorno para el proceso hijo: hereda SHIFT_* de prueba y fija DB_PATH al archivo compartido."""
    from tests import conftest  # valores de clave SOLO-PRUEBAS (deterministas)

    env = dict(os.environ)
    # Asegurar las claves de prueba aunque el entorno del runner no las tuviese explícitas.
    env.setdefault("SHIFT_ENC_KEYS", conftest.TEST_ENC_KEYS)
    env.setdefault("SHIFT_ENC_ACTIVE_KID", conftest.TEST_ENC_KID)
    env.setdefault("SHIFT_AUDIT_HMAC_KEY", conftest.TEST_AUDIT_HMAC_KEY)
    env.setdefault("SHIFT_ADMIN_TOKEN", conftest.TEST_ADMIN_TOKEN)
    env["DB_PATH"] = str(db_path)
    return env


def _spawn_worker(db_path: Path, role: str, iterations: int) -> subprocess.Popen:
    """Lanza un proceso hijo independiente (intérprete del `.venv`) ejecutando el worker."""
    backend_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", _WORKER_MODULE,
           str(db_path), role, str(iterations), str(_AMOUNT_CENTS)]
    return subprocess.Popen(
        cmd, cwd=str(backend_root), env=_child_env(db_path),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_independent_processes_no_corruption_money_conserved_chain_ok(shared_db):
    """Dos procesos independientes sobre el mismo archivo: sin corrupción, dinero conservado, cadena ok.

    Un proceso escritor (transferencias internas) y un proceso lector (saldos/historial), cada uno
    con su propia conexión al mismo archivo SQLite. Tras unir: `integrity_check` ok (sin
    corrupción), conservación del dinero, exactamente-una-vez, cadena íntegra y `seq` contiguo.
    La serialización por `BEGIN IMMEDIATE` mantiene la cadena sin huecos entre procesos (§6).
    """
    writer_iters = 10
    reader_iters = 15

    setup_conn = _open_conn(shared_db)
    try:
        before_total = _total_balance(setup_conn)
    finally:
        setup_conn.close()

    writer = _spawn_worker(shared_db, "writer", writer_iters)
    reader = _spawn_worker(shared_db, "reader", reader_iters)

    w_out, w_err = writer.communicate(timeout=120)
    r_out, r_err = reader.communicate(timeout=120)

    assert writer.returncode == 0, f"proceso escritor falló: rc={writer.returncode}\n{w_err}"
    assert reader.returncode == 0, f"proceso lector falló: rc={reader.returncode}\n{r_err}"

    w_report = json.loads(w_out.strip().splitlines()[-1])
    r_report = json.loads(r_out.strip().splitlines()[-1])
    assert "error" not in w_report, f"escritor reportó error: {w_report}"
    assert "error" not in r_report, f"lector reportó error: {r_report}"
    assert w_report["completed"] == writer_iters, (
        f"el proceso escritor no completó todas: {w_report}")
    assert r_report["reads"] == reader_iters, f"el proceso lector no leyó todas: {r_report}"

    verify_conn = _open_conn(shared_db)
    try:
        # Sin corrupción del archivo tras la concurrencia multiproceso.
        integrity = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok", f"integrity_check falló: {integrity!r}"
        # Conservación del dinero.
        assert _total_balance(verify_conn) == before_total, "el dinero no se conservó"
        # Exactamente-una-vez: tantas COMPLETED de la prueba como transferencias del escritor.
        assert _completed_internal_count(verify_conn) == writer_iters, (
            "nº de transferencias COMPLETED no coincide entre procesos")
        # Cadena íntegra, seq contiguo sin huecos, ancla coherente (una entrada por COMPLETED).
        n = _assert_chain_and_seq(verify_conn)
        assert n == writer_iters, (
            f"nº de entradas de auditoría {n} != transiciones del escritor {writer_iters}")
    finally:
        verify_conn.close()


def test_two_writer_processes_chain_gap_free(shared_db):
    """Dos procesos ESCRITORES concurrentes: la cadena queda sin huecos y verificable.

    Comprueba específicamente R8.4/§6: dos escritores independientes serializados por
    `BEGIN IMMEDIATE` producen una secuencia `seq` contigua (sin huecos) y una cadena HMAC
    verificable, además de conservar el dinero.
    """
    per_process = 8

    setup_conn = _open_conn(shared_db)
    try:
        before_total = _total_balance(setup_conn)
    finally:
        setup_conn.close()

    p1 = _spawn_worker(shared_db, "writer", per_process)
    p2 = _spawn_worker(shared_db, "writer", per_process)

    o1, e1 = p1.communicate(timeout=120)
    o2, e2 = p2.communicate(timeout=120)

    assert p1.returncode == 0, f"escritor 1 falló: rc={p1.returncode}\n{e1}"
    assert p2.returncode == 0, f"escritor 2 falló: rc={p2.returncode}\n{e2}"

    rep1 = json.loads(o1.strip().splitlines()[-1])
    rep2 = json.loads(o2.strip().splitlines()[-1])
    assert "error" not in rep1 and "error" not in rep2, f"error en escritores: {rep1} {rep2}"
    total_completed = rep1["completed"] + rep2["completed"]
    assert total_completed == 2 * per_process, (
        f"no todas las transferencias de ambos escritores completaron: {rep1} {rep2}")

    verify_conn = _open_conn(shared_db)
    try:
        integrity = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok", f"integrity_check falló: {integrity!r}"
        assert _total_balance(verify_conn) == before_total, "el dinero no se conservó"
        assert _completed_internal_count(verify_conn) == total_completed
        n = _assert_chain_and_seq(verify_conn)
        assert n == total_completed, (
            f"nº de entradas {n} != transiciones totales {total_completed}")
    finally:
        verify_conn.close()
