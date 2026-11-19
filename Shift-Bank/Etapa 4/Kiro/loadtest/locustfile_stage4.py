"""Locustfile de carga multidivisa de la Etapa 4 (Tarea 24; D-03/D-07/D-13).

Mezcla análoga al perfil heredado (60% lectura de saldos / 30% lectura de historial / 10%
operaciones de cambio de estado), adaptada al contrato multidivisa de la Etapa 4:

- 60% `GET /api/v2/accounts`  (lectura de saldos por moneda)      → @task(6)
- 30% `GET /api/transfers`    (lectura de historial)              → @task(3)
- 10% operaciones:            → @task(1)
    * transferencia interna USD misma-moneda pequeña (sin MFA, < USD 1000), o
    * conversión USD->EUR pequeña (sin MFA),
  alternadas, con `Idempotency-Key` UUID por operación (D-13).

No elude controles: usa montos pequeños (< USD 1,000.00) para no requerir MFA, y la fixture D-02
con saldos/límites amplios (isolation.setup_loadtest_db_stage4) evita rechazos de fondos/límite
por diseño. Clasifica 409 esperados (idempotencia/versión) como rechazo de negocio, no como error
inesperado; 5xx/transporte como error inesperado.
"""

from __future__ import annotations

import itertools
import uuid

from locust import HttpUser, between, task

# Alternador determinista entre interna y conversión para la tarea de operaciones.
_op_toggle = itertools.cycle(["internal", "conversion"])


class Stage4User(HttpUser):
    wait_time = between(0.1, 0.3)

    @task(6)
    def read_accounts(self):
        with self.client.get("/api/v2/accounts", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"UnexpectedError:accounts:{resp.status_code}")

    @task(3)
    def read_history(self):
        with self.client.get("/api/transfers", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"UnexpectedError:history:{resp.status_code}")

    @task(1)
    def mutate(self):
        kind = next(_op_toggle)
        headers = {"Idempotency-Key": str(uuid.uuid4()), "Content-Type": "application/json"}
        if kind == "internal":
            path = "/api/v2/transfers"
            body = {"from": "SAV-2001", "to": "CHK-1001", "amount": "10.00"}
        else:
            path = "/api/conversions"
            body = {"from": "CHK-1001", "to": "EUR-3001", "amount": "10.00"}
        with self.client.post(path, json=body, headers=headers, name=path,
                              catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 409:
                # Idempotencia/versión: rechazo de negocio esperado, contabilizado aparte.
                resp.failure(f"BusinessRejection:{resp.status_code}")
            elif 400 <= resp.status_code < 500:
                resp.failure(f"BusinessRejection:{resp.status_code}")
            else:
                resp.failure(f"UnexpectedError:{path}:{resp.status_code}")
