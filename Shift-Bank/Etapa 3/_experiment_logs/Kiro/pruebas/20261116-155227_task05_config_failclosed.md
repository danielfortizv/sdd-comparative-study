# Evidencia — Tarea 5 (Kiro, Etapa 3): Configuración externa de claves con validación fail-closed

- **Fecha/hora (local):** 2026-11-16 15:52:27
- **Spec:** `.kiro/specs/shift-bank-stage3`
- **Tarea:** 5 (auto) — Configuración externa de claves con validación fail-closed (`config.py`, `main.py`)
- **Requisitos:** R2.1, R2.2, R2.6, R15.3
- **Diseño:** §1.3, §1.4, §2.3, §2.6
- **AC:** AC-02, AC-03
- **Backend:** `Etapa 3/Kiro/backend`
- **Entorno:** Windows, Python 3.13.2, pytest 8.3.4 (venv `backend/.venv`)

## Alcance y restricciones respetadas

- No se modificó `SEED-3.md` ni datos históricos de la Etapa 2.
- No se hornea material de clave en el código de la app ni en `requirements*.txt`.
- El material de clave nunca se registra en logs/errores (verificado por test).

## Cambios de código (archivos / funciones)

### `app/config.py` (MOD)
Se añadió la sección "Etapa 3: claves externas" **sin valores por defecto inseguros**:

- **Imports:** `base64`, `binascii`, `os`.
- **Constantes de nombres de variables de entorno:**
  - `ENV_ENC_KEYS = "SHIFT_ENC_KEYS"`
  - `ENV_ENC_ACTIVE_KID = "SHIFT_ENC_ACTIVE_KID"`
  - `ENV_AUDIT_HMAC_KEY = "SHIFT_AUDIT_HMAC_KEY"`
  - `ENV_ADMIN_TOKEN = "SHIFT_ADMIN_TOKEN"`
  - `ENC_KEY_LENGTH_BYTES = 32` (AES-256).
- **`class ConfigError(RuntimeError)`** — error tipado de arranque fail-closed; el mensaje
  identifica la variable afectada pero **nunca** incluye material de clave (R2.6). Nota: la
  Tarea 6 profundizará la validación criptográfica en `crypto.CryptoConfigError`.
- **Accesores (solo lectura del entorno, sin defaults):**
  `get_enc_keys_raw()`, `get_enc_active_kid()`, `get_audit_hmac_key_raw()`, `get_admin_token()`.
- **Helpers de validación:**
  - `_validate_enc_keys()` — presencia de `SHIFT_ENC_KEYS` y `SHIFT_ENC_ACTIVE_KID`; parseo
    `kid:base64`; **saneamiento base64** (`b64decode(validate=True)`) y **longitud 32 bytes**;
    el `kid` activo debe existir en el mapa. Errores sin exponer el valor de la clave.
  - `_validate_audit_hmac_key()` — `SHIFT_AUDIT_HMAC_KEY` presente y no vacío (R6.3).
  - **`validate_startup_config()`** — orquesta ambos; es el único punto público que `main.py`
    invoca. Validación mínima intencional para Tarea 5 (presencia + base64/longitud del cifrado;
    no-vacío del HMAC); la Tarea 6 la profundiza.

### `app/main.py` (MOD)
- Nuevo import: `from . import config`.
- En `lifespan` (startup), **antes** de `_initialize_database()`:
  ```python
  config.validate_startup_config()
  _initialize_database()
  ```
  Si una clave requerida falta/ es inválida, `validate_startup_config` lanza `ConfigError`, la
  excepción propaga fuera de `lifespan` y **el proceso no sirve tráfico** (fail-closed,
  R2.2/R12.2/R15.3). Docstring de `lifespan` actualizado para documentar el comportamiento.

### `tests/conftest.py` (MOD) — provisión de claves SOLO-PRUEBAS
El arnés heredado arranca la app vía `TestClient` (dispara `lifespan`), que ahora exige claves.
Para mantener verde la suite **sin debilitar** el fail-closed de producción, el arnés fija claves
de prueba deterministas y claramente etiquetadas **antes de importar/arrancar la app** (mismo
patrón con que ya se parchea `DB_PATH`):

- Constantes de prueba: `TEST_ENC_KID = "test"`, `TEST_ENC_KEY_B64` (base64 de 32 bytes),
  `TEST_ENC_KEYS = "test:<b64>"`, `TEST_AUDIT_HMAC_KEY`, `TEST_ADMIN_TOKEN`.
- `_set_test_key_env()` usa `os.environ.setdefault(...)` (respeta valores de CI si existen) para
  `SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`, `SHIFT_ADMIN_TOKEN`.
- Se llama a `_set_test_key_env()` al importar `conftest.py` y en un fixture `autouse`
  `_ensure_test_keys` (restaura las claves antes de cada test, por si un negativo las borró).
- **Estas claves viven solo en el arnés**; no están en el código de la app ni en requirements.

### `tests/test_config_failclosed.py` (NUEVO) — cobertura negativa fail-closed
10 pruebas: positivo con claves válidas; negativos por ausencia de `SHIFT_ENC_KEYS`, de
`SHIFT_ENC_ACTIVE_KID`, kid activo desconocido, base64 inválido, longitud != 32 bytes, ausencia y
vacío de `SHIFT_AUDIT_HMAC_KEY`; aserción de que el mensaje de error no expone material de clave;
e **integración de `lifespan`**: construir `TestClient` sin claves → propaga `ConfigError` (la app
no arranca), con DB aislada en `tmp_path`.

## Variables de entorno (nombres canónicos)

| Variable | Propósito | Requerida en arranque |
|----------|-----------|-----------------------|
| `SHIFT_ENC_KEYS` | lista `kid:base64-32byte-key` separada por comas | Sí (validada) |
| `SHIFT_ENC_ACTIVE_KID` | kid activo para cifrar | Sí (validada) |
| `SHIFT_AUDIT_HMAC_KEY` | clave HMAC de la cadena de auditoría | Sí (validada) |
| `SHIFT_ADMIN_TOKEN` | token admin de verificación de auditoría (Tarea 15) | No en Tarea 5 |

## Cómo el arnés provee claves de prueba

Las claves se inyectan por `os.environ.setdefault` al importar `conftest.py` (antes de cualquier
arranque de app) y se reafirman por el fixture `autouse` `_ensure_test_keys`. No se tocan ni el
código de la app ni `requirements*.txt`. El fail-closed de producción permanece intacto: la app
sigue exigiendo que las claves vengan del entorno.

## Resultado real de pytest

### Suite nueva (negativa + integración)
Comando: `python -m pytest tests/test_config_failclosed.py -v`

```
collected 10 items
tests/test_config_failclosed.py::test_valida_con_claves_de_prueba_correctas PASSED [ 10%]
tests/test_config_failclosed.py::test_falla_sin_enc_keys PASSED          [ 20%]
tests/test_config_failclosed.py::test_falla_sin_active_kid PASSED        [ 30%]
tests/test_config_failclosed.py::test_falla_active_kid_desconocido PASSED [ 40%]
tests/test_config_failclosed.py::test_falla_base64_invalido PASSED       [ 50%]
tests/test_config_failclosed.py::test_falla_longitud_de_clave_incorrecta PASSED [ 60%]
tests/test_config_failclosed.py::test_falla_sin_hmac_key PASSED          [ 70%]
tests/test_config_failclosed.py::test_falla_hmac_vacio PASSED            [ 80%]
tests/test_config_failclosed.py::test_error_no_expone_material_de_clave PASSED [ 90%]
tests/test_config_failclosed.py::test_lifespan_falla_cerrado_sin_claves PASSED [100%]
======================== 10 passed, 1 warning in 0.48s ========================
```

### Suite completa (regresión heredada + nuevas)
Comando: `python -m pytest -q`

```
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
..............                                                           [100%]
230 passed, 1 warning in 14.81s
```

- **Baseline heredado previo:** 220 passed.
- **Tras Tarea 5:** 230 passed (220 heredadas + 10 nuevas). 0 fallos, 0 regresiones.
- (La única "warning" es una `DeprecationWarning` preexistente de Starlette, no relacionada.)

## Veredicto

- ✅ Con claves válidas (env de prueba): la app arranca y `pytest` queda 100% verde (230).
- ✅ Sin una clave requerida: la validación / arranque `lifespan` lanza `ConfigError` (fail-closed).
- ✅ El material de clave no aparece en logs/errores (test dedicado lo comprueba).
- ✅ Sin debilitar el fail-closed de producción; claves de prueba solo en el arnés.
