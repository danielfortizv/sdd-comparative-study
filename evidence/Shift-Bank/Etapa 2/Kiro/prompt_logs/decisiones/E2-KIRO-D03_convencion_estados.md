# Decisión del investigador E2-KIRO-D03 — Convención de estados de transferencia

- **ID:** E2-KIRO-D03
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** descubrimiento de requisitos y clarificación (previa a la generación de specs)
- **Estado:** APROBADA

## Contexto

Conflicto directo entre convenciones:

- **Etapa 1 (observado en código y API):** estados de transferencia interna en MAYÚSCULAS —
  `PENDING_MFA`, `COMPLETED`, `FAILED`, `EXPIRED` — persistidos en `transfer.status`,
  devueltos por `GET /api/transfers` y por el endpoint de confirmación MFA, y tipados
  literalmente en el frontend (`TransferStatus` en `types.ts`).
- **Contrato Etapa 2 (ACH-05/06/07, LIM-06):** estados ACH en minúsculas — `pending`,
  `settled`, `failed`.

Los invariantes HER-01/HER-02 y los escenarios A01/A02 exigen preservar el comportamiento
observable de Etapa 1, incluidos los valores de estado que la API ya emite. El mecanismo no
estaba resuelto por los documentos aprobados.

Alternativas planteadas: (1) conservar MAYÚSCULAS heredadas + minúsculas del contrato solo
para ACH; (2) normalizar todo a una convención; (3) máquinas de estado separadas con
recursos distintos.

## Decisión aprobada

**Opción 1 — Preservar los estados en MAYÚSCULAS de las transferencias internas y usar los
estados en minúsculas definidos por el contrato para las transferencias ACH.**

### Comportamiento aprobado

1. Preservar exactamente los estados de transferencia interna de Etapa 1:
   `PENDING_MFA`, `COMPLETED`, `FAILED`, `EXPIRED`.
2. Usar para las transferencias ACH los estados del contrato Etapa 2:
   `pending`, `settled`, `failed`.
3. Preservar la compatibilidad hacia atrás con las respuestas de API de Etapa 1 y el
   comportamiento del frontend. **No** renombrar ni normalizar los estados históricos de las
   transferencias internas.
4. El historial de transacciones debe soportar transferencias internas y ACH. Cada
   transferencia debe ser claramente distinguible por su tipo (`internal` o `ach`), de modo
   que el frontend y los consumidores de la API interpreten correctamente su estado.
5. Preservar el ciclo de vida ACH aprobado: débito inmediato tras la autorización, settlement
   sin débito adicional, y reembolso exactamente-una-vez para las ACH fallidas.
6. Las distintas convenciones de estado no deben introducir ambigüedad en la lógica de
   negocio, la validación, el renderizado del historial ni las pruebas automatizadas.
7. Kiro puede determinar de forma independiente los modelos de datos internos y la
   arquitectura de implementación durante la fase de diseño, siempre que se respeten estos
   contratos funcionales.

## Requisitos afectados

- **Contrato común:** ACH-05, ACH-06, ACH-07, ACH-08, ACH-09 (diferenciación en UI),
  LIM-06 (conteo diario por estado ACH).
- **Escenarios de aceptación:** A01, A02 (preservación E1), A07, A08 (ciclo ACH),
  A09 (validación).
- **Invariantes heredados:** HER-01, HER-02, HER-05.
- **Etapa 1 (baseline):** Requisitos 5 (historial), 6–8 (máquina de estados MFA) — preservados.

## Notas de implementación (no vinculantes, para la fase de diseño)

- Un campo de tipo (`internal` | `ach`) en el modelo de transferencia permite al historial
  unificado (`GET /api/transfers`) exponer ambos conjuntos de estados sin ambigüedad.
- Las ACH pendientes deben aparecer en el historial como `pending` (ACH-05/A07), conviviendo
  con los estados en MAYÚSCULAS de las internas.
- El conteo de uso diario de límites (LIM-06) debe interpretar correctamente cada convención:
  internas `COMPLETED` y ACH `pending`/`settled` cuentan; ACH `failed` tras reembolso no.

## Trazabilidad

- Decisiones relacionadas: E2-KIRO-D01 (límites), E2-KIRO-D02 (scheduler recurrente).
- Precede a la generación de `requirements.md`/`design.md`/`tasks.md` de la Etapa 2.
