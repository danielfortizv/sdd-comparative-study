"""Locustfile de la prueba de carga de Shift Bank (Etapa 3, Tarea 19).

design.md §3.2 · requirements R9.2, R10.3 · AC-10.

Propósito
---------
Define el `HttpUser` de Locust que genera la **mezcla de carga exacta y no negociable**
contra la API bancaria, respetando TODOS los controles heredados (MFA, saldo, límites). No
elude ningún control: usa el contrato real de la API (montos decimal-string, cuerpo
`from`/`to`/`amount`/`description`).

Mezcla de tareas (pesos de Locust `@task(weight)`), R9.2 / design.md §3.2
-------------------------------------------------------------------------
- **60%** `GET /api/accounts`  — lectura de saldos de cuentas.   → `@task(6)`
- **30%** `GET /api/transfers` — lectura del historial.          → `@task(3)`
- **10%** `POST /api/transfers` — transferencia interna pequeña. → `@task(1)`

Los pesos 6/3/1 codifican la proporción 60/30/10. Locust elige la siguiente tarea de forma
aleatoria ponderada por estos pesos; la **distribución real medida** (no estos pesos
nominales) la reporta el runner (Tarea 21, R9.4) a partir de las estadísticas por ruta.

Transferencia interna (R10.3 — NO eludir controles)
----------------------------------------------------
- **Monto pequeño** muy por debajo del umbral MFA (1.000.000 COP): se usa `50000.00` COP, de
  modo que la transferencia se complete DIRECTAMENTE sin MFA. También queda muy por debajo de
  los límites amplios sembrados por `isolation.py` (Tarea 18), así que no se disparan rechazos
  de límite por diseño.
- **Dirección alternada** checking↔savings en cada petición, para no drenar una sola cuenta a
  lo largo de los 60 s de carga y mantener fondos suficientes en ambos lados.
- **Monto decimal-string válido** (`"50000.00"`), respetando el modelo de dinero heredado.
- El cuerpo respeta el contrato real: `{"from", "to", "amount", "description"}`. El endpoint
  devuelve **201** en la creación (con y sin MFA); como el monto está bajo el umbral, la
  transferencia se COMPLETA sin requerir MFA.

Clasificación de respuestas (design.md §3.3)
--------------------------------------------
Se usa `catch_response=True` para distinguir, en las estadísticas de Locust:
- **201** → éxito (transferencia creada/completada).
- **4xx bien formado** (rechazo de dominio con cuerpo `{"error": {...}}`) → **rechazo de
  negocio esperado**: se marca como *failure* con una etiqueta `BusinessRejection:<code>` para
  contabilizarlo APARTE de los errores de transporte, sin confundirlo con un fallo inesperado.
  (Con el aislamiento/siembra de la Tarea 18 no deberían ocurrir, pero se clasifican por
  robustez y para alimentar el reporte de la Tarea 21.)
- **5xx** o **error de conexión/transporte** → **error inesperado** (fallo real del sistema),
  marcado como *failure* con etiqueta `UnexpectedError:<...>`.
Las lecturas (`GET`) tratan **cualquier** código != 2xx como error inesperado: no existen
rechazos de negocio esperados en esos endpoints de solo lectura.

Importabilidad (Tarea 19, criterio de aceptación)
--------------------------------------------------
Este módulo se importa limpiamente sin arrancar Locust ni requerir que la app esté corriendo:
`python -c "import loadtest.locustfile"`. El host/base URL lo inyecta el runner (Tarea 20) vía
`--host`/entorno; las rutas aquí son **relativas** (`/api/...`), de modo que la clase de
usuario es agnóstica del host.
"""

from __future__ import annotations

from locust import HttpUser, between, task

# --- Parámetros de la transferencia de carga (documentados, R10.3) -----------
#
# Monto decimal-string pequeño: 50.000,00 COP. Muy por debajo del umbral MFA (1.000.000 COP)
# para completarse sin MFA, y muy por debajo de los límites amplios sembrados (Tarea 18) para
# no disparar rechazos de límite.
TRANSFER_AMOUNT = "50000.00"
TRANSFER_DESCRIPTION = "loadtest internal transfer"

# Las dos cuentas internas heredadas. La dirección se alterna en cada POST para no drenar una.
_CHECKING = "checking"
_SAVINGS = "savings"

# Rutas RELATIVAS (host-agnósticas): el host lo fija el runner vía --host/entorno (Tarea 20).
ACCOUNTS_PATH = "/api/accounts"
TRANSFERS_PATH = "/api/transfers"


class ShiftBankUser(HttpUser):
    """Usuario virtual con la mezcla 60/30/10 y controles bancarios preservados.

    `wait_time` modela una pequeña pausa entre peticiones (0.1–0.5 s) para un patrón de carga
    realista; no afecta a la proporción de la mezcla, que la rigen los pesos `@task`.
    """

    # Pausa breve y acotada entre tareas; terminable y determinista en rango.
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        """Estado por usuario: alternancia de dirección checking<->savings."""
        # Empieza en checking->savings; se invierte en cada POST de transferencia.
        self._next_from = _CHECKING
        self._next_to = _SAVINGS

    # --- 60%: lectura de saldos de cuentas -----------------------------------
    @task(6)
    def get_accounts(self) -> None:
        """GET /api/accounts — 60% de la mezcla. Solo lectura: !2xx = error inesperado."""
        with self.client.get(
            ACCOUNTS_PATH, name="GET /api/accounts", catch_response=True
        ) as response:
            self._classify_read(response)

    # --- 30%: lectura del historial de transferencias ------------------------
    @task(3)
    def get_transfers(self) -> None:
        """GET /api/transfers — 30% de la mezcla. Solo lectura: !2xx = error inesperado."""
        with self.client.get(
            TRANSFERS_PATH, name="GET /api/transfers", catch_response=True
        ) as response:
            self._classify_read(response)

    # --- 10%: transferencia interna pequeña y válida -------------------------
    @task(1)
    def post_transfer(self) -> None:
        """POST /api/transfers — 10% de la mezcla.

        Monto pequeño bajo el umbral MFA y bajo los límites amplios sembrados, dirección
        alternada. Respeta el contrato real: no elude MFA/saldo/límites (R10.3).
        """
        from_kind, to_kind = self._next_from, self._next_to
        # Alterna la dirección para la próxima transferencia (no drenar una cuenta).
        self._next_from, self._next_to = to_kind, from_kind

        payload = {
            "from": from_kind,
            "to": to_kind,
            "amount": TRANSFER_AMOUNT,
            "description": TRANSFER_DESCRIPTION,
        }
        with self.client.post(
            TRANSFERS_PATH,
            json=payload,
            name="POST /api/transfers",
            catch_response=True,
        ) as response:
            self._classify_transfer(response)

    # --- Clasificación de respuestas (design.md §3.3) ------------------------
    @staticmethod
    def _classify_read(response) -> None:
        """Clasifica una respuesta de solo lectura (GET).

        No hay rechazos de negocio esperados en lecturas: cualquier código != 2xx (incluidos
        errores de transporte, donde `status_code` es 0) es un **error inesperado**.
        """
        status = response.status_code
        if status == 0:
            response.failure("UnexpectedError:transport")
            return
        if 200 <= status < 300:
            response.success()
            return
        response.failure(f"UnexpectedError:HTTP {status}")

    @staticmethod
    def _classify_transfer(response) -> None:
        """Clasifica una respuesta de POST /api/transfers (design.md §3.3).

        - 201               → éxito.
        - 4xx bien formado  → rechazo de negocio ESPERADO (contado aparte, no transporte).
        - 5xx / transporte  → error INESPERADO (fallo real).
        """
        status = response.status_code

        # Error de transporte/conexión: Locust reporta status_code == 0.
        if status == 0:
            response.failure("UnexpectedError:transport")
            return

        # Éxito del contrato: la creación devuelve 201 (con y sin MFA).
        if status == 201:
            response.success()
            return

        # 5xx: error inesperado del servidor.
        if 500 <= status < 600:
            response.failure(f"UnexpectedError:HTTP {status}")
            return

        # 4xx: rechazo de negocio esperado si el cuerpo es un error de dominio bien formado.
        if 400 <= status < 500:
            code = _domain_error_code(response)
            if code is not None:
                # Marcado como failure pero con etiqueta distinguible → se cuenta APARTE de
                # los errores de transporte/5xx en el reporte (Tarea 21).
                response.failure(f"BusinessRejection:{code}")
            else:
                # 4xx sin cuerpo de dominio reconocible: tratarlo como inesperado.
                response.failure(f"UnexpectedError:HTTP {status}")
            return

        # Cualquier otro código (1xx/3xx inesperado): inesperado.
        response.failure(f"UnexpectedError:HTTP {status}")


def _domain_error_code(response) -> str | None:
    """Extrae `error.code` de un cuerpo de error de dominio bien formado, o None.

    El contrato heredado de rechazos es `{"error": {"code": ..., "message": ...}}`
    (ver `routers/transfers.py`). Devuelve el código si está presente; None si el cuerpo no
    tiene esa forma (no es un rechazo de negocio reconocible).
    """
    try:
        body = response.json()
    except (ValueError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        return error["code"]
    return None


# --- Afirmación interna de pesos (criterio de aceptación de la Tarea 19) ------
#
# Permite un sanity check de la mezcla 60/30/10 sin arrancar Locust ni la app:
#   python -c "import loadtest.locustfile as m; m.assert_task_weights()"
# Locust registra los pesos en `HttpUser.tasks` repitiendo cada callable `weight` veces.
def task_weight_map() -> dict[str, int]:
    """Devuelve el mapa {nombre_de_tarea: peso} declarado por `ShiftBankUser`.

    Locust expande `tasks` a una lista donde cada tarea aparece `weight` veces; se cuenta la
    multiplicidad por nombre de función para recuperar el peso efectivo.
    """
    counts: dict[str, int] = {}
    for t in ShiftBankUser.tasks:
        name = getattr(t, "__name__", repr(t))
        counts[name] = counts.get(name, 0) + 1
    return counts


def assert_task_weights() -> dict[str, int]:
    """Verifica que la mezcla declarada es exactamente 6/3/1 (== 60/30/10). Devuelve el mapa."""
    weights = task_weight_map()
    expected = {"get_accounts": 6, "get_transfers": 3, "post_transfer": 1}
    assert weights == expected, f"Pesos de tareas inesperados: {weights} (esperado {expected})"
    return weights


if __name__ == "__main__":
    # Sanity check ejecutable sin Locust ni app en marcha.
    print("ShiftBankUser task weights:", assert_task_weights())
    print("Mix: 60% GET /api/accounts, 30% GET /api/transfers, 10% POST /api/transfers")
    print("OK: locustfile importable y pesos 6/3/1 (60/30/10) correctos.")
