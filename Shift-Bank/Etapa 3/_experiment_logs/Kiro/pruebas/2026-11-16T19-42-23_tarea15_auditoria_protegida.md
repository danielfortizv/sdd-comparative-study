# Evidencia — Tarea 15 (Kiro, Etapa 3): Verificación de auditoría protegida

- **Fecha/hora:** 2026-11-16T19:42:23 (local)
- **Tarea:** 15 (auto) — Verificación de auditoría protegida (`routers/audit.py`)
- **Requisitos:** R8.1, R8.2 · **Diseño:** §2.5 (verificación de la cadena), §2.6 (acceso protegido) · **AC:** AC-05
- **Backend:** `Etapa 3\Kiro\backend` (entorno `.venv`, Python 3.13.2, pytest 8.3.4)

## Qué se implementó

### Endpoint
Nuevo router `app/routers/audit.py` con el prefijo `/api/audit`, registrado en `app/main.py`
(`app.include_router(audit.router)`). Expone la verificación de integridad de la cadena de
auditoría como operación **administrativa protegida** (NO endpoint público anónimo):

- `GET  /api/audit/verify`
- `POST /api/audit/verify`

Ambas invocan `audit.verify_chain(conn)` y devuelven únicamente el veredicto:
- Cadena íntegra → `200 {"ok": true}`
- Cadena con fallo → `200 {"ok": false, "failed_seq": N, "reason": "..."}`

No se exponen payloads de auditoría ni material de clave; `failed_seq`/`reason` son metadatos no
sensibles. Las lecturas del contenido de la bitácora más allá de `verify` quedan fuera de alcance.

### Mecanismo de gating
- **Cabecera:** `X-Admin-Token`.
- **Secreto:** `SHIFT_ADMIN_TOKEN` leído del entorno vía `config.get_admin_token()` (Tarea 5).
- **Comparación en tiempo constante:** `hmac.compare_digest(provided, expected)`.
- **Denegación:** cabecera ausente o token no coincidente → **401 Unauthorized**
  (`{"error": {"code": "UNAUTHORIZED", ...}}`). Se eligió 401 (sobre 404) por claridad del
  contrato y así se documenta en el módulo. Ninguna respuesta denegada filtra el veredicto de
  `verify_chain` (sin claves `ok`/`failed_seq`/`reason`).
- **Fail-closed (R8.2):** si `SHIFT_ADMIN_TOKEN` está ausente o vacío, el endpoint **deniega**
  todo acceso (no "allow-all"). En los caminos de denegación se ejecuta una comparación señuelo
  de tiempo constante para no abrir una diferencia de temporización trivial entre
  "no configurado"/"sin cabecera" y "token erróneo".

La rutina `audit.verify_chain(conn)` permanece invocable en proceso (pruebas/CLI/runner de
carga) sin pasar por el gate; el router HTTP es la ÚNICA nueva superficie pública y está gateada.

## Pruebas — `tests/test_audit_access.py` (8 casos)

1. `test_valid_token_returns_ok_on_intact_chain` — token válido + cadena no vacía (2 transferencias
   reales sembradas vía API) → `200 {"ok": true}`.
2. `test_valid_token_post_variant` — variante POST con mismo gate/veredicto → `200 {"ok": true}`.
3. `test_missing_token_denied` — sin cabecera → `401`, sin fuga de veredicto.
4. `test_wrong_token_denied` — token erróneo → `401`.
5. `test_token_not_configured_fails_closed` — `SHIFT_ADMIN_TOKEN` desactivado (`monkeypatch.delenv`)
   → denegado sin cabecera, con cabecera cualquiera, y con el token que antes era válido (fail-closed).
6. `test_empty_token_configured_fails_closed` — token presente pero vacío/espacios → `401`.
7. `test_verify_chain_callable_in_process` — `audit.verify_chain` sigue siendo llamable directamente.
8. `test_other_endpoints_not_gated` — una transferencia y el historial responden SIN el token admin
   (confirmación de que ningún endpoint heredado empezó a exigir el token).

El token de prueba lo fija el `conftest.py` (Tarea 5): `SHIFT_ADMIN_TOKEN =
"shift-bank-stage3-test-admin-token"`, usado en los casos de token válido.

## Resultados de ejecución (reales)

### Archivo nuevo
`python -m pytest tests/test_audit_access.py -v`

```
collected 8 items
tests/test_audit_access.py::test_valid_token_returns_ok_on_intact_chain PASSED
tests/test_audit_access.py::test_valid_token_post_variant PASSED
tests/test_audit_access.py::test_missing_token_denied PASSED
tests/test_audit_access.py::test_wrong_token_denied PASSED
tests/test_audit_access.py::test_token_not_configured_fails_closed PASSED
tests/test_audit_access.py::test_empty_token_configured_fails_closed PASSED
tests/test_audit_access.py::test_verify_chain_callable_in_process PASSED
tests/test_audit_access.py::test_other_endpoints_not_gated PASSED
8 passed, 1 warning in 1.14s
```

### Suite completa
`python -m pytest -q`

```
336 passed, 1 warning in 18.30s
```

- **Conteo:** 328 previos + 8 nuevos = **336**, todos en verde.
- La única advertencia es un `DeprecationWarning` preexistente de `starlette.testclient`
  (`anyio.abc.BlockingPortal`), no relacionado con esta tarea.

## Acceptance

- El nuevo endpoint NO es alcanzable sin el token (401 confirmado sin cabecera y con token erróneo).
- Con `SHIFT_ADMIN_TOKEN` no configurado el endpoint deniega (fail-closed), no "allow-all".
- Ningún otro endpoint heredado empezó a requerir el token (transferencia e historial siguen a 200/201).
- No se modificaron `SEED-3.md` ni los datos históricos de la Etapa 2 (pruebas en DB temporal aislada
  por caso, vía `conftest.py`).

**VEREDICTO: PASS.**
