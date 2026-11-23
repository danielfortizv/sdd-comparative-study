# E2 · Kiro · Registro 04 — Generación de design.md (Etapa 2)

- **Fecha:** 2026-11-16
- **Etapa:** 2 · Herramienta: Kiro
- **Fase:** diseño técnico (SDD nativo: requirements → design → tasks → impl)
- **Autorización:** el investigador aprobó el alcance funcional de `requirements.md` corregido y
  autorizó la fase de diseño, sujeta a dos chequeos de consistencia previos.

## Chequeos de consistencia previos (solicitados)

1. **R3 — número de criterios.** Verificado sobre el texto real: R3 tiene **8** criterios
   (3.1–3.8). La observación del investigador es correcta; el error estaba en el **reporte
   previo** (describí R3 como "6→7"), no en la especificación. Desglose real del total: R1=6,
   R2=5, R3=8, R4=4, R5=4, R6=5, R7=4, R8=7, R9=7, R10=6, R11=4, R12=3, R13=5, R14=6, R15=8,
   R16=4 → **86 criterios**. Confirmado: 86.
2. **A09 — trazabilidad.** La fila contenía `A09 | 3.1, 3.8, 13.4`. A09 trata de validación de
   **monto de transferencia**; R13.4 trata de validación de **actualización de límites** (su
   lugar correcto es LIM-09, ya mapeado). Corrección aplicada: `A09 | 3.1, 3.8`. No cambia el
   alcance funcional (solo trazabilidad en tabla).

## Artefacto generado

- **Ruta:** `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/design.md`
- **Bytes:** 32.435 · **Líneas físicas:** 512
- **SHA-256:** `AB53F2C83F042B6665F9BE4922284A59790E35BD2231ED06615F72719CB1ED93`

## requirements.md tras la corrección A09

- **Bytes:** 34.532 · **Líneas:** 600 · **Criterios:** 86
- **SHA-256:** `D75CDB69FF7CFAEA9F9140CF5DD69DC4C3ABFD6F443AA58F18F4B15F2E2D1401`
  (cambió respecto al registro 03 por la única edición de la fila A09).

## Decisiones técnicas de diseño (documentadas y justificadas)

- DD-1: reutilizar `transfer` con columna `type` (internal/ach) + columnas ACH anulables.
- DD-2: scheduler como tarea asyncio de fondo en el `lifespan` de FastAPI (sin librería externa).
- DD-3: lógica `process_due(now)` pura con reloj inyectable, separada del disparador temporal.
- DD-4: idempotencia financiera por guarda de transición de estado dentro de la transacción.
- DD-5: migración de esquema idempotente aditiva (CREATE IF NOT EXISTS / ALTER con PRAGMA check).
- DD-6: límites en fila única; consumo diario calculado por agregación (día UTC), no almacenado.

## Cobertura

- ACH-01..10 (§A), REC-01..12 (§B), LIM-01..09 (§C), HER-01..06 (§D).
- A01..A19 → estrategia de pruebas con reloj inyectable; A20/A21 → sección de verificación.
- Tabla requisito→diseño incluida (R1..R16 mapeados a componentes).

## Integridad

- Specs de Etapa 1: sin cambios (git limpio).
- Seed común y contrato funcional: no modificados.
- Decisiones D01–D06 y evidencia previa (Registros 01–03, inventarios, smoke test): preservadas.
- No se generó `tasks.md`, pruebas ni código de aplicación.

## Estado

`design.md` generado. A la espera de revisión y aprobación explícita del investigador antes de
generar `tasks.md` o implementar.
