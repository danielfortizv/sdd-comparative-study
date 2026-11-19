# Evidencia — Tarea 11 (verificación): Detección de manipulación y endurecimiento

- **Fecha/hora:** 2026-11-16T16:57:58 (hora local de la máquina)
- **Spec:** `shift-bank-stage3` · Tarea 11 (auto, verificación) · AC-06
- **Requisitos:** R6.4, R6.5, R6.6 · **Diseño:** §2.5, §2.9, §10
- **Alcance:** SOLO pruebas. No se modificó `app/audit.py` ni ningún comportamiento de aplicación.
  No se tocó `SEED-3.md` ni datos históricos de la Etapa 2.
- **Archivo creado:** `backend/tests/test_audit_tamper.py` (13 pruebas, incluidas 4 variantes
  parametrizadas del caso 1).
- **Entorno:** `backend/.venv` (Python 3.13.2, pytest 8.3.4). DB SQLite temporal y aislada por
  prueba (esquema migrado de la Tarea 9); clave HMAC de prueba provista por `conftest.py`.

## Metodología

Para simular a un atacante con acceso **directo** a la base de datos (fuera de la ruta de la
aplicación), las pruebas de manipulación hacen `DROP TRIGGER` del trigger relevante
(`audit_log_no_update` / `audit_log_no_delete`), mutan la fila/ancla con SQL crudo, y luego
invocan `audit.verify_chain(conn)`. Las pruebas de endurecimiento (caso 4) **no** sueltan los
triggers: comprueban que SQLite aborta el UPDATE/DELETE ordinario.

Se apoya en el esquema de la Tarea 10: `verify_chain` devuelve `VerifyResult(ok, failed_seq,
reason)` comprobando, en orden, (c) contigüidad de `seq`, (b) encadenado `prev_hmac`, (a)
recomputación de `entry_hmac`, y finalmente el ancla de cola (§2.9).

## Resultados por caso negativo

| # | Caso | Mutación | `verify_chain` devolvió | ¿Detectado? |
|---|------|----------|-------------------------|-------------|
| 1a | Contenido: `payload` | UPDATE payload seq=2 | `ok=False, failed_seq=2`, razón menciona `entry_hmac` | SÍ |
| 1b | Contenido: `entry_hmac` | UPDATE entry_hmac seq=2 | `ok=False, failed_seq=2` | SÍ |
| 1c | Contenido: `outcome` | UPDATE outcome seq=2 (rejected→success) | `ok=False, failed_seq=2` | SÍ |
| 1d | Contenido: `entity_ref` | UPDATE entity_ref seq=2 | `ok=False, failed_seq=2` | SÍ |
| 2a | Cadena rota: `prev_hmac` reescrito | UPDATE prev_hmac seq=3 | `ok=False, failed_seq=3`, razón menciona `prev_hmac` | SÍ |
| 2b | Reorden: swap de `prev_hmac` (seq 2↔3) | UPDATE prev_hmac seq=2,3 | `ok=False, failed_seq=2` | SÍ |
| 3 | Eliminación intermedia (hueco) | DELETE seq=3 (de 1..5) | `ok=False, failed_seq=4`, razón "secuencia no contigua" | SÍ |
| 4a | Endurecimiento: UPDATE ordinario | UPDATE con triggers activos | `sqlite3.Error` ("append-only"); cadena intacta (`ok=True` tras rollback) | BLOQUEADO |
| 4b | Endurecimiento: DELETE ordinario | DELETE con triggers activos | `sqlite3.Error` ("append-only"); cadena intacta (`ok=True` tras rollback) | BLOQUEADO |
| 5a | Truncación de cola (1 fila) | DELETE seq=5, ancla sin tocar | `ok=False, failed_seq=5`, razón "truncación del final" | SÍ (vía ancla) |
| 5b | Truncación de cola (2 filas) | DELETE seq IN (5,6), ancla sin tocar | `ok=False, failed_seq=6`, razón "truncación del final" | SÍ (vía ancla) |
| 6 | **Límite documentado**: truncación + ancla reescrita | DELETE seq=5 **y** UPDATE ancla→seq=4 | `ok=True, failed_seq=None, reason=None` | **No detectable (esperado)** |

### Nota sobre el caso 6 (límite del modelo de amenazas, R6.6 / §2.9 / §10)

El caso 6 asienta el **límite reconocido**: con control total de la DB (incluida la tabla
`audit_anchor`) y de la clave HMAC, el atacante puede truncar la cola y reescribir el ancla para
que referencie la nueva cola, dejando un estado globalmente consistente. En ese escenario
`verify_chain` devuelve `ok=True` — comportamiento **esperado y correcto** dentro del modelo; no
se reclama inmutabilidad absoluta. La prueba afirma explícitamente este resultado para hacer la
frontera visible, no para reclamar una protección inexistente.

### Verificación de la condición de parada

Los casos 1–3 y 5 fueron **todos** detectados por `verify_chain` en el `seq` correcto. No se
encontró ninguna brecha real; no se modificó `app/audit.py`.

## Conteos reales de pytest

```
# Archivo nuevo
python -m pytest tests/test_audit_tamper.py -v
=> 13 passed in 0.60s

# Suite completa
python -m pytest -q
=> 298 passed, 1 warning in 14.73s
```

- Baseline previo: 285 pruebas. Nuevas: 13 (caso 1 × 4 variantes parametrizadas + casos 2a, 2b,
  3, 4a, 4b, 5a, 5b, 6, y una prueba extra de razón del caso 1). Total: **298 passed**.
- La advertencia (1 warning) es un `DeprecationWarning` preexistente de `starlette.testclient`
  (anyio), ajeno a esta tarea.

## Conclusión

**PASS.** Todos los negativos (manipulación de contenido, cadena rota/reordenada, eliminación
intermedia, truncación de cola vía ancla) son detectados en el `seq` correcto; los UPDATE/DELETE
ordinarios son abortados por los triggers append-only; y el límite de truncación con ancla
reescrita queda documentado como comportamiento esperado. Suite completa verde (298).
