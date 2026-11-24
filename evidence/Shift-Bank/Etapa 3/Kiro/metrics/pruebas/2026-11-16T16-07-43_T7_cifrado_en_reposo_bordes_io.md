# Evidencia T7 — Cifrado en reposo en el repositorio (bordes de E/S)

- **Fecha/hora:** 2026-11-16T16:07:43-05:00
- **Tarea:** 7 (auto) — Cifrado en reposo en el repositorio (bordes de E/S)
- **Spec:** `.kiro/specs/shift-bank-stage3` · **Diseño:** §1.5 · **Requisitos:** R1.1, R1.2, R1.3, R1.5, R1.6, R14 · **AC:** AC-01, AC-02, AC-04
- **Entorno:** Windows · Python 3.13.2 (`backend/.venv`) · cryptography 50.0.2
- **Restricciones respetadas:** no se tocó `SEED-3.md` ni datos históricos de la Etapa 2; DB temporal aislada por prueba (`conftest.py`). Se reutiliza `app/crypto.py` (Tarea 6). `name`/`bank` quedan en claro (fuera de alcance, design.md §1.5). Modelo monetario y contratos de decimales intactos.

## Objetivo

Insertar cifrar-al-escribir / descifrar-al-leer EXACTAMENTE en los bordes de E/S heredados, de
modo que los identificadores sensibles solo se almacenen como tokens `enc:v1:...` en SQLite,
mientras la capa de servicio y las respuestas de API siguen viendo/retornando claro-luego-
enmascarado (sin cambio de contrato).

## Funciones exactas modificadas

### `app/ach_repository.py`
- `import crypto` añadido.
- `create_beneficiary(...)`: **cifra** `routing_number` y `account_number` con `crypto.encrypt`
  antes del INSERT. `name`/`bank` sin cambios.
- `_decrypt_beneficiary_row(row)` (nuevo helper): descifra routing/cuenta y devuelve un `dict`
  (acceso por clave idéntico a `sqlite3.Row` para los llamadores).
- `list_beneficiaries(...)`: devuelve filas **descifradas** (lista de dicts).
- `get_beneficiary(...)`: devuelve la fila **descifrada** o `None`.
- `create_ach_no_commit(... beneficiary_snapshot=...)`: **cifra el JSON COMPLETO** del snapshot
  como un único token antes del INSERT.
- `get_ach_by_reference(...)`: devuelve un `dict` con `beneficiary_snapshot` **descifrado** en la
  lectura (otras columnas intactas).

### `app/repository.py`
- `import crypto` añadido.
- `_row_to_schedule(row)`: **descifra** `beneficiary_snapshot` al construir el `Schedule`
  (cubre `get_schedule`, `list_due_schedules`, `list_schedules` y la fila de retorno de
  `create_schedule`). `NULL` (schedules internos) se conserva tal cual.
- `create_schedule(... beneficiary_snapshot=...)`: **cifra** el snapshot JSON antes del INSERT
  (solo si no es `None`).

### `app/routers/transfers.py`
- `get_history`: en las entradas `type == "ach"`, **descifra** `beneficiary_snapshot` antes de
  `json.loads`; el enmascarado (cuenta a últimos 4 + `name`/`bank`) queda EXACTAMENTE igual.

## Cómo se evita la doble cifra y los desajustes cifrar/descifrar

Regla invariante: **un valor leído de la DB se descifra una vez; un valor escrito en la DB se
cifra una vez.**

- **Beneficiario:** se cifra en `create_beneficiary` (escritura) y se descifra en
  `list_beneficiaries`/`get_beneficiary` (lectura). El servicio y `beneficiaries.public_view`
  operan siempre sobre claro.
- **Snapshot ACH (`transfer.beneficiary_snapshot`):** `create_ach_no_commit` recibe SIEMPRE JSON
  en claro y lo cifra una vez. Las dos rutas que lo alimentan entregan claro:
  - Ruta interactiva (`ach_service.create_ach`): construye `snapshot_json` desde el snapshot en
    claro (que a su vez proviene de `get_beneficiary`, ya descifrado, o del ad hoc del request).
  - Ruta recurrente (`recurring_service._execute_ach_in_tx`): reutiliza
    `schedule.beneficiary_snapshot`, que `_row_to_schedule` **ya descifró** al leer el schedule.
    Al reescribir la ACH, `create_ach_no_commit` lo cifra de nuevo → exactamente una capa.
- **Snapshot de schedule (`recurring_schedule.beneficiary_snapshot`):** `create_schedule` cifra
  al escribir; `_row_to_schedule` descifra al leer. El `SELECT *` que `create_schedule` hace
  tras el INSERT pasa por `_row_to_schedule`, por lo que el `Schedule` devuelto trae el snapshot
  en claro (consistente con el comportamiento previo).
- **Historial (`routers/transfers.py`):** lee crudo de la tabla y descifra justo antes de
  `json.loads`. No reescribe, así que no hay riesgo de doble cifra.

Sin fallback silencioso a texto plano en la escritura: toda escritura sensible pasa por
`crypto.encrypt`. Las lecturas en operación normal esperan tokens cifrados (los datos de seed y
ad-hoc de un DB de prueba fresco se crean por estas mismas rutas de escritura, por lo que ya
están cifrados). Las filas internas del `seed.py` no son ACH (`type` interno, sin snapshot), por
lo que el historial no intenta descifrarlas.

## Verificación en reposo (`tests/test_encryption_at_rest.py`, nuevo)

4 pruebas, todas PASS:

1. `test_beneficiario_cifrado_en_reposo_pero_enmascarado_en_api`: `beneficiary.routing_number` y
   `beneficiary.account_number` crudos empiezan por `enc:v1:`; sin dígitos sensibles crudos; la
   API devuelve `account_masked == "••••3210"` y `routing_number == "123456789"` (sin cuenta
   completa). El listado enmascara igual.
2. `test_ach_snapshot_cifrado_en_reposo_pero_historial_enmascarado`: `transfer.beneficiary_snapshot`
   crudo empieza por `enc:v1:` y no contiene el JSON claro; el beneficiario guardado vía
   `save_adhoc` también queda cifrado; el historial ACH descifra-al-leer y enmascara igual
   (forma inalterada; sin token `enc:` ni cuenta completa en la respuesta).
3. `test_schedule_snapshot_cifrado_en_reposo`: `recurring_schedule.beneficiary_snapshot` crudo
   empieza por `enc:v1:`; la lista de schedules sigue funcionando (decrypt-on-read).
4. `test_sin_claro_en_ninguna_columna_sensible`: barrido defensivo — tras beneficiario + ACH +
   schedule, TODAS las columnas sensibles (`beneficiary.routing_number/account_number`,
   `transfer.beneficiary_snapshot`, `recurring_schedule.beneficiary_snapshot`) empiezan por
   `enc:v1:` y ninguna contiene los dígitos en claro.

Las aserciones en reposo leen la DB con una conexión `sqlite3` cruda (sin pasar por los bordes
de descifrado), garantizando que se inspecciona el contenido real persistido.

## Resultados de pruebas (reales)

Comando: `python -m pytest -q` (desde `backend/`, con `backend/.venv`).

### Suite dirigida (decrypt-on-read preserva comportamiento heredado)
`tests/test_ach.py tests/test_recurring.py tests/test_recurring_api.py tests/test_recurring_execution.py`
→ **85 passed, 1 warning**.

### Nuevo archivo de cifrado en reposo
`tests/test_encryption_at_rest.py` → **4 passed, 1 warning**.

### Suite COMPLETA (heredada E1/E2 + Etapa 3)
`python -m pytest -q` → **255 passed, 1 warning in ~16.07s**.

- Baseline previo: 251 pruebas. Nuevas: 4 (`test_encryption_at_rest.py`). Total: **255**.
- Cero regresiones: todas las pruebas heredadas de ACH/beneficiarios/recurrentes/historial pasan
  sin cambios, lo que demuestra que el descifrado-al-leer preserva el comportamiento observable.
- La única advertencia es un `DeprecationWarning` de `starlette.testclient` preexistente (no
  relacionado con este cambio).

## Veredicto

**PASS.** Cifrado en reposo activo en los bordes de E/S; contratos de API y del historial sin
cambios de forma; ninguna columna sensible contiene texto plano; regresión completa verde
(255/255) sobre datos cifrados. Sin ciphertext ni material de clave en respuestas de API.
