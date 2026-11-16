# E2 · Kiro · Registro 06 — Generación de tasks.md (Etapa 2)

- **Fecha:** 2026-11-16 · Etapa 2 · Herramienta: Kiro
- **Fase:** planificación de implementación (SDD nativo: requirements → design → tasks → impl)
- **Autorización:** el investigador aprobó `design.md` (con D01–D07) y autorizó generar **solo**
  `tasks.md`. Sin implementar código ni pruebas.

## Artefacto generado

- **Ruta:** `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md`
- **Bytes:** 22.841 · **Líneas físicas:** 385
- **SHA-256:** `4C68862390E218A423BFD74B51F1FED98B70AD262CF132BE2FABC00DA40B3DF1`

## Estructura

- **46 tareas** numeradas (orden = orden de ejecución recomendado), con viñetas de detalle
  (93 líneas de subtarea estilo Kiro) y referencias `_Requisitos:_` / `_Contrato:_` / `_Diseño:_`
  / `_Decisión:_`.
- Organizadas en 7 fases (A–G) con dependencias explícitas.
- **13 tareas de verificación** marcadas `**(verificación)**` (2, 3, 4, 5, 13, 18, 26, 34, 40,
  41, 42, 43, 44); el resto son de implementación/registro.

### Desglose por fase

| Fase | Tareas | Contenido |
|---|---|---|
| A — Baseline + regresión E1 | 1–6 | arnés de pruebas aislado, regresión cuentas/internas/MFA/API, checkpoint |
| B — Evolución de BD y cimientos | 7–13 | migración transaccional, tablas nuevas + UNIQUE/índices, clock, utilidades tx, seed límites, lifespan, pruebas de migración |
| C — Límites dinámicos | 14–18 | servicio/endpoints de límites, consumo diario UTC, integración en internas, pruebas de concurrencia |
| D — Beneficiarios + ACH | 19–26 | beneficiarios + enmascarado, `pending_auth`, débito atómico, settlement, reembolso, historial unificado, pruebas |
| E — Recurrentes + scheduler | 27–34 | schedules, D06, ejecución durable atómica (UNIQUE), scheduler único worker, pruebas deterministas |
| F — Frontend | 35–39 | cliente/tipos, navegación, ACH/beneficiarios, historial, recurrentes/límites |
| G — Verificación + evidencia | 40–46 | regresión, aceptación A01–A19, A20 build, A21 manual, integridad BD, registro de resultados reales |

## Orden de dependencias

A ▶ B ▶ C ▶ D ▶ E ▶ F ▶ G. B provee esquema/utilidades a C/D/E; C precede a D/E (límites); D
precede a E (ciclo ACH reutilizado); F tras endpoints; G al final.

## Cobertura

- R1–R16: todos representados (tabla de cobertura en el documento).
- 86 criterios: ruta de implementación + verificación.
- ACH-01..10 (19–26), REC-01..12 (27–34), LIM-01..09 (14–18), HER-01..06 (2–5, 16, 40, 44).
- A01–A19 (tarea 41), A20 (40, 42, 45), A21 (43).
- Correcciones de auditoría reflejadas: F10/DD-7 (8, 30), F10-bis/D07 (32), F7 (21, 22),
  F8/F9 (15, 16, 30), F11 (7, 13), F12 (7), F3 (21), F13 (8), UI-1 (35, 38), startup (12).

## Restricciones arquitectónicas preservadas

Atomicidad financiera, idempotencia recurrente durable (UNIQUE + transacción), ciclo ACH (sin
débito pre-MFA, sin re-débito en settlement, reembolso único), migración transaccional no
destructiva, autonomía del scheduler, compatibilidad hacia atrás, D01–D07 vinculantes. Sin ORM,
sin scheduler distribuido, sin microservicios.

## Primera tarea recomendada

**Tarea 1** (arnés de pruebas con DB aislada): habilita la Fase A (baseline de E1 antes de
modificar), protege los datos históricos (Req. 15.8) y es la base de verificación del resto.

## Integridad

- Modificado/creado: solo `tasks.md` (nuevo) y este registro.
- `requirements.md` (SHA `D75CDB69…`) y `design.md` (SHA `FA8F38DF…`) **sin cambios** (verificado).
- Specs de E1, seed común, contrato y decisiones D01–D07: preservados. E1 git limpio.
- No se generó código de aplicación ni pruebas; no se instalaron dependencias.

## Aclaración

No se ha ejecutado ni validado ninguna tarea; `tasks.md` es un plan. Las pruebas y métricas se
producirán en la fase de implementación, registrando resultados reales (sin fabricar).
