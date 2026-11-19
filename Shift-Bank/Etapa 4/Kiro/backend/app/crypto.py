"""Cifrado autenticado por campo para identificadores bancarios sensibles (Etapa 3, Tarea 6).

Implementa AEAD **AES-256-GCM** (vía `cryptography.hazmat.primitives.ciphers.aead.AESGCM`)
sobre el formato versionado del diseño §1.2:

    enc:v1:<kid>:<base64url(nonce)>:<base64url(ciphertext||tag)>

Decisiones de diseño honradas (design.md §1.1–§1.3):

- **Primitiva:** AES-256-GCM (confidencialidad + integridad autenticada). Un texto cifrado
  manipulado o una clave incorrecta fallan la verificación del tag al descifrar (R1.4, R2.5).
- **Nonce:** 96 bits aleatorios (`os.urandom(12)`) por operación de cifrado; nunca reutilizado
  con la misma clave (cada escritura genera un nonce nuevo) → dos cifrados del mismo texto
  producen tokens distintos.
- **AAD:** el prefijo `enc:v1:<kid>` se pasa como *associated data* del AES-GCM, de modo que
  alterar el `kid` del token invalida el tag (R2.4, R2.5).
- **Versionado de clave:** el `kid` queda registrado en el propio token para seleccionar la
  clave de descifrado correcta y manejar claves obsoletas de forma determinista (R2.4).
- **Fail-closed, sin texto plano:** no hay clave por defecto embebida ni respaldo en claro
  (R2.3). Claves ausentes/inválidas → `CryptoConfigError`; integridad/kid fallido →
  `DecryptionError`.
- **Higiene de secretos (R2.6, R15.2):** este módulo NUNCA registra claves ni texto plano; los
  mensajes de error no incluyen material de clave, nonce, texto cifrado crudo ni plaintext.

Las claves se proveen EXTERNAMENTE por entorno; los accesores crudos y la longitud requerida
viven en `app.config` (Tarea 5). Este módulo reutiliza esos accesores (`get_enc_keys_raw`,
`get_enc_active_kid`, `ENC_KEY_LENGTH_BYTES`, nombres `ENV_*`).
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config

# Prefijo/magic + versión de formato (design.md §1.2). Evolucionar el esquema implica una
# nueva versión (p. ej. `enc:v2:`), sin romper el descifrado de tokens `v1` existentes.
_PREFIX = "enc:v1:"

# Nonce AES-GCM: 96 bits = 12 bytes (recomendación estándar para GCM, design.md §1.1).
_NONCE_LENGTH_BYTES = 12


class CryptoConfigError(RuntimeError):
    """Configuración de claves ausente o inválida (fail-closed en carga/arranque).

    Se lanza por `load_keys()` cuando `SHIFT_ENC_KEYS`/`SHIFT_ENC_ACTIVE_KID` faltan, tienen
    formato inválido, contienen base64 inválido o una clave de longitud != 32 bytes (AES-256).
    El mensaje identifica QUÉ variable/kid falla pero NUNCA incluye material de clave (R2.6).
    """


class DecryptionError(RuntimeError):
    """Fallo de integridad o de selección de clave al descifrar (fail-closed en operación).

    Se lanza por `decrypt()` cuando el token está malformado, el `kid` es desconocido/ausente,
    o la verificación AEAD del tag falla (texto cifrado/nonce/kid manipulado). Nunca devuelve
    datos incorrectos ni opera con datos manipulados (R2.5). El mensaje no incluye texto plano
    ni material de clave (R2.6).
    """


def _b64url_encode(raw: bytes) -> str:
    """Codifica bytes a base64url sin padding (seguro para el formato de token)."""
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Decodifica base64url (tolerando padding ausente). Lanza en entrada inválida."""
    # `urlsafe_b64decode` exige padding correcto; re-añadimos el relleno que falte.
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def load_keys() -> tuple[dict[str, bytes], str]:
    """Carga y valida el material de clave de cifrado desde el entorno (fail-closed).

    Lee `SHIFT_ENC_KEYS` (lista `kid:base64-32bytes` separada por comas) y
    `SHIFT_ENC_ACTIVE_KID` usando los accesores de `config` (Tarea 5). Decodifica cada clave
    desde base64 y valida que mida exactamente `ENC_KEY_LENGTH_BYTES` (32 bytes = AES-256).

    No cachea: cada llamada vuelve a leer el entorno, de modo que las pruebas que cambian las
    variables (p. ej. con `monkeypatch`) siempre ven el estado actual sin necesidad de un
    `reset` explícito. `encrypt`/`decrypt` invocan esta función por operación.

    Returns:
        (keys, active_kid): mapa `{kid: key_bytes}` y el kid activo (presente en el mapa).

    Raises:
        CryptoConfigError: si falta configuración, el formato es inválido, el base64 no
            decodifica, una clave no mide 32 bytes, o el kid activo no está en el mapa.
    """
    raw = config.get_enc_keys_raw()
    if not raw or not raw.strip():
        raise CryptoConfigError(
            f"{config.ENV_ENC_KEYS} ausente o vacío: se requiere para cifrado en reposo"
        )

    active_kid = config.get_enc_active_kid()
    if not active_kid or not active_kid.strip():
        raise CryptoConfigError(
            f"{config.ENV_ENC_ACTIVE_KID} ausente o vacío: se requiere el kid activo"
        )
    active_kid = active_kid.strip()

    keys: dict[str, bytes] = {}
    for item in raw.split(","):
        parsed = _parse_enc_key_item(item)
        if parsed is None:
            continue
        kid, key_bytes = parsed
        keys[kid] = key_bytes

    if not keys:
        raise CryptoConfigError(f"{config.ENV_ENC_KEYS} no contiene ninguna clave válida")
    if active_kid not in keys:
        raise CryptoConfigError(
            f"{config.ENV_ENC_ACTIVE_KID} apunta a un kid ausente en {config.ENV_ENC_KEYS}"
        )

    return keys, active_kid


def _parse_enc_key_item(item: str) -> tuple[str, bytes] | None:
    """Parsea y valida una entrada `kid:base64` de `SHIFT_ENC_KEYS`.

    Devuelve `(kid, key_bytes)` para una entrada válida, o `None` si la entrada está vacía
    (debe omitirse). Lanza `CryptoConfigError` con los MISMOS mensajes que antes estaban en
    línea; nunca incluye material de clave en los mensajes (R2.6).
    """
    item = item.strip()
    if not item:
        return None
    if ":" not in item:
        raise CryptoConfigError(
            f"{config.ENV_ENC_KEYS} con formato inválido: se espera 'kid:base64' por entrada"
        )
    kid, b64 = item.split(":", 1)
    kid = kid.strip()
    b64 = b64.strip()
    if not kid or not b64:
        raise CryptoConfigError(
            f"{config.ENV_ENC_KEYS} con entrada inválida: kid o clave vacíos"
        )
    try:
        key_bytes = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        # No se incluye el valor; solo el kid y la causa genérica (R2.6).
        raise CryptoConfigError(
            f"{config.ENV_ENC_KEYS} contiene base64 inválido para kid '{kid}'"
        ) from exc
    if len(key_bytes) != config.ENC_KEY_LENGTH_BYTES:
        raise CryptoConfigError(
            f"{config.ENV_ENC_KEYS}: la clave para kid '{kid}' debe ser de "
            f"{config.ENC_KEY_LENGTH_BYTES} bytes (AES-256)"
        )
    return kid, key_bytes


def is_encrypted(value: str) -> bool:
    """True si y solo si `value` tiene el prefijo de formato cifrado (`enc:v1:`).

    Discriminador usado por la migración idempotente (Tarea 8) para distinguir un valor ya
    cifrado de uno en claro pendiente de migrar (design.md §1.2). No valida el resto del
    token; solo el prefijo de versión.
    """
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt(plaintext: str) -> str:
    """Cifra `plaintext` (str UTF-8) con la clave ACTIVA y devuelve el token versionado.

    Formato (design.md §1.2):
        enc:v1:<kid>:<base64url(nonce)>:<base64url(ciphertext||tag)>

    - Usa un nonce de 96 bits aleatorio y nuevo por llamada (`os.urandom(12)`): dos cifrados
      del mismo texto producen tokens distintos.
    - Pasa el prefijo `enc:v1:<kid>` como AAD, ligando el texto cifrado a su kid (R2.4).

    Raises:
        CryptoConfigError: si la configuración de claves es inválida/ausente (fail-closed).
    """
    keys, active_kid = load_keys()
    key = keys[active_kid]

    nonce = os.urandom(_NONCE_LENGTH_BYTES)
    aad = f"{_PREFIX}{active_kid}".encode("utf-8")
    # AESGCM.encrypt devuelve ciphertext || tag (el tag de 16 bytes va al final).
    ct_and_tag = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad)

    return f"{_PREFIX}{active_kid}:{_b64url_encode(nonce)}:{_b64url_encode(ct_and_tag)}"


def decrypt(token: str) -> str:
    """Descifra un token versionado y devuelve el texto plano original (str UTF-8).

    Parsea el formato, selecciona la clave por `<kid>`, reconstruye la AAD (`enc:v1:<kid>`) y
    verifica el tag AEAD. Rechaza de forma segura cualquier manipulación.

    Raises:
        DecryptionError: si el token está malformado, el `kid` es desconocido/ausente, o la
            verificación de integridad (tag/AAD) falla (R2.5). No hay fallback a texto plano.
        CryptoConfigError: si la configuración de claves es inválida/ausente (fail-closed).
    """
    if not isinstance(token, str) or not token.startswith(_PREFIX):
        raise DecryptionError("token con formato inválido: prefijo 'enc:v1:' ausente")

    # Cuerpo tras el prefijo: "<kid>:<b64url(nonce)>:<b64url(ct||tag)>".
    body = token[len(_PREFIX):]
    parts = body.split(":")
    if len(parts) != 3:
        raise DecryptionError("token con formato inválido: se esperan kid, nonce y ciphertext")
    kid, nonce_b64, ct_b64 = parts
    if not kid or not nonce_b64 or not ct_b64:
        raise DecryptionError("token con formato inválido: segmento vacío")

    keys, _active_kid = load_keys()
    key = keys.get(kid)
    if key is None:
        # kid obsoleto/desconocido: rechazo seguro, sin revelar el conjunto de kids (R2.5).
        raise DecryptionError("kid desconocido o ausente: no se puede descifrar el registro")

    try:
        nonce = _b64url_decode(nonce_b64)
        ct_and_tag = _b64url_decode(ct_b64)
    except (binascii.Error, ValueError) as exc:
        raise DecryptionError("token con codificación base64url inválida") from exc

    if len(nonce) != _NONCE_LENGTH_BYTES:
        raise DecryptionError("token con nonce de longitud inválida")

    aad = f"{_PREFIX}{kid}".encode("utf-8")
    try:
        plaintext = AESGCM(key).decrypt(nonce, ct_and_tag, aad)
    except InvalidTag as exc:
        # Integridad fallida: ciphertext/nonce/kid manipulado o clave incorrecta (R2.5).
        raise DecryptionError("verificación de integridad fallida: registro manipulado") from exc

    return plaintext.decode("utf-8")
