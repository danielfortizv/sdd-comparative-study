# Evidencia — Tarea 22: Verificación de invariantes post-carga

- **Fecha:** 2026-11-16 (-0500)
- **Tarea:** 22 (auto) (verificación) — Verificación de invariantes post-carga
  (`loadtest/verify_invariants.py`)
- **Spec:** `Etapa 3/Kiro/.kiro/specs/shift-bank-stage3`
- **Requisitos:** R10.4 (conservación del dinero, ausencia de estados parciales, cadena íntegra
  incluida el ancla), R10.5 (cualquier violación ⇒ corrida FALLIDA, independiente del rendimiento)
- **Diseño:** §3.4 (Verificación de corrección bajo concurrencia)
- **AC:** AC-09
- **Entorno:** Python (venv `backend/.venv`) · Windows · ejecutado desde `Etapa 3/Kiro/backend`

---

## 1. Artefactos creados / modificados

| Archivo | Tipo | Propósito |
|---|---|---|
| `Etapa 3/Kiro/loadtest/verify_invariants.py` | nuevo | Verificador post-carga: conservación del dinero, ausencia de estados parciales, `audit.verify_chain` íntegra (incluida el ancla). API fail-loud + CLI. |
| `Etapa 3/Kiro/backend/tests/test_loadtest_invariants.py` | nuevo | 15 pruebas (positivas + negativas + fail-loud) que ejercen el verificador con transacciones financieras REALES vía la capa de servicio. |

No se modificó código de la app (`app/*`), ni `SEED-3.md`, ni dato alguno de la Etapa 2. No se
optimizó la app. Las decisiones aprobadas D-E3-01..04 se preservan (no se tocaron claves por
entorno, cifrado en reposo, auditoría ni topología de despliegue).

---

## 2. Fórmula de conservación — DERIVADA del esquema real (no inventada)

Leyendo `db.py`, `repository.py`, `ach_repository.py`, `service.py` y `ach_service.py`:

- `account.balance_cents` = saldos de las dos cuentas internas (checking/savings).
- **Transferencia interna** (`type='internal'`): débito del origen + abono al destino en la MISMA
  `financial_transaction` (`repository.apply_transfer_in_tx`) ⇒ **la suma de saldos se conserva**;
  el dinero permanece dentro del sistema.
- **Transferencia ACH** (`type='ach'`): débito del origen hacia un beneficiario EXTERNO
  (`ach_repository.debit_source_no_commit`) ⇒ el dinero **sale del sistema**. El débito ocurre al
  activar (`pending`) y persiste en `settled`. Una ACH `failed` reembolsa **exactamente una vez**
  (`fail_and_refund_no_commit`, guarda `refunded 0→1`) ⇒ el dinero **vuelve** a los saldos. Las
  ACH `pending_auth`/`expired` nunca debitaron.

Invariante resultante:

```
total_inicial_sembrado
    == SUM(account.balance_cents)
       + SUM(transfer.amount_cents WHERE type='ach' AND status IN ('pending','settled'))
```

El runner pasa `expected_total_cents` = total inicial sembrado (conocido de `isolation.py`:
checking + savings = 2 · 1.000.000.000.000 centavos). Si no se provee, se usa el total actual
reconstruido como apoyo diagnóstico (documentado: esa ruta no detecta pérdida/creación por sí
sola; la verificación fuerte requiere el inicial conocido).

---

## 3. Ausencia de estados parciales — columnas de estado REALES

Catálogo de reposo derivado del código de servicio:

- Internos (`service.py`): `PENDING_MFA`, `COMPLETED`, `EXPIRED`, `FAILED`.
- ACH (`ach_service.py`): `pending_auth`, `pending`, `settled`, `failed`, `expired`.

Coherencia estado↔columna que se verifica (un débito-sin-crédito es imposible dentro de una sola
transacción financiera; su manifestación observable es la incoherencia de columna):

- interna `COMPLETED` ⇒ `completed_at` no nulo;
- ACH `settled` ⇒ `settled_at` no nulo;
- ACH `failed` ⇒ `refunded = 1` (reembolso exactamente-una-vez ya aplicado);
- cualquier `status` fuera del catálogo ⇒ estado parcial/prohibido.

---

## 4. Integridad de cadena (incluida el ancla) y fail-loud

- Se invoca `audit.verify_chain(conn)` sobre la conexión de la DB de carga; `ok` debe ser `True`.
  `verify_chain` ya cubre manipulación de contenido, reordenamiento, eliminación intermedia
  (contigüidad de `seq`) y **truncación del final vía el ancla de cola** (§2.9).
- **Fail-loud (R10.5):** `verify_invariants(db_path, expected_total_cents=None) -> InvariantReport`
  con `ok: bool` y `violations`. Cualquier violación ⇒ `ok=False`. Una DB ausente/ilegible/sin
  esquema o una cadena no verificable se reportan como violación (`precondition`/`audit_chain`),
  **nunca** como PASS. No se tragan excepciones (`sqlite3.Error` → violación explícita).
  `assert_ok()` lanza `InvariantError` para llamadores que prefieran excepción. El CLI
  (`python -m loadtest.verify_invariants <db>`) devuelve salida != 0 ante cualquier violación.
- No se importa `locust`/gevent (evita `monkey.patch_all`), coherente con `report.py`; solo se
  usa stdlib + el paquete `app` (importable vía `isolation`, que añade `backend/` a `sys.path`).

---

## 5. Pruebas (transacciones financieras REALES, sin mocks)

`backend/tests/test_loadtest_invariants.py` siembra una DB de archivo aislada con
`loadtest.isolation.setup_loadtest_db` y ejecuta movimientos reales vía
`app.service.create_transfer` y `app.ach_service.create_ach/settle_ach/fail_ach` (reloj manual
determinista para el settlement). Cobertura:

**Positivas (conservación + cadena íntegras):**
- transferencias internas alternando dirección ⇒ suma de saldos conservada, salida ACH = 0;
- ACH `pending` ⇒ la suma de saldos SOLA queda corta por el débito, pero `saldos + salida_ACH`
  recupera el total sembrado (valida la fórmula derivada);
- ACH `settled` ⇒ sigue contando como salida; conservación intacta;
- ACH `failed` con reembolso ⇒ el dinero vuelve, salida = 0; conservación intacta;
- `assert_ok()` no lanza en estado sano.

**Negativas (cada violación DEBE detectarse):**
- saldo corrompido hacia arriba (dinero creado) ⇒ `money_conservation`; `assert_ok` lanza;
- saldo corrompido hacia abajo (dinero destruido) ⇒ `money_conservation`;
- fila de `audit_log` manipulada (payload alterado sin recalcular HMAC) ⇒ `audit_chain`
  con `audit_failed_seq` no nulo;
- cola de auditoría truncada (última entrada borrada, ancla intacta) ⇒ `audit_chain` vía ancla;
- ACH `settled` sin `settled_at` ⇒ `partial_state`;
- interna `COMPLETED` sin `completed_at` ⇒ `partial_state`;
- `status` desconocido (`WEIRD_INTERMEDIATE`) ⇒ `partial_state`.

**Fail-loud:**
- DB inexistente ⇒ `ok=False` (`precondition`), nunca PASS silencioso;
- DB sin esquema (archivo SQLite vacío) ⇒ `ok=False` (`precondition`);
- sin `expected_total_cents` ⇒ fallback usa el observado (apoyo diagnóstico), estado consistente ok.

### Resultado del módulo nuevo (ejecutado realmente)

```
$ backend/.venv/Scripts/python.exe -m pytest tests/test_loadtest_invariants.py -q
...............                                [100%]
15 passed in 0.92s
```

Comando exacto (desde `Etapa 3/Kiro/backend`): `.\.venv\Scripts\python.exe -m pytest -q`
(suite completa) y `.\.venv\Scripts\python.exe -m pytest tests/test_loadtest_invariants.py -q`
(módulo nuevo).

### Suite completa (regresión)

> **Verificada (corrida real completada).** Comando exacto desde `Etapa 3\Kiro\backend`:
> `.\.venv\Scripts\python.exe -m pytest -q`. Resultado real observado:
> **372 passed, 1 warning in 24.60s**. El único warning es el DeprecationWarning preexistente de
> starlette/anyio (`test_ach.py::test_crear_y_listar_beneficiario_enmascarado`), ajeno a esta
> tarea. Esto confirma la progresión 357 (baseline Tarea 21) -> **372** (357 + 15 pruebas nuevas),
> sin regresiones.

---

## 6. Veredicto

- ✅ `loadtest/verify_invariants.py`: `verify_invariants(db_path, expected_total_cents) ->
  InvariantReport` (ok + violaciones) con conservación derivada del esquema real, ausencia de
  estados parciales sobre columnas reales, y `audit.verify_chain` íntegra incluida el ancla.
- ✅ Fail-loud (R10.5): cualquier violación o estado no verificable ⇒ `ok=False` / salida != 0;
  nunca un PASS para un estado inverificable.
- ✅ 15 pruebas (positivas, negativas y fail-loud) con transacciones financieras reales:
  **15 PASS** (ejecutadas y verificadas).
- ✅ Suite completa (regresión): **372 passed, 1 warning in 24.60s** (verificada); baseline previo 357, total
  esperado 372 (a confirmar con una corrida real).
- ✅ No se tocó `app/*`, `SEED-3.md` ni datos de la Etapa 2; D-E3-01..04 preservadas.

**ESTADO: COMPLETO. Módulo 15/15 PASS; suite completa verificada en verde (372/372).**
