"""Constantes de configuración de Shift Bank (Etapa 1).

Centraliza los valores de negocio y de infraestructura usados por el backend:
ruta de la base de datos, umbral de MFA, código MFA fijo y TTL de la ventana de MFA.
Todos los valores reflejan el diseño y los requisitos aprobados; no se añaden ajustes
fuera del alcance de la Etapa 1.
"""

import base64
import binascii
import os
from decimal import Decimal
from pathlib import Path

# Ruta del archivo SQLite. Se ubica junto al paquete backend.
DB_PATH: Path = Path(__file__).resolve().parent.parent / "shift_bank.db"

# Umbral de MFA heredado (Etapa 1–3, COP). Preservado como referencia histórica; la Etapa 4
# usa el umbral en equivalente USD (ver MFA_THRESHOLD_USD) sobre el modelo multidivisa.
MFA_THRESHOLD: Decimal = Decimal("1000000")

# --- Etapa 4: multidivisa y FX (D-01, D-03, D-07) ----------------------------
#
# Monedas soportadas (ISO-4217), todas con 2 decimales (D-01). No se mezclan saldos de monedas
# distintas (D-01). El conjunto es cerrado; una moneda fuera de él se rechaza como error de
# dominio controlado.
SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP")

# Tasas de cambio racionales FIJAS, expresadas como unidades de la moneda POR 1 USD
# (D-03: tasas racionales exactas, sin servicio externo en vivo, sin floats). Se guardan como
# cadenas y se elevan a `fractions.Fraction` en `fx.py` para aritmética exacta. Son valores de
# simulación determinista; viven versionados en el repo (no hay API FX externa, SEED-4).
# Matriz oficial de la guía Etapa 4 (racionales exactos):
#   USD/EUR = 9/10, USD/GBP = 8/10, EUR/USD = 10/9, GBP/USD = 10/8,
#   EUR/GBP = 8/9, GBP/EUR = 9/8.
# Expresadas aquí como "unidades de la moneda por 1 USD": EUR = 9/10, GBP = 8/10. Las cruzadas
# EUR<->GBP derivan exactamente de estas (EUR/GBP = (8/10)/(9/10) = 8/9; GBP/EUR = 9/8).
FX_RATES_PER_USD: dict[str, str] = {
    "USD": "1",
    "EUR": "9/10",   # USD/EUR = 9/10 (0.90 EUR por USD)
    "GBP": "8/10",   # USD/GBP = 8/10 (0.80 GBP por USD)
}

# Límites dinámicos de la Etapa 4 en equivalente USD (D-07). Por operación USD 5,000.00; diario
# acumulado USD 10,000.00 (día UTC). En unidades menores (centavos USD).
LIMIT_PER_OP_USD_MINOR: int = 5_000_00
LIMIT_DAILY_USD_MINOR: int = 10_000_00

# Umbral de MFA en equivalente USD (D-07): MFA requerida cuando el equivalente USD SIN redondear
# es ESTRICTAMENTE mayor que USD 1,000.00.
MFA_THRESHOLD_USD: Decimal = Decimal("1000.00")

# Código MFA simulado fijo (Requisito 7.1).
MFA_CODE: str = "123456"

# Ventana de validez de una transferencia PENDING_MFA, en segundos (5 minutos, Requisito 8.1).
MFA_TTL_SECONDS: int = 5 * 60

# Nombres amigables por tipo de cuenta (Requisito 2.1).
ACCOUNT_DISPLAY_NAMES: dict[str, str] = {
    "checking": "Checking",
    "savings": "Savings",
}

# --- Etapa 2 ------------------------------------------------------------------

# Límites dinámicos por defecto en centavos (decisión E2-KIRO-D01).
# Por transferencia: 5.000.000,00 COP = 500.000.000 centavos.
# Diario acumulado: 10.000.000,00 COP = 1.000.000.000 centavos.
DEFAULT_PER_TRANSFER_LIMIT_CENTS: int = 500_000_000
DEFAULT_DAILY_LIMIT_CENTS: int = 1_000_000_000

# Intervalos de recurrencia en días (REC-02, Req. 8.2): diaria=1, semanal=7, mensual=30.
# "mensual" = 30 días fijos (no un mes calendario), por decisión de diseño.
RECURRENCE_INTERVAL_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}

# Intervalo de "despertar" del scheduler de fondo, en segundos (DD-2/DD-3, Req. 10.1/10.2,
# Tarea 32). Cada tick la única tarea asyncio invoca `recurring_service.process_due(now)` y el
# barrido de settlement ACH. Es solo la cadencia del disparador; la elegibilidad real de cada
# ocurrencia/liquidación la decide `now` (reloj inyectable), no este valor.
SCHEDULER_TICK_SECONDS: int = 1

# --- Etapa 3: claves externas (D-E3-01/02, R2.1, R2.6, R15.3) ----------------
#
# Diseño §1.4: las claves de cifrado y auditoría se proveen EXTERNAMENTE por
# variables de entorno. No hay valores por defecto inseguros ni material de clave
# embebido en el código ni en imágenes (R2.1). Este módulo solo expone accesores
# a los valores crudos del entorno; la validación (presencia/formato) vive en el
# helper `validate_startup_config` que `main.py` invoca en `lifespan` (fail-closed,
# R2.2/R15.3). El material de clave NUNCA se registra en logs ni mensajes de error
# (R2.6): los errores de validación describen QUÉ variable falla, nunca su valor.

# Nombres canónicos de las variables de entorno (diseño §1.4, §2.3, §2.6).
ENV_ENC_KEYS: str = "SHIFT_ENC_KEYS"              # lista "kid:base64-32bytes" separada por comas
ENV_ENC_ACTIVE_KID: str = "SHIFT_ENC_ACTIVE_KID"  # kid activo para cifrar
ENV_AUDIT_HMAC_KEY: str = "SHIFT_AUDIT_HMAC_KEY"  # clave HMAC de la cadena de auditoría
ENV_ADMIN_TOKEN: str = "SHIFT_ADMIN_TOKEN"        # token admin para verificación de auditoría

# Longitud requerida de la clave de cifrado AES-256 (32 bytes = 256 bits).
ENC_KEY_LENGTH_BYTES: int = 32


class ConfigError(RuntimeError):
    """Error de configuración de arranque (fail-closed).

    Se lanza cuando una clave/token requerido está ausente o es inválido. El mensaje
    identifica la variable de entorno afectada pero NUNCA incluye material de clave
    (R2.6, R15.2). La Tarea 6 profundiza la validación criptográfica en `crypto.py`
    (`CryptoConfigError`); aquí mantenemos una validación mínima de arranque.
    """


def get_enc_keys_raw() -> str | None:
    """Devuelve el valor crudo de `SHIFT_ENC_KEYS` del entorno (o None si no existe)."""
    return os.environ.get(ENV_ENC_KEYS)


def get_enc_active_kid() -> str | None:
    """Devuelve el `kid` activo de cifrado del entorno (o None si no existe)."""
    return os.environ.get(ENV_ENC_ACTIVE_KID)


def get_audit_hmac_key_raw() -> str | None:
    """Devuelve el valor crudo de la clave HMAC de auditoría (o None si no existe)."""
    return os.environ.get(ENV_AUDIT_HMAC_KEY)


def get_admin_token() -> str | None:
    """Devuelve el token administrativo del entorno (o None si no existe)."""
    return os.environ.get(ENV_ADMIN_TOKEN)


def _validate_enc_keys() -> None:
    """Valida presencia + saneamiento base64/longitud de la clave de cifrado activa.

    Validación MÍNIMA de arranque (la Tarea 6 la profundiza en `crypto.load_keys`):
    - `SHIFT_ENC_KEYS` presente y no vacío, con al menos una entrada `kid:base64`.
    - `SHIFT_ENC_ACTIVE_KID` presente y no vacío.
    - El `kid` activo existe en el mapa y su clave decodifica base64 a 32 bytes.

    Nunca incluye material de clave en los mensajes de error (R2.6).
    """
    raw = get_enc_keys_raw()
    if not raw or not raw.strip():
        raise ConfigError(f"{ENV_ENC_KEYS} ausente o vacío: se requiere para cifrado en reposo")

    active_kid = get_enc_active_kid()
    if not active_kid or not active_kid.strip():
        raise ConfigError(f"{ENV_ENC_ACTIVE_KID} ausente o vacío: se requiere el kid activo")
    active_kid = active_kid.strip()

    keys: dict[str, int] = {}
    for item in raw.split(","):
        parsed = _parse_enc_key_item(item)
        if parsed is None:
            continue
        kid, key_len = parsed
        keys[kid] = key_len

    if not keys:
        raise ConfigError(f"{ENV_ENC_KEYS} no contiene ninguna clave válida")
    if active_kid not in keys:
        raise ConfigError(
            f"{ENV_ENC_ACTIVE_KID} apunta a un kid ausente en {ENV_ENC_KEYS}"
        )


def _parse_enc_key_item(item: str) -> tuple[str, int] | None:
    """Parsea y valida una entrada `kid:base64` de `SHIFT_ENC_KEYS`.

    Devuelve `(kid, longitud_en_bytes)` para una entrada válida, o `None` si la entrada
    está vacía (debe omitirse). Lanza `ConfigError` con los MISMOS mensajes que antes
    estaban en línea; nunca incluye material de clave (R2.6).
    """
    item = item.strip()
    if not item:
        return None
    if ":" not in item:
        raise ConfigError(
            f"{ENV_ENC_KEYS} con formato inválido: se espera 'kid:base64' por entrada"
        )
    kid, b64 = item.split(":", 1)
    kid = kid.strip()
    b64 = b64.strip()
    if not kid or not b64:
        raise ConfigError(
            f"{ENV_ENC_KEYS} con entrada inválida: kid o clave vacíos"
        )
    try:
        key_bytes = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        # No se incluye el valor; solo el kid y la causa genérica.
        raise ConfigError(
            f"{ENV_ENC_KEYS} contiene base64 inválido para kid '{kid}'"
        ) from exc
    if len(key_bytes) != ENC_KEY_LENGTH_BYTES:
        raise ConfigError(
            f"{ENV_ENC_KEYS}: la clave para kid '{kid}' debe ser de "
            f"{ENC_KEY_LENGTH_BYTES} bytes (AES-256)"
        )
    return kid, len(key_bytes)


def _validate_audit_hmac_key() -> None:
    """Valida que la clave HMAC de auditoría esté presente y no vacía (R6.3, R2.2)."""
    raw = get_audit_hmac_key_raw()
    if not raw or not raw.strip():
        raise ConfigError(
            f"{ENV_AUDIT_HMAC_KEY} ausente o vacío: se requiere para la cadena de auditoría"
        )


def validate_startup_config() -> None:
    """Valida la configuración de claves requerida en el arranque (fail-closed).

    Invocada por `main.py` dentro de `lifespan` ANTES de servir tráfico. Si alguna
    clave requerida está ausente o es inválida, lanza `ConfigError` para abortar el
    arranque (R2.2, R12.2, R15.3; diseño §1.4). No valida `SHIFT_ADMIN_TOKEN` aquí:
    su ausencia se trata en el borde del endpoint de verificación (Tarea 15).

    Validación mínima intencional para la Tarea 5 (presencia + saneamiento base64/
    longitud de la clave de cifrado; no-vacío del HMAC). La Tarea 6 profundiza la
    validación criptográfica en `crypto.py`.
    """
    _validate_enc_keys()
    _validate_audit_hmac_key()
