"""Pruebas de `app.crypto` — AEAD AES-256-GCM con formato versionado (Etapa 3, Tarea 6).

Cobertura (design.md §1.1–§1.3; R1.4, R2.3, R2.4, R2.5, R18.2):
- round-trip encrypt/decrypt (unidad + propiedad sobre muchos textos);
- forma del token `enc:v1:<kid>:<nonce>:<ct||tag>`;
- unicidad de nonce: dos cifrados del mismo texto → tokens distintos;
- ciphertext manipulado → `DecryptionError`;
- kid alterado en el token → `DecryptionError` (AAD liga el kid al tag);
- kid desconocido/ausente → `DecryptionError`;
- clave ausente/inválida → `CryptoConfigError`;
- `is_encrypted` casos True/False;
- ausencia de fallback a texto plano (un valor cifrado nunca es su propio plaintext).

El arnés (`conftest.py`) ya fija claves de PRUEBA deterministas en el entorno
(`SHIFT_ENC_KEYS=test:...`, `SHIFT_ENC_ACTIVE_KID=test`). Los casos que necesitan un entorno
distinto lo ajustan con `monkeypatch` (los accesores de `config` leen `os.environ` en vivo, así
que no hace falta ningún `reset` explícito del módulo).
"""

import base64
import random

import pytest

import app.crypto as crypto

# Material de clave de PRUEBAS (coincide con `conftest`/`test_config_failclosed`).
_KID = "test"
_KEY_B64 = "c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ="  # 32 bytes AES-256
_ENC_KEYS = f"{_KID}:{_KEY_B64}"

# Segunda clave válida (32 bytes) para escenarios multi-kid / rotación.
_KID2 = "k2"
_KEY2_B64 = base64.b64encode(b"another-32-byte-stage3-test-key!").decode()  # 32 bytes
_MULTI_ENC_KEYS = f"{_ENC_KEYS},{_KID2}:{_KEY2_B64}"


def _set_keys(monkeypatch, *, enc_keys=_ENC_KEYS, active_kid=_KID):
    """Fija (o borra, con None) las variables de entorno de claves de cifrado."""
    if enc_keys is None:
        monkeypatch.delenv(crypto.config.ENV_ENC_KEYS, raising=False)
    else:
        monkeypatch.setenv(crypto.config.ENV_ENC_KEYS, enc_keys)
    if active_kid is None:
        monkeypatch.delenv(crypto.config.ENV_ENC_ACTIVE_KID, raising=False)
    else:
        monkeypatch.setenv(crypto.config.ENV_ENC_ACTIVE_KID, active_kid)


# --- load_keys ---------------------------------------------------------------


def test_load_keys_devuelve_mapa_y_kid_activo(monkeypatch):
    _set_keys(monkeypatch)
    keys, active_kid = crypto.load_keys()
    assert active_kid == _KID
    assert set(keys) == {_KID}
    assert len(keys[_KID]) == crypto.config.ENC_KEY_LENGTH_BYTES  # 32 bytes


def test_load_keys_sin_enc_keys_lanza_cryptoconfigerror(monkeypatch):
    _set_keys(monkeypatch, enc_keys=None)
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_load_keys_sin_active_kid_lanza_cryptoconfigerror(monkeypatch):
    _set_keys(monkeypatch, active_kid=None)
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_load_keys_active_kid_desconocido_lanza(monkeypatch):
    _set_keys(monkeypatch, active_kid="inexistente")
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_load_keys_base64_invalido_lanza(monkeypatch):
    _set_keys(monkeypatch, enc_keys=f"{_KID}:no-base64-!!!")
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_load_keys_longitud_incorrecta_lanza(monkeypatch):
    short = base64.b64encode(b"too-short").decode()  # 9 bytes != 32
    _set_keys(monkeypatch, enc_keys=f"{_KID}:{short}")
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_load_keys_formato_sin_dos_puntos_lanza(monkeypatch):
    _set_keys(monkeypatch, enc_keys="sin-separador")
    with pytest.raises(crypto.CryptoConfigError):
        crypto.load_keys()


def test_error_de_config_no_expone_material_de_clave(monkeypatch):
    """El mensaje de `CryptoConfigError` nunca incluye material de clave (R2.6)."""
    marker = "SUPERSECRETKEYMATERIAL"
    _set_keys(monkeypatch, enc_keys=f"{_KID}:{marker}!!!")
    with pytest.raises(crypto.CryptoConfigError) as excinfo:
        crypto.load_keys()
    assert marker not in str(excinfo.value)


# --- encrypt / decrypt round-trip -------------------------------------------


def test_round_trip_basico(monkeypatch):
    _set_keys(monkeypatch)
    plaintext = "1234567890"
    token = crypto.encrypt(plaintext)
    assert crypto.decrypt(token) == plaintext


def test_round_trip_unicode_y_vacio(monkeypatch):
    _set_keys(monkeypatch)
    for plaintext in ("", "cuenta: 00-11-22", "ñáé 💸 routing", "x" * 1024):
        token = crypto.encrypt(plaintext)
        assert crypto.decrypt(token) == plaintext


def test_propiedad_round_trip_muchos_textos(monkeypatch):
    """Validates: Requirements 1.4 — descifrar lo cifrado recupera el texto original.

    Prueba basada en propiedad (sin dependencias externas): genera muchos textos aleatorios
    —incluyendo vacíos, ASCII, Unicode fuera del BMP y cadenas largas— y verifica el
    invariante `decrypt(encrypt(x)) == x` para todos ellos.
    """
    _set_keys(monkeypatch)
    rng = random.Random(0xE3_06)  # semilla fija → reproducible

    # Casos límite explícitos.
    casos = ["", " ", "\n\t", "0", "9" * 1, "ñ", "💸", ":", "enc:v1:falso"]
    # Muestras aleatorias de longitud y alfabeto variables (ASCII + Unicode amplio).
    for _ in range(200):
        length = rng.randint(0, 256)
        chars = [chr(rng.randint(0x20, 0x10FFFF)) for _ in range(length)]
        # Evitar surrogates aislados (no codificables en UTF-8).
        casos.append("".join(c for c in chars if not 0xD800 <= ord(c) <= 0xDFFF))

    for plaintext in casos:
        token = crypto.encrypt(plaintext)
        assert crypto.decrypt(token) == plaintext


# --- forma del token ---------------------------------------------------------


def test_forma_del_token(monkeypatch):
    """El token tiene forma `enc:v1:<kid>:<nonce>:<ct||tag>` (design.md §1.2)."""
    _set_keys(monkeypatch)
    token = crypto.encrypt("algo")
    assert token.startswith("enc:v1:")
    # 5 segmentos separados por ':' => ['enc', 'v1', '<kid>', '<nonce>', '<ct||tag>'].
    segments = token.split(":")
    assert len(segments) == 5
    assert segments[0] == "enc"
    assert segments[1] == "v1"
    assert segments[2] == _KID
    assert segments[3] and segments[4]  # nonce y ciphertext no vacíos


# --- unicidad de nonce -------------------------------------------------------


def test_nonce_unico_entre_dos_cifrados(monkeypatch):
    """Dos cifrados del mismo texto producen tokens distintos (nonce aleatorio)."""
    _set_keys(monkeypatch)
    plaintext = "mismo-texto"
    t1 = crypto.encrypt(plaintext)
    t2 = crypto.encrypt(plaintext)
    assert t1 != t2
    # Mismo kid, pero el segmento del nonce difiere.
    assert t1.split(":")[3] != t2.split(":")[3]
    # Y ambos descifran al mismo plaintext.
    assert crypto.decrypt(t1) == plaintext
    assert crypto.decrypt(t2) == plaintext


# --- integridad: ciphertext manipulado --------------------------------------


def test_ciphertext_manipulado_lanza_decryptionerror(monkeypatch):
    _set_keys(monkeypatch)
    token = crypto.encrypt("sensible")
    segments = token.split(":")
    # Alterar el último carácter del segmento ciphertext||tag.
    ct = segments[4]
    flipped = ct[:-1] + ("A" if ct[-1] != "A" else "B")
    tampered = ":".join(segments[:4] + [flipped])
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(tampered)


# --- integridad: kid alterado (AAD) -----------------------------------------


def test_kid_alterado_en_token_lanza_decryptionerror(monkeypatch):
    """Cambiar el kid por otro kid válido rompe el tag porque el kid va en la AAD (R2.4)."""
    _set_keys(monkeypatch, enc_keys=_MULTI_ENC_KEYS, active_kid=_KID)
    token = crypto.encrypt("sensible")  # cifrado con kid activo `_KID`
    segments = token.split(":")
    assert segments[2] == _KID
    # Reescribir el kid a `_KID2` (clave existente) sin recifrar → AAD distinta → tag inválido.
    segments[2] = _KID2
    tampered = ":".join(segments)
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(tampered)


# --- kid desconocido / ausente ----------------------------------------------


def test_kid_desconocido_lanza_decryptionerror(monkeypatch):
    """Un token cuyo kid no está en el conjunto de claves → DecryptionError (R2.5)."""
    _set_keys(monkeypatch, enc_keys=_MULTI_ENC_KEYS, active_kid=_KID)
    token = crypto.encrypt("sensible")
    # Ahora el entorno solo conoce `_KID`; forjamos un token con un kid inexistente.
    segments = token.split(":")
    segments[2] = "kid-fantasma"
    forged = ":".join(segments)
    _set_keys(monkeypatch, enc_keys=_ENC_KEYS, active_kid=_KID)
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(forged)


def test_token_malformado_lanza_decryptionerror(monkeypatch):
    _set_keys(monkeypatch)
    for bad in (
        "no-es-token",
        "enc:v1:",
        "enc:v1:test",
        "enc:v1:test:soloNonce",
        "enc:v1:test::",
        "enc:v2:test:AAAA:BBBB",  # versión no soportada → sin prefijo enc:v1:
    ):
        with pytest.raises(crypto.DecryptionError):
            crypto.decrypt(bad)


# --- descifrado con clave incorrecta ----------------------------------------


def test_clave_incorrecta_no_descifra(monkeypatch):
    """Un token cifrado con una clave y descifrado con otra (mismo kid) → DecryptionError."""
    _set_keys(monkeypatch, enc_keys=_ENC_KEYS, active_kid=_KID)
    token = crypto.encrypt("sensible")
    # Reemplazar la clave del kid `test` por otra de 32 bytes distinta, mismo kid.
    otra = base64.b64encode(b"DISTINTA-clave-de-32-bytes-aes!!").decode()
    _set_keys(monkeypatch, enc_keys=f"{_KID}:{otra}", active_kid=_KID)
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(token)


# --- is_encrypted ------------------------------------------------------------


def test_is_encrypted_true(monkeypatch):
    _set_keys(monkeypatch)
    token = crypto.encrypt("algo")
    assert crypto.is_encrypted(token) is True
    assert crypto.is_encrypted("enc:v1:test:AAAA:BBBB") is True


def test_is_encrypted_false():
    for value in ("", "1234567890", "enc:", "enc:v2:...", "plaintext", "env:v1:x"):
        assert crypto.is_encrypted(value) is False


# --- sin fallback a texto plano ---------------------------------------------


def test_sin_fallback_texto_plano(monkeypatch):
    """El token cifrado nunca contiene el plaintext ni es igual a él (R2.3)."""
    _set_keys(monkeypatch)
    plaintext = "0001112223334445"
    token = crypto.encrypt(plaintext)
    assert token != plaintext
    assert plaintext not in token
    # Descifrar un valor en claro (no token) no "cae" a devolver el claro: falla cerrado.
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(plaintext)
