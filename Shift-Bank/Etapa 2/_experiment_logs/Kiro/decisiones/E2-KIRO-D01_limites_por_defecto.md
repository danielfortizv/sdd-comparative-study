# Decisión del investigador E2-KIRO-D01 — Valores por defecto de límites dinámicos (COP)

- **ID:** E2-KIRO-D01
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** descubrimiento de requisitos y clarificación (previa a la generación de specs)
- **Estado:** APROBADA

## Contexto

El contrato funcional común (sección 4, LIM-01..09) exige un límite por transferencia y un
límite diario acumulado para el usuario mock, configurables por el usuario, y **prohíbe
importar montos en USD** a una aplicación basada en COP: los valores iniciales deben
aprobarse explícitamente para la moneda de cada implementación heredada. El baseline de
Etapa 1 de Kiro opera en COP con saldos iniciales Checking = 5.000.000,00 y
Savings = 15.000.000,00, y umbral de MFA = 1.000.000,00 COP.

## Decisión aprobada

| Parámetro | Valor aprobado (COP) | En centavos (modelo E1) |
|---|---|---|
| Límite por transferencia | **5.000.000** | 500.000.000 |
| Límite diario acumulado | **10.000.000** | 1.000.000.000 |

### Alcance de aplicación

- Los límites aplican al **usuario mock autenticado**.
- Deben aplicarse de forma consistente a: **transferencias internas**, **transferencias ACH**
  y **ejecuciones de pagos recurrentes** (internas y ACH).
- Los límites son **configurables por el usuario** (editables desde la UI), conforme al
  contrato funcional aprobado (LIM-01, LIM-02).

### Invariantes heredados que se preservan

- Modelo monetario de Etapa 1: **centavos enteros (`INTEGER`), moneda COP**. Sin cambios.
- **Umbral de MFA = 1.000.000 COP**, sin cambios.
- **No** se modifican los saldos heredados ni las transacciones históricas sembradas.

## Justificación

- 5.000.000 COP por transferencia coincide con el saldo inicial de Checking, un tope por
  operación razonable y coherente con la escala monetaria de la aplicación heredada.
- 10.000.000 COP diarios acumulados permiten varias operaciones por día dentro de la escala
  de los saldos sembrados (Checking 5M, Savings 15M) y habilitan los escenarios de
  aceptación de consumo diario del contrato (A12, con unidades en la moneda COP de esta
  herramienta en lugar de las 1000 unidades del ejemplo).
- Ambos valores se expresan en COP, respetando la prohibición de importar montos USD y la
  exigencia de aprobación de moneda del contrato.

## Requisitos afectados

- **Contrato común:** LIM-01, LIM-02, LIM-03, LIM-04, LIM-05, LIM-07, LIM-08.
- **Escenarios de aceptación:** A10, A11, A12, A14.
- **Invariantes heredados:** HER-01, HER-03, HER-04 (preservar modelo monetario, MFA y
  saldos/historial heredados).
- **Etapa 1 (baseline):** Requisitos 1.3 (saldos), 6.2 (umbral MFA) — preservados sin cambios.

## Trazabilidad

- Precede a la generación de `requirements.md`/`design.md`/`tasks.md` de la Etapa 2.
- Estos valores serán los valores por defecto iniciales; la configurabilidad por el usuario
  se especificará como requisito verificable en la futura spec de Etapa 2.
