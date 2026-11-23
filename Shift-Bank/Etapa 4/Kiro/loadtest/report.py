"""Reporte de métricas de la prueba de carga (Etapa 3, Tarea 21).

design.md §3.3 · requirements R9.3, R9.4 · AC-11.

Propósito
---------
Consumir los **artefactos CSV reales** que deja Locust (producidos por el runner de la Tarea 20:
`<prefix>_stats.csv`, `<prefix>_stats_history.csv`, `<prefix>_failures.csv`,
`<prefix>_exceptions.csv`) y emitir un reporte **legible por máquina (JSON)** con TODAS las
métricas exigidas por R9.3, además de la **distribución real de peticiones medida** por ruta
(R9.4), presentada junto a la distribución objetivo 60/30/10.

Principio rector (R9.3/R9.4): el reporte se DERIVA de la salida CSV real de Locust; nunca
fabrica números. Si un CSV esperado no existe o no es parseable, se falla ruidosamente
(`ReportError`); nunca se inventan métricas ni se reporta un resultado vacío como válido.

Qué contiene el reporte (R9.3)
------------------------------
- `latency_ms`: p50/p95/p99 POR tipo de operación (lectura vs transferencia) y por ruta
  individual, más el agregado. Leídos de las columnas `50% / 95% / 99%` del `_stats.csv`.
- `throughput`: peticiones por segundo (columna `Requests/s`), por ruta, por tipo y agregado.
- `request_counts`: conteos por ruta (`Request Count`), por tipo, y total.
- `rejections`: **rechazos de negocio esperados** (fallos etiquetados `BusinessRejection:*` o
  4xx de dominio) contados SEPARADAMENTE de los **errores inesperados** (`UnexpectedError:*`,
  5xx, transporte). La separación se deriva de `_failures.csv` + `_exceptions.csv`, usando los
  prefijos de etiqueta definidos por el locustfile de la Tarea 19.
- `environment`: versión de Python, SO y versión de Locust.
- `run_params`: parámetros EXACTOS de ejecución (users=30, spawn_rate=5, steady 60 s, ramp 6 s).
- `distribution`: distribución **real medida** por ruta (porcentaje de `Request Count` sobre el
  total real) JUNTO a la distribución objetivo (60/30/10). R9.4 exige MEDIR la realidad, no
  asumir los pesos de tareas de Locust.

Clasificación de operaciones (design.md §3.2/§3.3)
--------------------------------------------------
- **read** (lectura): `GET /api/accounts`, `GET /api/transfers`.
- **transfer** (transferencia): `POST /api/transfers`.

Las claves de ruta usan el `Name` que el locustfile asigna a cada petición (p. ej.
`"GET /api/accounts"`), que es exactamente el `Name` que Locust escribe en el `_stats.csv`.

Preservación (R9.6): el JSON es un artefacto ADICIONAL con timestamp; nunca sobrescribe los CSV
originales de Locust ni un reporte previo.
"""

from __future__ import annotations

import csv
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# --- Clasificación de rutas (design.md §3.2/§3.3) ----------------------------
#
# Nombres de petición tal como el locustfile (Tarea 19) los registra y como aparecen en la
# columna `Name` del `_stats.csv`.
READ_ROUTES = ("GET /api/accounts", "GET /api/transfers")
TRANSFER_ROUTES = ("POST /api/transfers",)

# Fila agregada de Locust: `Name == "Aggregated"` con `Type` vacío.
AGGREGATED_NAME = "Aggregated"

# Prefijos de etiqueta de fallo definidos por el locustfile (Tarea 19), design.md §3.3.
BUSINESS_REJECTION_PREFIX = "BusinessRejection:"
UNEXPECTED_ERROR_PREFIX = "UnexpectedError:"

# Distribución objetivo (pesos nominales 60/30/10), design.md §3.2.
TARGET_DISTRIBUTION_PCT = {
    "GET /api/accounts": 60.0,
    "GET /api/transfers": 30.0,
    "POST /api/transfers": 10.0,
}


class ReportError(RuntimeError):
    """Fallo al construir el reporte (CSV ausente/no parseable). Fail-loud, nunca fabricar."""


# ---------------------------------------------------------------------------
# Estructuras del reporte
# ---------------------------------------------------------------------------
@dataclass
class RouteStats:
    """Estadísticas por ruta derivadas directamente del `_stats.csv`."""

    name: str
    op_type: str                      # "read" | "transfer"
    request_count: int
    failure_count: int
    throughput_rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class LatencyGroup:
    """p50/p95/p99 para un grupo (ruta, tipo de operación o agregado)."""

    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class DistributionEntry:
    """Distribución real medida frente a la objetivo para una ruta."""

    route: str
    request_count: int
    measured_pct: float               # % real = request_count / total_real * 100 (R9.4)
    target_pct: float | None          # % objetivo nominal (60/30/10), None si no aplica


def _op_type_for_route(name: str) -> str | None:
    """Clasifica una ruta como 'read' o 'transfer', o None si no es una ruta conocida."""
    if name in READ_ROUTES:
        return "read"
    if name in TRANSFER_ROUTES:
        return "transfer"
    return None


# ---------------------------------------------------------------------------
# Parsing de CSV (derivado de la salida REAL de Locust; nunca fabricado)
# ---------------------------------------------------------------------------
def _require_file(path: Path, kind: str) -> Path:
    """Exige que un CSV requerido exista; si no, falla ruidosamente (no fabricar)."""
    if not path.is_file():
        raise ReportError(
            f"No se encontró el CSV de {kind}: {path}. El reporte DEBE derivarse de la salida "
            "real de Locust; no se fabrican métricas ni se reporta un resultado vacío."
        )
    return path


def _parse_float(value: str, *, field_name: str, row_name: str) -> float:
    """Convierte una celda a float; 'N/A'/'' → 0.0; valores no numéricos → ReportError."""
    text = (value or "").strip()
    if text == "" or text.upper() == "N/A":
        return 0.0
    try:
        return float(text)
    except ValueError as exc:
        raise ReportError(
            f"Valor no numérico en columna '{field_name}' de la fila '{row_name}': {value!r}"
        ) from exc


def _parse_int(value: str, *, field_name: str, row_name: str) -> int:
    """Convierte una celda a int (vía float para tolerar '12.0'); 'N/A'/'' → 0."""
    text = (value or "").strip()
    if text == "" or text.upper() == "N/A":
        return 0
    try:
        return int(float(text))
    except ValueError as exc:
        raise ReportError(
            f"Valor no entero en columna '{field_name}' de la fila '{row_name}': {value!r}"
        ) from exc


def parse_stats_csv(stats_path: Path) -> tuple[dict[str, RouteStats], LatencyGroup | None, dict]:
    """Parsea `<prefix>_stats.csv` y devuelve (rutas, agregado, crudo_agregado).

    Columnas consumidas (contrato de Locust 2.x): `Type`, `Name`, `Request Count`,
    `Failure Count`, `Requests/s`, `50%`, `95%`, `99%`. La fila `Aggregated` (Name ==
    "Aggregated", Type vacío) se separa del resto como el agregado global.

    Devuelve:
      - `routes`: {name -> RouteStats} para cada ruta conocida (read/transfer).
      - `aggregated`: LatencyGroup del agregado global, o None si no hay fila Aggregated.
      - `aggregated_raw`: dict con request_count/failure_count/throughput del agregado.
    """
    _require_file(stats_path, "estadísticas (stats)")
    routes: dict[str, RouteStats] = {}
    aggregated: LatencyGroup | None = None
    aggregated_raw: dict[str, Any] = {}

    with stats_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"Name", "Request Count", "Failure Count", "Requests/s", "50%", "95%", "99%"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ReportError(
                f"El stats CSV {stats_path} no tiene las columnas esperadas; faltan: "
                f"{sorted(missing)}. ¿Es realmente un CSV de estadísticas de Locust?"
            )
        for row in reader:
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            p50 = _parse_float(row["50%"], field_name="50%", row_name=name)
            p95 = _parse_float(row["95%"], field_name="95%", row_name=name)
            p99 = _parse_float(row["99%"], field_name="99%", row_name=name)

            if name == AGGREGATED_NAME:
                aggregated = LatencyGroup(p50_ms=p50, p95_ms=p95, p99_ms=p99)
                aggregated_raw = {
                    "request_count": _parse_int(
                        row["Request Count"], field_name="Request Count", row_name=name
                    ),
                    "failure_count": _parse_int(
                        row["Failure Count"], field_name="Failure Count", row_name=name
                    ),
                    "throughput_rps": _parse_float(
                        row["Requests/s"], field_name="Requests/s", row_name=name
                    ),
                }
                continue

            op_type = _op_type_for_route(name)
            if op_type is None:
                # Ruta desconocida: se ignora para los grupos read/transfer, pero no se fabrica.
                continue
            routes[name] = RouteStats(
                name=name,
                op_type=op_type,
                request_count=_parse_int(
                    row["Request Count"], field_name="Request Count", row_name=name
                ),
                failure_count=_parse_int(
                    row["Failure Count"], field_name="Failure Count", row_name=name
                ),
                throughput_rps=_parse_float(
                    row["Requests/s"], field_name="Requests/s", row_name=name
                ),
                p50_ms=p50,
                p95_ms=p95,
                p99_ms=p99,
            )

    return routes, aggregated, aggregated_raw


@dataclass
class RejectionSplit:
    """Separación de fallos: rechazos de negocio ESPERADOS vs errores INESPERADOS (R9.3)."""

    expected_business_rejections: int = 0
    unexpected_errors: int = 0
    business_rejection_detail: dict[str, int] = field(default_factory=dict)
    unexpected_error_detail: dict[str, int] = field(default_factory=dict)


def parse_failures_csv(failures_path: Path) -> RejectionSplit:
    """Parsea `<prefix>_failures.csv` y separa rechazos de negocio de errores inesperados.

    Columnas de Locust 2.x: `Method`, `Name`, `Error`, `Occurrences`, `First Seen`, `Last Seen`.
    La columna `Error` contiene la etiqueta que el locustfile (Tarea 19) asignó vía
    `response.failure(...)`:
      - `BusinessRejection:<code>` → rechazo de negocio ESPERADO (4xx de dominio bien formado).
      - `UnexpectedError:<...>`     → error INESPERADO (5xx / transporte / 4xx no reconocido).

    Clasificación por prefijo de etiqueta; cualquier etiqueta de fallo sin el prefijo de
    negocio se cuenta, de forma conservadora, como error inesperado (un fallo es un fallo).
    Un archivo sólo con cabecera (sin filas) ⇒ cero fallos (split en cero), que es el caso
    sano esperado con el aislamiento/siembra de la Tarea 18.
    """
    _require_file(failures_path, "fallos (failures)")
    split = RejectionSplit()

    with failures_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = set(reader.fieldnames or [])
        if "Error" not in fieldnames or "Occurrences" not in fieldnames:
            raise ReportError(
                f"El failures CSV {failures_path} no tiene las columnas esperadas "
                f"(encontradas: {sorted(fieldnames)}). ¿Es un CSV de fallos de Locust?"
            )
        for row in reader:
            error_label = (row.get("Error") or "").strip()
            if not error_label:
                continue
            occurrences = _parse_int(
                row["Occurrences"], field_name="Occurrences", row_name=error_label
            )
            if error_label.startswith(BUSINESS_REJECTION_PREFIX):
                split.expected_business_rejections += occurrences
                split.business_rejection_detail[error_label] = (
                    split.business_rejection_detail.get(error_label, 0) + occurrences
                )
            else:
                # UnexpectedError:* o cualquier otra etiqueta de fallo → inesperado.
                split.unexpected_errors += occurrences
                split.unexpected_error_detail[error_label] = (
                    split.unexpected_error_detail.get(error_label, 0) + occurrences
                )

    return split


def parse_exceptions_csv(exceptions_path: Path) -> int:
    """Parsea `<prefix>_exceptions.csv` y devuelve el total de excepciones del arnés.

    Columnas de Locust 2.x: `Count`, `Message`, `Traceback`, `Nodes`. Las excepciones son
    fallos del propio arnés/tarea (no respuestas del servidor); se reportan aparte y SE SUMAN
    a los errores inesperados en el conteo de salud (una excepción nunca es un rechazo de
    negocio esperado). Un archivo sólo con cabecera ⇒ 0.
    """
    _require_file(exceptions_path, "excepciones (exceptions)")
    total = 0
    with exceptions_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if "Count" not in set(reader.fieldnames or []):
            raise ReportError(
                f"El exceptions CSV {exceptions_path} no tiene la columna 'Count' "
                f"(encontradas: {reader.fieldnames}). ¿Es un CSV de excepciones de Locust?"
            )
        for row in reader:
            total += _parse_int(row["Count"], field_name="Count", row_name="exception")
    return total


# ---------------------------------------------------------------------------
# Agregación por tipo de operación y distribución real medida
# ---------------------------------------------------------------------------
def _weighted_percentile_by_type(routes: dict[str, RouteStats], op_type: str) -> LatencyGroup:
    """Percentiles p50/p95/p99 por tipo de operación.

    Locust no provee percentiles pre-agregados por "tipo" (solo por ruta y el agregado
    global). Para un grupo con una sola ruta (p. ej. transfer → POST /api/transfers), el
    percentil del tipo es EXACTAMENTE el de esa ruta. Para un grupo con varias rutas (read →
    2 GET), se usa una **aproximación conservadora: el máximo** del percentil entre las rutas
    del grupo (peor caso), ya que no se dispone de la distribución completa de latencias por
    ruta en el stats CSV. Esta elección se documenta como cota superior, nunca subestima la
    latencia del tipo. El percentil global exacto por tipo, si se requiere con precisión, se
    deriva del agregado o de los histogramas; aquí se reporta la cota superior por ruta.
    """
    members = [r for r in routes.values() if r.op_type == op_type]
    if not members:
        return LatencyGroup(p50_ms=0.0, p95_ms=0.0, p99_ms=0.0)
    return LatencyGroup(
        p50_ms=max(r.p50_ms for r in members),
        p95_ms=max(r.p95_ms for r in members),
        p99_ms=max(r.p99_ms for r in members),
    )


def compute_measured_distribution(routes: dict[str, RouteStats]) -> list[DistributionEntry]:
    """Calcula la distribución REAL medida por ruta (R9.4).

    Mide el porcentaje de peticiones realmente emitidas por ruta sobre el TOTAL real
    observado (suma de `Request Count` de las rutas conocidas), NO los pesos nominales de
    Locust. Presenta el porcentaje real junto al objetivo (60/30/10). Si el total es 0 (sin
    tráfico), los porcentajes medidos son 0.0 (no se fabrica un 60/30/10 ficticio).
    """
    total_real = sum(r.request_count for r in routes.values())
    entries: list[DistributionEntry] = []
    # Orden estable y legible: rutas conocidas en orden canónico, luego cualquier extra.
    ordered_names = [n for n in (*READ_ROUTES, *TRANSFER_ROUTES) if n in routes]
    ordered_names += [n for n in routes if n not in ordered_names]
    for name in ordered_names:
        r = routes[name]
        measured = (r.request_count / total_real * 100.0) if total_real > 0 else 0.0
        entries.append(
            DistributionEntry(
                route=name,
                request_count=r.request_count,
                measured_pct=round(measured, 4),
                target_pct=TARGET_DISTRIBUTION_PCT.get(name),
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Construcción del reporte (R9.3 + R9.4)
# ---------------------------------------------------------------------------
def capture_environment() -> dict[str, str]:
    """Captura el entorno real: versión de Python, SO y versión de Locust (R9.3).

    La versión de Locust se obtiene de los METADATOS del paquete instalado
    (`importlib.metadata.version`), NO importando `locust`: importar el paquete dispara el
    monkey-patch de gevent (`monkey.patch_all()`) en el arranque, que interfiere con el resto
    del arnés de pruebas (TestClient/anyio). Leer los metadatos evita ese efecto colateral.
    """
    from importlib import metadata

    try:
        locust_version = metadata.version("locust")
    except metadata.PackageNotFoundError:  # pragma: no cover - locust es solo-dev.
        locust_version = "no-instalado"
    return {
        "python_version": sys.version.split()[0],
        "os": platform.platform(),
        "locust_version": locust_version,
    }


# Parámetros EXACTOS de ejecución del contrato (R9.1 / design.md §3.2), para defaults del CLI.
EXACT_RUN_PARAMS = {
    "users": 30,
    "spawn_rate": 5,
    "steady_seconds": 60,
    "ramp_up_seconds": 6,   # 30 usuarios / 5 por segundo = 6 s
}


def _resolve_csv_paths(csv_prefix: str | Path) -> dict[str, Path]:
    """Deriva las rutas de los cuatro CSV a partir del prefijo del runner (Tarea 20)."""
    prefix = Path(csv_prefix)
    base = str(prefix)
    return {
        "stats": Path(base + "_stats.csv"),
        "stats_history": Path(base + "_stats_history.csv"),
        "failures": Path(base + "_failures.csv"),
        "exceptions": Path(base + "_exceptions.csv"),
    }


def build_report(
    csv_prefix: str | Path,
    run_params: dict | None = None,
    env: dict | None = None,
) -> dict:
    """Construye el reporte de métricas (dict JSON-serializable) desde los CSV REALES.

    Args:
      csv_prefix: prefijo de los CSV de Locust (p. ej. `.../results/locust_run_20260101T000000`);
                  se derivan `_stats.csv`, `_stats_history.csv`, `_failures.csv`,
                  `_exceptions.csv`.
      run_params: parámetros EXACTOS de ejecución (users/spawn_rate/steady/ramp). Si es None,
                  se usan los del contrato (`EXACT_RUN_PARAMS`).
      env:        entorno (python/os/locust). Si es None, se captura del proceso actual.

    Devuelve un dict con todos los campos de R9.3 y la distribución real medida (R9.4). Lanza
    `ReportError` si los CSV requeridos (stats/failures/exceptions) faltan o no son parseables:
    el reporte NO fabrica números ni reporta un resultado vacío como válido.
    """
    paths = _resolve_csv_paths(csv_prefix)
    run_params = dict(run_params) if run_params is not None else dict(EXACT_RUN_PARAMS)
    env = dict(env) if env is not None else capture_environment()

    # --- Parseo de los CSV reales (fail-loud si faltan) ----------------------
    routes, aggregated, aggregated_raw = parse_stats_csv(paths["stats"])
    if not routes:
        raise ReportError(
            f"El stats CSV {paths['stats']} no contiene ninguna ruta conocida "
            f"({READ_ROUTES + TRANSFER_ROUTES}). No se fabrica un reporte vacío."
        )
    rejection_split = parse_failures_csv(paths["failures"])
    harness_exceptions = parse_exceptions_csv(paths["exceptions"])

    # --- Conteos por ruta / tipo / total -------------------------------------
    counts_by_route = {name: r.request_count for name, r in routes.items()}
    counts_by_type = {
        "read": sum(r.request_count for r in routes.values() if r.op_type == "read"),
        "transfer": sum(r.request_count for r in routes.values() if r.op_type == "transfer"),
    }
    total_requests = sum(counts_by_route.values())

    # --- Throughput por ruta / tipo / agregado -------------------------------
    throughput_by_route = {name: r.throughput_rps for name, r in routes.items()}
    throughput_by_type = {
        "read": sum(r.throughput_rps for r in routes.values() if r.op_type == "read"),
        "transfer": sum(r.throughput_rps for r in routes.values() if r.op_type == "transfer"),
    }
    aggregated_throughput = aggregated_raw.get(
        "throughput_rps", sum(throughput_by_route.values())
    )

    # --- Latencia p50/p95/p99 por ruta / tipo / agregado ---------------------
    latency_by_route = {
        name: LatencyGroup(p50_ms=r.p50_ms, p95_ms=r.p95_ms, p99_ms=r.p99_ms)
        for name, r in routes.items()
    }
    latency_by_type = {
        "read": _weighted_percentile_by_type(routes, "read"),
        "transfer": _weighted_percentile_by_type(routes, "transfer"),
    }

    # --- Distribución REAL medida vs objetivo (R9.4) -------------------------
    distribution = compute_measured_distribution(routes)

    # --- Fallos: esperados (negocio) vs inesperados --------------------------
    # Los errores inesperados "efectivos" para salud = fallos inesperados + excepciones del arnés.
    unexpected_total = rejection_split.unexpected_errors + harness_exceptions
    unexpected_error_rate = (
        (unexpected_total / total_requests) if total_requests > 0 else 0.0
    )

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "report_kind": "shift-bank-stage3-loadtest-metrics",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "source_csv": {k: str(v) for k, v in paths.items()},
        "environment": env,
        "run_params": run_params,
        "request_counts": {
            "by_route": counts_by_route,
            "by_type": counts_by_type,
            "total": total_requests,
        },
        "throughput_rps": {
            "by_route": throughput_by_route,
            "by_type": throughput_by_type,
            "aggregated": aggregated_throughput,
        },
        "latency_ms": {
            "by_route": {name: asdict(lg) for name, lg in latency_by_route.items()},
            "by_type": {t: asdict(lg) for t, lg in latency_by_type.items()},
            "aggregated": asdict(aggregated) if aggregated is not None else None,
            "note": (
                "p50/p95/p99 por ruta y agregado se leen directamente de las columnas "
                "50%/95%/99% del stats CSV de Locust. El percentil 'by_type' para 'read' "
                "(2 rutas) es la cota superior (máximo entre rutas) por no disponer de la "
                "distribución de latencias combinada; 'transfer' (1 ruta) es exacto."
            ),
        },
        "rejections": {
            "expected_business_rejections": rejection_split.expected_business_rejections,
            "unexpected_errors": rejection_split.unexpected_errors,
            "harness_exceptions": harness_exceptions,
            "unexpected_total_including_exceptions": unexpected_total,
            "unexpected_error_rate": round(unexpected_error_rate, 6),
            "business_rejection_detail": rejection_split.business_rejection_detail,
            "unexpected_error_detail": rejection_split.unexpected_error_detail,
            "classification_note": (
                "Rechazos de negocio ESPERADOS = fallos con etiqueta 'BusinessRejection:*' "
                "(4xx de dominio bien formado). Errores INESPERADOS = etiquetas "
                "'UnexpectedError:*' (5xx / transporte / 4xx no reconocido) + excepciones del "
                "arnés. Prefijos definidos por el locustfile (Tarea 19)."
            ),
        },
        "distribution": {
            "measured_vs_target": [asdict(d) for d in distribution],
            "target_distribution_pct": TARGET_DISTRIBUTION_PCT,
            "note": (
                "La distribución 'measured_pct' es la REAL observada (Request Count por ruta / "
                "total real * 100), no los pesos nominales de Locust (R9.4)."
            ),
        },
    }
    return report


# ---------------------------------------------------------------------------
# Escritura del reporte JSON (artefacto adicional, con timestamp, sin sobrescribir)
# ---------------------------------------------------------------------------
def write_report_json(
    report: dict,
    output_dir: str | Path,
    *,
    tag: str = "report",
    timestamp: str | None = None,
) -> Path:
    """Escribe el reporte como JSON con timestamp; NO sobrescribe artefactos previos (R9.6).

    El nombre es `loadtest_report_<tag>_<YYYYmmddTHHMMSS>.json`. Si ya existiera (colisión de
    segundo exacto), se añade un sufijo numérico para no sobrescribir nunca. Devuelve la ruta
    escrita. Los CSV originales de Locust quedan intactos (este es un artefacto ADICIONAL).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or time.strftime("%Y%m%dT%H%M%S", time.localtime())
    base_name = f"loadtest_report_{tag}_{stamp}.json"
    out_path = out_dir / base_name
    # Garantía anti-sobrescritura: sufijo incremental si el nombre ya existe.
    counter = 1
    while out_path.exists():
        out_path = out_dir / f"loadtest_report_{tag}_{stamp}_{counter}.json"
        counter += 1
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="report",
        description=(
            "Reporte de métricas de carga de Shift Bank (Etapa 3, Tarea 21). Deriva un JSON "
            "legible por máquina de los CSV REALES de Locust (R9.3/R9.4). No fabrica métricas."
        ),
    )
    parser.add_argument(
        "csv_prefix",
        help=(
            "Prefijo de los CSV de Locust (sin sufijo), p. ej. "
            ".../results/locust_run_20260101T000000. Se derivan _stats/_failures/_exceptions."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio donde escribir el JSON (default: junto a los CSV).",
    )
    parser.add_argument(
        "--tag",
        default="report",
        help="Etiqueta del nombre de archivo (p. ej. 'smoke' para ejemplos de mecánica).",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_json",
        help="Imprime el JSON en stdout además de escribirlo.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI: construye el reporte desde los CSV reales y lo escribe como JSON (sin sobrescribir)."""
    args = _build_parser().parse_args(argv)
    try:
        report = build_report(args.csv_prefix)
    except ReportError as exc:
        print(f"[report] FALLO: {exc}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or str(Path(args.csv_prefix).parent)
    out_path = write_report_json(report, output_dir, tag=args.tag)
    print(f"[report] JSON escrito en: {out_path}")
    if args.print_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    # Resumen legible.
    rc = report["request_counts"]
    rej = report["rejections"]
    print("=== report: RESUMEN ===")
    print(f"  total peticiones:            {rc['total']}")
    print(f"  por tipo:                    {rc['by_type']}")
    print(f"  throughput agregado (rps):   {report['throughput_rps']['aggregated']}")
    print(f"  rechazos negocio esperados:  {rej['expected_business_rejections']}")
    print(f"  errores inesperados:         {rej['unexpected_errors']}")
    print(f"  excepciones del arnés:       {rej['harness_exceptions']}")
    print(f"  tasa error inesperado:       {rej['unexpected_error_rate']}")
    print("  distribución real medida vs objetivo:")
    for d in report["distribution"]["measured_vs_target"]:
        tgt = "n/a" if d["target_pct"] is None else f"{d['target_pct']:.1f}%"
        print(
            f"    {d['route']:22s} count={d['request_count']:>6d}  "
            f"medida={d['measured_pct']:.2f}%  objetivo={tgt}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
