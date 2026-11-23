# Decisión del investigador E2-KIRO-D05 — Representación del destino ACH en el historial

- **ID:** E2-KIRO-D05
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** descubrimiento de requisitos y clarificación (previa a la generación de specs)
- **Estado:** APROBADA

## Contexto

El historial heredado (`GET /api/transfers`) devuelve `direction { from, to }` asumiendo que
origen y destino son cuentas internas (`checking`/`savings`). Una ACH va de una cuenta interna
hacia un beneficiario externo (nombre, banco, routing, número de cuenta), que no encaja en ese
shape. El contrato exige que la ACH aparezca en el historial unificado (ACH-05/A07) y se
distinga de las internas (ACH-09), pero no fijaba la forma del destino externo ni cómo
preservar el `direction` heredado. Afecta el contrato observable del historial y la
compatibilidad hacia atrás (HER-01/A01).

Alternativas planteadas: (1) preservar `direction` para internas + bloque beneficiario en ACH;
(2) generalizar `direction` a origen/destino tipados; (3) recurso separado para historial ACH.

## Decisión aprobada

**Opción 1 — Preservar la estructura de historial de transferencias internas y extender las
entradas ACH con información adicional del beneficiario.**

### Comportamiento funcional aprobado

1. Preservar la representación de historial de Etapa 1 para transferencias internas, incluido:

   ```json
   "direction": { "from": "Checking", "to": "Savings" }
   ```

2. Las respuestas de API de transferencias internas permanecen compatibles hacia atrás. No se
   renombran, eliminan ni reestructuran sus campos existentes.
3. Las transferencias ACH aparecen en el historial unificado (`GET /api/transfers`), con sus
   estados `pending`, `settled` y `failed`.
4. Cada entrada del historial identifica su tipo de transferencia (`internal` o `ach`),
   conforme a E2-KIRO-D03.
5. Las entradas ACH incluyen una representación adicional del beneficiario con:
   - Nombre del beneficiario.
   - Banco del beneficiario.
   - Número de cuenta del beneficiario **enmascarado**, exponiendo solo los últimos 4 dígitos.
6. Nunca se exponen números de cuenta de beneficiario completos ni otra información bancaria
   sensible innecesaria en las respuestas del historial (coherente con el Requisito 2 de E1:
   no exponer identificadores internos).
7. El frontend muestra con claridad las transferencias internas y ACH, preservando el
   renderizado existente de las internas y presentando la información del beneficiario externo
   y el estado ACH de forma apropiada.
8. Se mantienen los requisitos aprobados de consistencia monetaria, ciclo de vida de la
   transacción, MFA y límites dinámicos.
9. Kiro tiene libertad arquitectónica para determinar el modelo de datos interno y la
   implementación de la API durante la fase de diseño, siempre que se preserven la
   compatibilidad hacia atrás y el comportamiento funcional aprobado.

## Requisitos afectados

- **Contrato común:** ACH-02 (no exponer datos de otro usuario), ACH-05, ACH-09 (UI
  diferenciada), ACH-03 (datos del beneficiario), REC-11 (el schedule retiene datos de destino
  suficientes).
- **Escenarios de aceptación:** A01, A03, A04, A07, A21 (inspección de UI).
- **Invariantes heredados:** HER-01 (historial/queries de E1 siguen funcionando), HER-06.
- **Etapa 1 (baseline):** Requisitos 2 (no exponer identificadores internos), 5 (historial)
  — preservados.
- **Decisiones relacionadas:** E2-KIRO-D03 (campo de tipo internal/ach), E2-KIRO-D04 (ciclo
  ACH).

## Trazabilidad

- Precede a la generación de `requirements.md`/`design.md`/`tasks.md` de la Etapa 2.
- Cierra la quinta ambigüedad material (A–E) identificada en el descubrimiento.
