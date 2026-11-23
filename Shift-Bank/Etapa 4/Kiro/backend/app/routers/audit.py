"""Router de verificación de auditoría protegida (Etapa 3, Tarea 15).

Expone la verificación de integridad de la cadena de auditoría (`audit.verify_chain`) como una
operación **administrativa protegida**, NO como un endpoint público anónimo (design.md §2.5/§2.6,
R8.1/R8.2). Dado el modelo de cliente mock heredado (sin login real), el acceso se simula con un
**token administrativo** provisto por entorno (`SHIFT_ADMIN_TOKEN`), exigido por la cabecera
`X-Admin-Token`.

Decisiones honradas (design.md §2.6; R8.1, R8.2):

- **Gate por cabecera + comparación en tiempo constante.** El endpoint lee la cabecera
  `X-Admin-Token` y la compara con `SHIFT_ADMIN_TOKEN` (config, Tarea 5) usando
  `hmac.compare_digest`, evitando fugas por canal lateral de temporización. Si la cabecera falta
  o no coincide → **401 Unauthorized**. Se elige 401 (sobre 404) por claridad del contrato: el
  endpoint existe pero requiere credencial administrativa. No se filtra ningún resultado de
  verificación en las respuestas denegadas.

- **Fail-closed si el token no está configurado (R8.2).** Si `SHIFT_ADMIN_TOKEN` está ausente o
  vacío en el entorno, el endpoint DENIEGA el acceso (no "allow-all"): sin token administrativo
  configurado no hay forma de autenticarse, de modo que la verificación nunca queda expuesta
  anónimamente. La comparación se hace igualmente en tiempo constante contra una cadena vacía
  para no abrir un camino de retorno temprano distinto entre "no configurado" y "token erróneo".

- **Superficie mínima y no sensible.** La única respuesta autorizada es el veredicto de
  `verify_chain`: `{"ok": true}` en una cadena íntegra, o `{"ok": false, "failed_seq": N,
  "reason": "..."}` en caso de fallo. `failed_seq`/`reason` son metadatos NO sensibles (un `seq`
  y una descripción legible); NUNCA se exponen payloads de auditoría ni material de clave. Las
  lecturas del contenido de la bitácora más allá de `verify` quedan fuera de alcance.

- **Invocable fuera de HTTP.** La rutina `audit.verify_chain(conn)` sigue siendo llamable en
  proceso (pruebas, CLI, runner de carga) sin pasar por este gate; este router es la ÚNICA nueva
  superficie pública y está protegida.

_Requisitos: R8.1, R8.2_ · _Diseño: §2.5, §2.6_
"""

import hmac

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from .. import audit, config
from ..db import get_connection

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _is_authorized(provided: str | None) -> bool:
    """Decide si `provided` (cabecera `X-Admin-Token`) autoriza el acceso administrativo.

    Fail-closed (R8.2): si `SHIFT_ADMIN_TOKEN` no está configurado (ausente/ vacío) → denegar.
    Si falta la cabecera → denegar. La comparación válida usa `hmac.compare_digest` (tiempo
    constante). En los caminos de denegación también se ejecuta una comparación de longitud
    estable para no introducir una diferencia de temporización trivial entre "no configurado"/
    "sin cabecera" y "token erróneo"; el resultado se descarta y se devuelve False.
    """
    expected = config.get_admin_token()
    if not expected or not expected.strip():
        # Token no configurado → fail-closed. Comparación señuelo para estabilidad temporal.
        hmac.compare_digest(provided or "", provided or "")
        return False
    if provided is None:
        hmac.compare_digest(expected, expected)
        return False
    return hmac.compare_digest(provided, expected)


def _unauthorized() -> JSONResponse:
    """Respuesta de denegación 401 sin filtrar ningún resultado de verificación."""
    return JSONResponse(
        status_code=401,
        content={"error": {"code": "UNAUTHORIZED",
                           "message": "Credencial administrativa requerida"}},
    )


def _verify(conn) -> JSONResponse:
    result = audit.verify_chain(conn)
    body: dict[str, object] = {"ok": result.ok}
    if not result.ok:
        body["failed_seq"] = result.failed_seq
        body["reason"] = result.reason
    return JSONResponse(status_code=200, content=body)


@router.get("/verify")
def verify_get(
    x_admin_token: str | None = Header(default=None),
    conn=Depends(_conn),
) -> JSONResponse:
    """Verifica la integridad de la cadena de auditoría (operación administrativa protegida).

    Requiere la cabecera `X-Admin-Token` con el valor de `SHIFT_ADMIN_TOKEN`. Sin token válido
    → 401. Con token válido → 200 con el veredicto de `audit.verify_chain`.
    """
    if not _is_authorized(x_admin_token):
        return _unauthorized()
    return _verify(conn)


@router.post("/verify")
def verify_post(
    x_admin_token: str | None = Header(default=None),
    conn=Depends(_conn),
) -> JSONResponse:
    """Variante POST de `/api/audit/verify` con el mismo gate y veredicto que la GET."""
    if not _is_authorized(x_admin_token):
        return _unauthorized()
    return _verify(conn)
