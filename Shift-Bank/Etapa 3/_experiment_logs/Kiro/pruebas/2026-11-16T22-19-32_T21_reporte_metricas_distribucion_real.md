# Evidencia — Tarea 21: Reporte de métricas con distribución real medida

- **Fecha:** 2026-11-16T22:19:32 (-0500)
- **Tarea:** 21 (auto) — Reporte de métricas con distribución real medida
- **Spec:** `Etapa 3/Kiro/.kiro/specs/shift-bank-stage3`
- **Requisitos:** R9.3 (reporte completo de métricas), R9.4 (distribución real medida)
- **Diseño:** §3.3 (Métricas, umbrales y evidencia); §3.2 (distribución real medida)
- **AC:** AC-11
- **Entorno:** Python 3.13.2 · Windows-11-10.0.26300-SP0 · Locust 2.47.0 (venv `backend/.venv`)

> **ADVERTENCIA (no es el baseline):** El ejemplo real incluido abajo está DERIVADO de los CSV
> de **SMOKE de mecánica** que dejó la Tarea 20 (`loadtest/results/locust_smoke_20261116T220006_*`),
> NO del baseline oficial de 60 s. El baseline oficial es la **Tarea 23** y NO se ejecuta aquí.

---

## 1. Artefactos creados / modificados

| Archivo | Tipo | Propósito |
|---|---|---|
| `Etapa 3/Kiro/loadtest/report.py` | nuevo | Módulo de reporte: parsea los CSV reales de Locust y emite JSON (R9.3/R9.4). |
| `Etapa 3/Kiro/backend/tests/test_loadtest_report.py` | nuevo | 13 pruebas unitarias con CSV sintéticos de contenido conocido. |
| `Etapa 3/Kiro/loadtest/results/loadtest_report_smoke_20261116T221916.json` | nuevo (ejemplo) | Reporte **smoke-derived** (NO baseline) generado desde los CSV de la Tarea 20. |

No se modificó `SEED-3.md` ni dato alguno de la Etapa 2. Los CSV originales de Locust quedan
intactos: el JSON es un artefacto **adicional** con timestamp (R9.6).

---

## 2. Esquema del reporte JSON (R9.3) — campos

`build_report(csv_prefix, run_params, env) -> dict`. Claves de primer nivel:

- `schema_version`, `report_kind`, `generated_at`, `source_csv` (rutas de los 4 CSV usados).
- `environment`: `python_version`, `os`, `locust_version` (R9.3 — entorno real).
  - La versión de Locust se obtiene de `importlib.metadata.version("locust")` y **NO** importando
    `locust`, porque importar el paquete dispara `gevent.monkey.patch_all()` al cargar, lo que
    interfiere con el resto del arnés (TestClient/anyio) y colgaba la suite. Leer metadatos evita
    ese efecto colateral (ver §6).
- `run_params`: `users=30`, `spawn_rate=5`, `steady_seconds=60`, `ramp_up_seconds=6` (contrato
  exacto R9.1; 30/5 = 6 s de ramp).
- `request_counts`: `by_route`, `by_type` (`read`/`transfer`), `total`.
- `throughput_rps`: `by_route`, `by_type`, `aggregated` (leído de la fila `Aggregated`).
- `latency_ms`: `by_route`, `by_type`, `aggregated` (cada uno con `p50_ms`/`p95_ms`/`p99_ms`) +
  `note`.
- `rejections`: `expected_business_rejections`, `unexpected_errors`, `harness_exceptions`,
  `unexpected_total_including_exceptions`, `unexpected_error_rate`, `business_rejection_detail`,
  `unexpected_error_detail`, `classification_note`.
- `distribution`: `measured_vs_target` (lista de `{route, request_count, measured_pct,
  target_pct}`), `target_distribution_pct` (60/30/10), `note`.

`write_report_json(report, output_dir, tag, timestamp)` escribe
`loadtest_report_<tag>_<YYYYmmddTHHMMSS>.json` y **nunca sobrescribe** (sufijo incremental ante
colisión de segundo exacto).

### Columnas CSV consumidas (contrato Locust 2.x, verificado contra los artefactos reales)

- `_stats.csv`: `Type, Name, Request Count, Failure Count, Requests/s, 50%, 95%, 99%` (más
  columnas que se ignoran). La fila agregada es `Name == "Aggregated"` con `Type` vacío.
- `_failures.csv`: `Method, Name, Error, Occurrences, First Seen, Last Seen`.
- `_exceptions.csv`: `Count, Message, Traceback, Nodes`.
- `_stats_history.csv`: referenciado en `source_csv` (no requerido para los agregados del reporte).

Las celdas `N/A`/vacías se normalizan a 0; celdas no numéricas en columnas numéricas → `ReportError`.

---

## 3. Cómo se calcula la distribución REAL medida (R9.4)

Para cada ruta conocida se toma `Request Count` del `_stats.csv`. El total real es la suma de
esos conteos. El porcentaje medido por ruta es `request_count / total_real * 100`. Se presenta
**junto** al objetivo nominal (`target_distribution_pct` = 60/30/10). **No** se usan los pesos
`@task` 6/3/1 de Locust: se mide lo realmente emitido. Si el total es 0, los porcentajes medidos
son 0.0 (no se fabrica un 60/30/10 ficticio).

Clasificación de rutas (design.md §3.2/§3.3):
- `read`: `GET /api/accounts`, `GET /api/transfers`.
- `transfer`: `POST /api/transfers`.

---

## 4. Lógica de separación esperados vs inesperados (R9.3)

Se parsea la columna `Error` de `_failures.csv`, que contiene la etiqueta que el locustfile
(Tarea 19) asignó vía `response.failure(...)`:

- Prefijo `BusinessRejection:` → **rechazo de negocio ESPERADO** (4xx de dominio bien formado);
  se suma a `expected_business_rejections` y se detalla por código.
- Cualquier otra etiqueta de fallo, incluido el prefijo `UnexpectedError:` (5xx / transporte /
  4xx no reconocido) → **error INESPERADO**; se suma a `unexpected_errors` y se detalla.
- Las **excepciones del arnés** (`_exceptions.csv`, columna `Count`) nunca son rechazos de negocio;
  se cuentan aparte (`harness_exceptions`) y se suman a `unexpected_total_including_exceptions`.
- `unexpected_error_rate = unexpected_total_including_exceptions / total_requests`.

Un `_failures.csv`/`_exceptions.csv` con sólo cabecera (sin filas) ⇒ cero fallos (caso sano con el
aislamiento/siembra de la Tarea 18).

### Percentil `by_type`

- `transfer` tiene 1 ruta (`POST /api/transfers`) → el percentil del tipo es **exacto** (el de
  esa ruta).
- `read` tiene 2 rutas → se reporta la **cota superior** (máximo del percentil entre rutas), por
  no disponer de la distribución de latencias combinada en el `_stats.csv`. Nunca subestima la
  latencia del tipo; documentado en `latency_ms.note`.

---

## 5. Prueba unitaria (CSV sintético de contenido conocido)

`backend/tests/test_loadtest_report.py` (13 pruebas). Alimenta un `_stats.csv`/`_failures.csv`/
`_exceptions.csv` sintéticos con conteos elegidos para dar una distribución real **≠** 60/30/10
(accounts=600, GET transfers=280, POST=120 → 60.0% / 28.0% / 12.0% sobre total=1000), demostrando
que se mide la realidad y no los pesos. Afirma:

- p50/p95/p99 por ruta, por tipo (transfer exacto, read = cota superior) y agregado.
- throughput por ruta/tipo y agregado (leído de la fila `Aggregated`, no recalculado).
- conteos por ruta/tipo/total.
- distribución medida (60/28/12) ≠ objetivo (60/30/10), suma ≈ 100%.
- separación esperados (3) vs inesperados (5) + excepciones del arnés (2) → total inesperado 7,
  tasa 7/1000; y caso "sólo cabecera" → todo en cero.
- entorno/params exactos; respeta `run_params`/`env` explícitos.
- **fail-loud:** `ReportError` ante stats/failures faltante, columnas inválidas, o stats sin
  ninguna ruta conocida (nunca fabrica números ni reporta vacío como válido).
- escritura JSON adicional, con timestamp, sin sobrescribir; round-trip JSON; CSV originales
  intactos.

### Resultado de la prueba unitaria

```
$ backend/.venv/Scripts/python.exe -m pytest tests/test_loadtest_report.py -q
.............                                                            [100%]
13 passed in 0.19s
```

### Suite completa (regresión)

```
$ backend/.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
.....................................................................    [100%]
357 passed, 1 warning in 18.48s
```

344 (heredadas) + 13 (nuevas) = **357 PASS**. El único warning es el `DeprecationWarning`
preexistente de Starlette/anyio, no relacionado con esta tarea.

---

## 6. Ejemplo REAL smoke-derived (NO baseline)

Comando (ejecutado desde `Etapa 3/Kiro/`):

```
backend/.venv/Scripts/python.exe -m loadtest.report \
    "loadtest/results/locust_smoke_20261116T220006" --tag smoke --print
```

Salida JSON: `loadtest/results/loadtest_report_smoke_20261116T221916.json`. Métricas clave
(derivadas de los CSV reales del SMOKE de la Tarea 20, **no** del baseline de 60 s):

- Total peticiones: **356** (read=319, transfer=37); throughput agregado ≈ **35.21 rps**.
- Latencia agregada: p50=10 ms, p95=1600 ms, p99=4200 ms. (Valores altos propios de un smoke de
  mecánica en entorno limitado; **no** representan rendimiento de baseline.)
- Rechazos de negocio esperados: 0 · errores inesperados: 0 · excepciones del arnés: 0 · tasa de
  error inesperado: 0.0 (coherente con `_failures.csv`/`_exceptions.csv` sólo-cabecera).
- **Distribución REAL medida vs objetivo (R9.4):**

| Ruta | Request Count | Medida | Objetivo |
|---|---:|---:|---:|
| GET /api/accounts | 216 | 60.67% | 60.0% |
| GET /api/transfers | 103 | 28.93% | 30.0% |
| POST /api/transfers | 37 | 10.39% | 10.0% |

La medida (60.67/28.93/10.39) difiere del objetivo nominal (60/30/10), lo que confirma que el
reporte **mide la realidad** observada y no asume los pesos `@task` de Locust (R9.4).

> Reiteración: este ejemplo es **smoke-derived** (Tarea 20), **no** el baseline oficial (Tarea 23).

---

## 7. Veredicto

- ✅ `build_report(csv_prefix, run_params, env) -> dict` + `write_report_json(...)` implementados.
- ✅ Reporte JSON con TODOS los campos de R9.3 (p50/p95/p99 por tipo y agregado, throughput,
  conteos, esperados vs inesperados, entorno, parámetros exactos) y distribución real medida (R9.4).
- ✅ Derivado de CSV reales; fail-loud si faltan/ilegibles; nunca fabrica números.
- ✅ Prueba unitaria sobre CSV sintético: **13 PASS**. Suite completa: **357 PASS** (344 + 13).
- ✅ JSON adicional con timestamp, sin sobrescribir; CSV originales preservados.
- ✅ No se tocó `SEED-3.md` ni datos de la Etapa 2; no se optimizó la app; no se ejecutó el
  baseline oficial (Tarea 23).

**ESTADO: PASS.**
