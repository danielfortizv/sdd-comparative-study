# Etapa 4 — Kiro — Resumen de métricas

> Solo valores observados. **N/D** = sin evidencia en el workspace. Cuenta NUEVA de Kiro Student
> únicamente; no se mezcla con la cuenta anterior. No se inventan totales.

## 1. Tareas (SDD nativo)
- Tareas principales: **31/31 completas**. Gates de investigador aprobados: T4, T28, T30.
- Denominador estándar del estudio: **31 tareas** (no confundir con sub-pruebas). Las sub-pruebas
  (p. ej. 11 pruebas FX) NO cuentan como tareas.

## 2. Pruebas (observadas)
| Suite | Resultado | Exit |
|---|---|---|
| Backend Pytest (final) | 444 passed, 1 warning | 0 |
| Backend Pytest (baseline heredado M0) | 372 passed | 0 |
| Frontend Vitest (final) | 14 passed (3 heredadas + 11 Stage 4) | 0 |
| Frontend build `tsc && vite build` | 45 módulos transformados | 0 |

## 3. Cobertura (misma metodología PRE y POST)
- Backend (coverage.py, `--cov=app`): **94%** local (TOTAL).
- Medición del proyecto en SonarQube: **coverage 49,6%** (línea 49,6 / rama 50,8).
  - Denominador: `backend/app` + `frontend/src` (según `sonar-project-stage4.properties`),
    excluyendo tests. El valor global baja porque el frontend React heredado no tiene pruebas
    unitarias (lcov cubre API client + módulos Stage 4). Es un número honesto, no inflado.
- Artefactos: `backend/coverage.xml`, `frontend/coverage/lcov.info` (+ copias PRE/POST en
  `sonarqube/`).

## 4. Carga Locust en vivo (30 / 5 / 60, contrato exacto)
- Peticiones totales: **8.409**; fallos: **0**; throughput ≈ **128,7 req/s**.
- p95: lecturas 53 ms (accounts) / 61 ms (history); operaciones 73 ms (conversión) / 71 ms (interna).
- Distribución medida ≈ 60/30/10. Umbrales (p95 lectura <200, p95 op <500, errores <1%): CUMPLE.
- Invariantes post-carga: `invariants_ok=True`, `audit_chain_ok=True`.

## 5. Despliegue Docker (en vivo)
- build/up exit 0; backend+nginx healthy; HTTPS 200 (fixture D-02); redirect 301; conversión HTTPS
  200; persistencia tras restart; audit verify {ok:true}; fail-closed con claves vacías.
- Teardown `down -v` exit 0; `.env`/`certs` eliminados; workspace limpio.

## 6. SonarQube — PRE vs POST (proyecto Shift-Bank---Stage-4---Kiro)
| Métrica | PRE | POST | Δ |
|---|---|---|---|
| CE status | SUCCESS | SUCCESS | — |
| analysisId | cd37bcc9-6884-4dd4-a92a-d4e8f374cb62 | bb7434e4-29e5-424e-8799-8f2c8b1cc936 | — |
| Quality Gate | OK | OK (new_violations=0) | — |
| issues (unresolved) | 162 | 158 | −4 |
| bugs | 0 | 0 | 0 |
| vulnerabilities | 1 | 0 | **−1** |
| code_smells | 161 | 158 | −3 |
| security_hotspots | 0 | 0 | 0 |
| sqale_index (deuda, min) | 783 | 768 | −15 |
| sqale_debt_ratio | 0,4% | 0,4% | 0 |
| coverage | 49,7% | 49,6% | −0,1 (mismo alcance) |
| duplicated_lines_density | 0,0% | 0,0% | 0 |

### Issues por clave (verificado)
- Resueltos (4): `1c9b78d4` S2245 (vuln, apiV2.ts:47, CLOSED/FIXED), `9a8ff686` S7767
  (apiV2.ts:47), `1dd96ef1` S6759 (ConversionForm:14), `6f57b9f8` S6759 (MultiCurrencyDashboard:12).
- Introducidos: **0**.

### Tradicional (ratings)
| Rating | PRE | POST |
|---|---|---|
| reliability | A (1.0) | A (1.0) |
| security | C (3.0) | **A (1.0)** |
| maintainability (sqale) | A (1.0) | A (1.0) |

### MQR (impactos y ratings — NO mezclar con tradicional)
| MQR | PRE | POST |
|---|---|---|
| impactos SECURITY | MED 1 | **0** |
| impactos RELIABILITY | HIGH 1 / MED 2 / LOW 3 | MED 2 / LOW 3 |
| impactos MAINTAINABILITY | HIGH 3 / MED 122 / LOW 33 / INFO 1 | HIGH 2 / MED 122 / LOW 31 / INFO 1 |
| rating security | C (3.0) | **A (1.0)** |
| rating reliability | **D (4.0)** | **C (3.0)** |
| rating maintainability | A (1.0) | A (1.0) |
| remediación maintainability | 743 min | 728 min |
| remediación reliability | 60 min | 55 min |

## 7. D1 — medición de créditos (cuenta NUEVA)
| Dato | Valor | Fuente |
|---|---|---|
| Plan | Kiro Student | investigador |
| Snapshot PRE (2026-11-18) usados | 30,24 / 1000 | investigador (`D1/D1-credit-snapshot-stage4.md`) |
| Snapshot PRE restantes | 969,76 | investigador |
| Snapshot POST (fin Etapa 4) | **N/D** | no provisto |
| Créditos consumidos en Etapa 4 (delta) | **N/D** | sin snapshot POST ni export de uso |
| Interacciones / mensajes | **N/D** | sin export de sesión en el workspace |
| Tool calls / subagentes | **N/D** | sin export de sesión |
| Timestamps de sesión | **N/D** | sin export de sesión |

Nota: `preparacion/D1/session-exports/` solo contiene `.gitkeep`; no hay archivo de uso. El
snapshot 898,98 pertenece a OTRA cuenta (histórico; NO es el baseline de la Etapa 4). No se
calcula ni se inventa ningún delta.

## 8. Entorno
- Python 3.13.2; pip 26.x; venv aislado. Node v20.17.0; npm 11.6.3. Docker 29.9.3 / Compose v5.7.0.
- Diferencia vs preparación: Node v24.19.0/npm 11.17.0 (registrado, no oculto; resultados
  equivalentes).
