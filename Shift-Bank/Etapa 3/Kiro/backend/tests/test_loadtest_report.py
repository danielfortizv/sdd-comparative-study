"""Pruebas del reporte de métricas de carga (Etapa 3, Tarea 21).

design.md §3.3 · requirements R9.3, R9.4 · AC-11.

Verifican que `loadtest.report.build_report` DERIVA correctamente, a partir de CSV
SINTÉTICOS de contenido CONOCIDO (mismo formato que emite Locust 2.x), todas las métricas
exigidas por R9.3 y la distribución real medida de R9.4:

- p50/p95/p99 por ruta, por tipo (read/transfer) y agregado.
- throughput (requests/s) por ruta, por tipo y agregado.
- conteos de peticiones por ruta, por tipo y total.
- separación de rechazos de negocio ESPERADOS vs errores INESPERADOS (por prefijo de
  etiqueta del locustfile de la Tarea 19), incluyendo excepciones del arnés.
- distribución REAL medida (porcentaje por ruta sobre el total real) junto al objetivo.

Además:
- La escritura JSON es un artefacto ADICIONAL con timestamp que NO sobrescribe (R9.6).
- Si falta un CSV requerido o es ilegible, el reporte falla ruidosamente (no fabrica números).

Nota: estas pruebas usan CSV SINTÉTICOS deterministas (no la salida de una corrida real).
No ejecutan la prueba de carga ni el baseline oficial (eso es la Tarea 23).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# `loadtest` vive en la raíz del proyecto (junto a `backend/`). pytest corre desde `backend/`,
# así que añadimos la raíz del proyecto a sys.path para poder importar `loadtest.report`.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from loadtest import report as report_mod  # noqa: E402


# --- CSV sintéticos de contenido CONOCIDO (formato Locust 2.x) ----------------
#
# Conteos elegidos para dar una distribución real NO exactamente 60/30/10, de modo que la
# prueba verifique que se MIDE la realidad (R9.4) y no se asumen los pesos:
#   accounts=600, transfers(GET)=280, transfers(POST)=120  → total=1000
#   → medida: 60.0% / 28.0% / 12.0%   (objetivo 60/30/10)
_STATS_CSV = (
    "Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,"
    "Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,"
    "50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%\n"
    "GET,GET /api/accounts,600,0,8,12.3,2.0,180.0,106.0,30.0,0.0,"
    "8,12,15,18,40,95,150,170,180,180,180\n"
    "GET,GET /api/transfers,280,2,6,11.0,2.2,160.0,10.1,14.0,0.1,"
    "6,10,14,16,38,120,150,160,160,160,160\n"
    "POST,POST /api/transfers,120,5,80,220.0,14.7,480.0,78.0,6.0,0.25,"
    "80,170,220,240,420,460,470,480,480,480,480\n"
    ",Aggregated,1000,7,10,45.0,2.0,480.0,80.0,50.0,0.35,"
    "10,18,37,120,300,200,470,470,480,480,480\n"
)

# Failures CSV: 2 rechazos de negocio esperados + 5 errores inesperados.
#   BusinessRejection:insufficient_funds (3) + BusinessRejection:limit_exceeded (?) ...
# Elegimos: negocio esperado = 2+1 = 3; inesperado = 4+1 = 5. (Independiente del stats.)
_FAILURES_CSV = (
    "Method,Name,Error,Occurrences,First Seen,Last Seen\n"
    "POST,POST /api/transfers,BusinessRejection:insufficient_funds,2,1,2\n"
    "POST,POST /api/transfers,BusinessRejection:limit_exceeded,1,1,2\n"
    "POST,POST /api/transfers,UnexpectedError:HTTP 500,4,1,2\n"
    "GET,GET /api/accounts,UnexpectedError:transport,1,1,2\n"
)

# Exceptions CSV: 1 excepción del arnés (debe sumarse a los errores inesperados en salud).
_EXCEPTIONS_CSV = (
    "Count,Message,Traceback,Nodes\n"
    '2,"boom","Traceback...",node1\n'
)

# Variantes "solo cabecera" (caso sano: sin fallos / sin excepciones).
_FAILURES_CSV_EMPTY = "Method,Name,Error,Occurrences,First Seen,Last Seen\n"
_EXCEPTIONS_CSV_EMPTY = "Count,Message,Traceback,Nodes\n"


def _write_csv_set(
    tmp_path: Path,
    *,
    stats: str = _STATS_CSV,
    failures: str = _FAILURES_CSV,
    exceptions: str = _EXCEPTIONS_CSV,
    stats_history: str = "Timestamp,User Count,Type,Name\n",
    prefix_name: str = "locust_synth",
) -> Path:
    """Escribe el conjunto de CSV sintéticos y devuelve el prefijo (sin sufijo)."""
    prefix = tmp_path / prefix_name
    (tmp_path / f"{prefix_name}_stats.csv").write_text(stats, encoding="utf-8")
    (tmp_path / f"{prefix_name}_failures.csv").write_text(failures, encoding="utf-8")
    (tmp_path / f"{prefix_name}_exceptions.csv").write_text(exceptions, encoding="utf-8")
    (tmp_path / f"{prefix_name}_stats_history.csv").write_text(stats_history, encoding="utf-8")
    return prefix


@pytest.fixture()
def synthetic_prefix(tmp_path: Path) -> Path:
    return _write_csv_set(tmp_path)


# --- Latencia p50/p95/p99 (R9.3) ---------------------------------------------
def test_latency_percentiles_per_route_and_type(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    lat = report["latency_ms"]

    # Por ruta: leído directo de columnas 50%/95%/99%.
    assert lat["by_route"]["GET /api/accounts"] == {"p50_ms": 8.0, "p95_ms": 95.0, "p99_ms": 170.0}
    assert lat["by_route"]["GET /api/transfers"] == {"p50_ms": 6.0, "p95_ms": 120.0, "p99_ms": 160.0}
    assert lat["by_route"]["POST /api/transfers"] == {"p50_ms": 80.0, "p95_ms": 460.0, "p99_ms": 480.0}

    # Por tipo: transfer (1 ruta) exacto; read (2 rutas) = cota superior (máximo por percentil).
    assert lat["by_type"]["transfer"] == {"p50_ms": 80.0, "p95_ms": 460.0, "p99_ms": 480.0}
    assert lat["by_type"]["read"] == {"p50_ms": 8.0, "p95_ms": 120.0, "p99_ms": 170.0}

    # Agregado: leído de la fila Aggregated.
    assert lat["aggregated"] == {"p50_ms": 10.0, "p95_ms": 200.0, "p99_ms": 470.0}


# --- Throughput (R9.3) --------------------------------------------------------
def test_throughput_per_route_type_aggregated(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    tput = report["throughput_rps"]
    assert tput["by_route"]["GET /api/accounts"] == 30.0
    assert tput["by_route"]["GET /api/transfers"] == 14.0
    assert tput["by_route"]["POST /api/transfers"] == 6.0
    assert tput["by_type"]["read"] == pytest.approx(44.0)
    assert tput["by_type"]["transfer"] == pytest.approx(6.0)
    # El agregado se lee de la fila Aggregated (50.0), no se recalcula sumando.
    assert tput["aggregated"] == 50.0


# --- Conteos por ruta y total (R9.3) -----------------------------------------
def test_request_counts(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    rc = report["request_counts"]
    assert rc["by_route"] == {
        "GET /api/accounts": 600,
        "GET /api/transfers": 280,
        "POST /api/transfers": 120,
    }
    assert rc["by_type"] == {"read": 880, "transfer": 120}
    assert rc["total"] == 1000


# --- Distribución REAL medida vs objetivo (R9.4) -----------------------------
def test_measured_distribution_is_real_not_weights(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    dist = {d["route"]: d for d in report["distribution"]["measured_vs_target"]}

    # Medida = conteo real / total real * 100  (NO los pesos nominales 60/30/10).
    assert dist["GET /api/accounts"]["measured_pct"] == pytest.approx(60.0)
    assert dist["GET /api/transfers"]["measured_pct"] == pytest.approx(28.0)
    assert dist["POST /api/transfers"]["measured_pct"] == pytest.approx(12.0)

    # El objetivo nominal 60/30/10 se presenta JUNTO a la medida (R9.4).
    assert dist["GET /api/accounts"]["target_pct"] == 60.0
    assert dist["GET /api/transfers"]["target_pct"] == 30.0
    assert dist["POST /api/transfers"]["target_pct"] == 10.0

    # La distancia medida≠objetivo demuestra que se MIDE la realidad (transfers GET 28≠30).
    assert dist["GET /api/transfers"]["measured_pct"] != dist["GET /api/transfers"]["target_pct"]

    # Suma de porcentajes medidos ≈ 100%.
    total_pct = sum(d["measured_pct"] for d in report["distribution"]["measured_vs_target"])
    assert total_pct == pytest.approx(100.0)


# --- Separación rechazos de negocio esperados vs errores inesperados (R9.3) ---
def test_expected_vs_unexpected_split(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    rej = report["rejections"]

    # Esperados = 2 + 1 (BusinessRejection:*).
    assert rej["expected_business_rejections"] == 3
    assert rej["business_rejection_detail"] == {
        "BusinessRejection:insufficient_funds": 2,
        "BusinessRejection:limit_exceeded": 1,
    }

    # Inesperados = 4 + 1 (UnexpectedError:*), SIN contar aún las excepciones.
    assert rej["unexpected_errors"] == 5
    assert rej["unexpected_error_detail"] == {
        "UnexpectedError:HTTP 500": 4,
        "UnexpectedError:transport": 1,
    }

    # Excepciones del arnés (Count=2) se cuentan aparte y se suman a los inesperados en salud.
    assert rej["harness_exceptions"] == 2
    assert rej["unexpected_total_including_exceptions"] == 7

    # Tasa de error inesperado = 7 / 1000.
    assert rej["unexpected_error_rate"] == pytest.approx(7 / 1000)


def test_split_with_empty_failures_is_all_zero(tmp_path: Path):
    prefix = _write_csv_set(
        tmp_path, failures=_FAILURES_CSV_EMPTY, exceptions=_EXCEPTIONS_CSV_EMPTY
    )
    report = report_mod.build_report(prefix)
    rej = report["rejections"]
    assert rej["expected_business_rejections"] == 0
    assert rej["unexpected_errors"] == 0
    assert rej["harness_exceptions"] == 0
    assert rej["unexpected_error_rate"] == 0.0


# --- Entorno y parámetros exactos (R9.3) -------------------------------------
def test_environment_and_run_params(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    env = report["environment"]
    assert set(env) == {"python_version", "os", "locust_version"}
    assert env["python_version"]  # no vacío (capturado del proceso real).

    rp = report["run_params"]
    assert rp == {"users": 30, "spawn_rate": 5, "steady_seconds": 60, "ramp_up_seconds": 6}

    # run_params/env explícitos deben respetarse.
    custom = report_mod.build_report(
        synthetic_prefix,
        run_params={"users": 30, "spawn_rate": 5, "steady_seconds": 60, "ramp_up_seconds": 6},
        env={"python_version": "3.13.2", "os": "TestOS", "locust_version": "2.47.0"},
    )
    assert custom["environment"]["os"] == "TestOS"
    assert custom["environment"]["locust_version"] == "2.47.0"


# --- Fail-loud: CSV faltante / ilegible (no fabricar) ------------------------
def test_missing_stats_csv_raises(tmp_path: Path):
    # Sólo failures/exceptions presentes; falta _stats.csv.
    (tmp_path / "x_failures.csv").write_text(_FAILURES_CSV_EMPTY, encoding="utf-8")
    (tmp_path / "x_exceptions.csv").write_text(_EXCEPTIONS_CSV_EMPTY, encoding="utf-8")
    with pytest.raises(report_mod.ReportError):
        report_mod.build_report(tmp_path / "x")


def test_missing_failures_csv_raises(tmp_path: Path):
    (tmp_path / "y_stats.csv").write_text(_STATS_CSV, encoding="utf-8")
    (tmp_path / "y_exceptions.csv").write_text(_EXCEPTIONS_CSV_EMPTY, encoding="utf-8")
    with pytest.raises(report_mod.ReportError):
        report_mod.build_report(tmp_path / "y")


def test_malformed_stats_missing_columns_raises(tmp_path: Path):
    bad = "Type,Name,Something\nGET,GET /api/accounts,1\n"
    prefix = _write_csv_set(tmp_path, stats=bad)
    with pytest.raises(report_mod.ReportError):
        report_mod.build_report(prefix)


def test_stats_with_no_known_routes_raises(tmp_path: Path):
    only_unknown = (
        "Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,"
        "Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,"
        "50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%\n"
        "GET,GET /other,5,0,8,12.0,2.0,180.0,106.0,30.0,0.0,8,12,15,18,40,95,150,170,180,180,180\n"
    )
    prefix = _write_csv_set(tmp_path, stats=only_unknown)
    with pytest.raises(report_mod.ReportError):
        report_mod.build_report(prefix)


# --- Escritura JSON: artefacto adicional, con timestamp, sin sobrescribir (R9.6) ---
def test_write_report_json_is_additional_and_timestamped(tmp_path: Path, synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    out_dir = tmp_path / "out"

    p1 = report_mod.write_report_json(report, out_dir, tag="smoke", timestamp="20260101T000000")
    assert p1.exists()
    assert p1.name == "loadtest_report_smoke_20260101T000000.json"

    # Round-trip: el JSON es parseable y conserva los campos clave.
    loaded = json.loads(p1.read_text(encoding="utf-8"))
    assert loaded["request_counts"]["total"] == 1000
    assert loaded["distribution"]["target_distribution_pct"]["GET /api/accounts"] == 60.0

    # Segundo write con el MISMO timestamp NO sobrescribe (anti-colisión).
    p2 = report_mod.write_report_json(report, out_dir, tag="smoke", timestamp="20260101T000000")
    assert p2 != p1
    assert p2.exists() and p1.exists()

    # Los CSV sintéticos originales permanecen intactos (artefacto adicional).
    assert (synthetic_prefix.parent / f"{synthetic_prefix.name}_stats.csv").exists()


# --- JSON serializable completo (R9.3): todos los campos presentes -----------
def test_report_is_json_serializable_with_all_r93_fields(synthetic_prefix: Path):
    report = report_mod.build_report(synthetic_prefix)
    # Debe serializar sin error (legible por máquina).
    json.dumps(report)
    for key in (
        "environment",
        "run_params",
        "request_counts",
        "throughput_rps",
        "latency_ms",
        "rejections",
        "distribution",
    ):
        assert key in report, f"Falta el campo R9.3 '{key}' en el reporte"
