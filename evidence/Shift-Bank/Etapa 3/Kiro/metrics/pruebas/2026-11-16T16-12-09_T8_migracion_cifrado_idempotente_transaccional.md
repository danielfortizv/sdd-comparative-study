# Evidencia — Tarea 8 (M1): Migración de cifrado idempotente y transaccional

- **Fecha/hora (local):** 2026-11-16T16-12-09
- **Tarea:** T8 (auto) — `db.migrate_encryption(conn)` invocada tras `db.migrate(conn)` en el arranque.
- **Requisitos:** R3.1 (idempotencia), R3.2 (rollback transaccional total), R3.3 (preservación de datos/contratos), R3.4 (sin claro al terminar).
- **Diseño:** §1.6 (migración de cifrado de datos existentes), §8 G3.
- **AC:** AC-04.
- **Entorno:** Windows, Python 3.13.2, venv `backend/.venv`.
- **Alcance de preservación:** no se modificó `SEED-3.md` ni datos históricos de la Etapa 2; todas las pruebas usan DB temporal aislada (`isolated_db_path`).

## Qué se implementó

### `app/db.py` — `migrate_encryption(conn)`
Nueva función que recorre las columnas sensibles y cifra **en su lugar** cualquier valor en claro pendiente de migrar. Columnas objetivo (`_ENCRYPTION_TARGETS`):

| Tabla | Columna | WHERE |
|-------|---------|-------|
| `beneficiary` | `account_number` | `account_number IS NOT NULL` |
| `beneficiary` | `routing_number` | `routing_number IS NOT NULL` |
| `transfer` | `beneficiary_snapshot` | `type = 'ach' AND beneficiary_snapshot IS NOT NULL` |
| `recurring_schedule` | `beneficiary_snapshot` | `beneficiary_snapshot IS NOT NULL` |

Para cada fila se lee `rowid` y el valor; se actualiza con `UPDATE ... WHERE rowid = ?`, independiente de la PK de cada tabla.

### `app/main.py` — integración en el arranque
`_initialize_database()` ahora ejecuta `migrate_encryption(conn)` justo después de `migrate(conn)` y antes de `seed(conn)`. Se importa `migrate_encryption` desde `app.db`.

## Mecanismo de idempotencia (R3.1)
- Se usa `crypto.is_encrypted(value)` (prefijo `enc:v1:`) para **omitir** los valores ya cifrados.
- Solo se cifran valores **no nulos, no vacíos y no ya cifrados**.
- Una 2ª corrida deja el token idéntico (no re-cifra, no doble-cifra, no corrompe). Verificado por `test_migracion_idempotente_segunda_corrida_no_recifra`.
- Como el camino normal de escritura (Tarea 7) ya cifra, sobre una DB "nueva" la migración es un **no-op** idempotente — por eso el arranque del fixture `app_client` no rompe las pruebas existentes.

## Enfoque transaccional / rollback (R3.2)
- Toda la migración se ejecuta dentro de una **única transacción explícita**: `conn.execute("BEGIN")` ... `conn.commit()`, con `except Exception: conn.rollback(); raise`. Patrón idéntico a `db.migrate`.
- **No** se usa `executescript` (haría COMMIT implícito y rompería la atomicidad).
- Ante cualquier excepción a mitad de camino (valor corrupto/no decodificable o fallo de `crypto.encrypt`) se hace **ROLLBACK completo**: no queda mezcla cifrado/claro. Verificado por `test_migracion_rollback_total_ante_fallo` (monkeypatch que hace fallar la 2ª llamada a `encrypt`; se confirma que ≥2 valores se intentaron y que tras el fallo **ninguna** columna quedó cifrada).

## Sin claro al terminar (R3.4) y preservación (R3.3)
- Tras COMMIT exitoso, las 4 columnas objetivo son tokens `enc:v1:...` y `crypto.decrypt` recupera el claro original; los dígitos sensibles no aparecen crudos en el token.
- Columnas no sensibles (`name`, `bank`, `amount_cents`, `description`) y filas no objetivo (transferencia interna sin snapshot) quedan intactas. Verificado por `test_migracion_preserva_no_sensibles_y_filas_no_objetivo`.

## Pruebas — `tests/test_encryption_migration.py`
Siembra **texto en claro** con `sqlite3` crudo (bypass del cifrado del repositorio) para simular registros heredados, luego corre `migrate_encryption`.

Casos:
1. `test_migracion_cifra_claro_y_decrypt_recupera_original` — todas las columnas → `enc:v1:`; `decrypt` recupera el claro (R3.4).
2. `test_migracion_idempotente_segunda_corrida_no_recifra` — 2ª corrida no cambia nada; `decrypt` sigue correcto (R3.1).
3. `test_migracion_rollback_total_ante_fallo` — fallo inyectado a mitad → rollback total, nada cifrado (R3.2).
4. `test_migracion_preserva_no_sensibles_y_filas_no_objetivo` — no sensibles y filas no objetivo intactas (R3.3).
5. `test_migracion_noop_en_db_sin_registros` — no-op seguro en DB sin registros (idempotencia de arranque).

## Comandos exactos y resultados reales

### Suite nueva
```
.\.venv\Scripts\python.exe -m pytest tests/test_encryption_migration.py -v
```
Resultado: **5 passed in 0.32s** (exit 0). Los 5 casos PASSED.

### Suite completa
```
.\.venv\Scripts\python.exe -m pytest -q
```
Resultado: **260 passed, 1 warning in 17.04s** (exit 0).

- Conteo: 255 previos + 5 nuevos = **260** ✅.
- El único warning es un `DeprecationWarning` preexistente de `starlette.testclient` (anyio), no relacionado con esta tarea.
- El arranque del fixture `app_client` dispara `lifespan` → `migrate_encryption`; como las escrituras de la Tarea 7 ya están cifradas, la migración es no-op y no rompe la regresión heredada.

## Veredicto
**PASS.** Función implementada e integrada en el arranque; idempotencia (via `is_encrypted`) y rollback transaccional total (BEGIN/COMMIT + rollback, sin `executescript`) demostrados con pruebas reales. Regresión completa verde (260/260).
