# Decisión del investigador E2-KIRO-D04 — Umbral de MFA para transferencias ACH directas

- **ID:** E2-KIRO-D04
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** descubrimiento de requisitos y clarificación (previa a la generación de specs)
- **Estado:** APROBADA

## Contexto

El contrato (HER-04) exige que las ACH directas "sensibles" requieran las verificaciones de
MFA heredadas, tras las verificaciones de límite de transferencia (LIM-07). Pero "sensible"
no estaba definido para ACH: no se especificaba si aplica el umbral heredado de 1.000.000 COP
o si toda ACH a un tercero es sensible por definición. Regla de negocio de seguridad que
requería decisión del investigador.

Alternativas planteadas: (1) mismo umbral heredado (≥ 1.000.000 COP); (2) toda ACH requiere
MFA; (3) umbral propio para ACH.

## Decisión aprobada

**Opción 1 — Aplicar a las ACH directas el umbral de MFA existente de Etapa 1.**

### Comportamiento funcional aprobado

1. Las ACH directas requieren MFA cuando el monto es **mayor o igual a 1.000.000 COP**,
   exactamente como en Etapa 1.
2. Las ACH por debajo de 1.000.000 COP no requieren MFA, siempre que superen las demás
   validaciones.
3. Se preserva el comportamiento MFA heredado de Etapa 1:
   - El código de verificación simulado existente (`123456`).
   - El periodo de expiración de MFA existente (5 minutos).
   - El manejo de código inválido existente (permanece pendiente, permite reintento, sin
     lockout).
   - Las transiciones de estado MFA existentes.
4. Los límites de transferencia y la validación de saldo se aplican **antes** de completar la
   autorización MFA. Un código MFA correcto nunca puede saltarse los límites de transacción
   ni la restricción de fondos insuficientes (LIM-07, A14).
5. En las ACH que requieren MFA, la cuenta **no se debita** hasta que la autorización MFA
   tiene éxito. Una vez autorizada, la transferencia entra en estado ACH `pending` y la
   cuenta se debita de inmediato (ACH-05).
6. Una autorización MFA fallida o expirada no debe producir un débito financiero no
   autorizado.
7. Se preserva el comportamiento de settlement y fallo ACH aprobado, incluido el reembolso
   exactamente-una-vez cuando una ACH previamente debitada falla (ACH-07/ACH-08).
8. Se preserva la distinción entre estados de transferencia interna y estados ACH establecida
   en E2-KIRO-D03.
9. Los pagos recurrentes siguen las reglas de autorización MFA del contrato común aprobado:
   autorización al crear un schedule sensible, sin requerir MFA interactiva en cada ejecución
   automática (REC-09, coherente con E2-KIRO-D02).

### Orden de comprobaciones aprobado (ACH directa)

1. Validación de formato (beneficiario, routing 9 dígitos, cuenta 4–17 dígitos) y monto
   (positivo, ≤ 2 decimales).
2. Validación de fondos suficientes.
3. Validación de límites (por transferencia y diario) — E2-KIRO-D01.
4. Si monto ≥ 1.000.000 COP: paso de MFA. Sin débito hasta autorización exitosa.
5. Tras autorización (o directamente si < umbral): estado ACH `pending` + débito inmediato.

## Requisitos afectados

- **Contrato común:** HER-03, HER-04, ACH-04, ACH-05, ACH-07, ACH-08, LIM-03, LIM-07.
- **Escenarios de aceptación:** A08, A11, A13, A14.
- **Invariantes heredados:** HER-03 (preservar PIN/umbral/expiración/manejo de errores E1),
  HER-05 (sin estados/saldos inconsistentes).
- **Etapa 1 (baseline):** Requisitos 6 (umbral MFA), 7 (confirmación MFA), 8 (expiración/
  fallo) — preservados y reutilizados para ACH.
- **Decisiones relacionadas:** E2-KIRO-D01 (límites antes de MFA), E2-KIRO-D02 (recurrentes),
  E2-KIRO-D03 (convención de estados).

## Trazabilidad

- Precede a la generación de `requirements.md`/`design.md`/`tasks.md` de la Etapa 2.
