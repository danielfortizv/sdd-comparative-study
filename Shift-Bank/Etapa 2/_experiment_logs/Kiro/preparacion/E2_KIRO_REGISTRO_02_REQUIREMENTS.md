# E2 · Kiro · Registro 02 — Generación de requirements.md (Etapa 2)

- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Fase:** especificación de requisitos (SDD nativo: requirements → design → tasks → impl)
- **Autorización:** el investigador autorizó generar **solo** `requirements.md`.

## Artefacto generado

- **Ruta:** `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/requirements.md`
- **Tamaño:** 31.380 bytes
- **Estructura:** nueva feature spec `shift-bank-stage2` (no modifica la spec heredada
  `shift-bank` de la Etapa 1).

## Métricas

- Requisitos funcionales: **16** (agrupados en A. ACH, B. Recurrentes, C. Límites,
  D. Compatibilidad E1).
- Historias de usuario: **16** (una por requisito).
- Criterios de aceptación (EARS): **82**.

## Fuentes autoritativas utilizadas

- `Etapa 2/SEED-2.md` (aprobado como entrada autoritativa).
- `Etapa 2/E2_COMMON_FUNCTIONAL_CONTRACT.md` (aprobado).
- Decisiones `E2-KIRO-D01..D05` (en `decisiones/`).
- Specs heredadas `shift-bank/{requirements,design,tasks}.md` y comportamiento observado en
  el código (backend FastAPI/sqlite3, frontend React/TS).

## Cobertura (trazabilidad declarada en el propio documento)

- ACH-01..ACH-10 → cubiertos por Requisitos 1–7.
- REC-01..REC-12 → cubiertos por Requisitos 8–12.
- LIM-01..LIM-09 → cubiertos por Requisitos 13–14.
- HER-01..HER-06 → cubiertos por Requisitos 15–16 (y referencias cruzadas).
- A01..A19 → mapeados a criterios concretos; A20 (suite de pruebas) y A21 (inspección manual
  de UI) se marcan como escenarios de verificación a materializar en `tasks.md`/fase de
  verificación, no como requisitos funcionales.

## Decisiones del investigador incorporadas (sin contradicción)

- D01 límites 5.000.000 / 10.000.000 COP → Req. 13, 14.
- D02 scheduler en segundo plano, idempotente, testable → Req. 10, 11.
- D03 estados MAYÚSCULAS internas + minúsculas ACH + tipo internal/ach → Req. 6, 15.
- D04 umbral MFA ACH ≥ 1.000.000 COP, límites antes de MFA → Req. 3, 14.
- D05 historial internas sin cambios + beneficiario ACH enmascarado → Req. 6, 1.

## Separación de evidencia

- Las **decisiones del investigador** permanecen en `decisiones/` (D01–D05).
- La **especificación generada** vive en `.kiro/specs/shift-bank-stage2/` (artefacto SDD).
- Este **registro de actividad** vive en `preparacion/`, separado de ambas.

## Integridad verificada

- Specs heredadas de Etapa 1 (`Etapa 1/Kiro/.kiro`): sin cambios (git limpio).
- Specs de Etapa 1 en la copia de trabajo (`Etapa 2/Kiro/.kiro/specs/shift-bank`): no
  modificadas.
- No se generó `design.md`, `tasks.md`, pruebas ni código de aplicación.
- Evidencia previa (D01–D05, registro 01, inventarios, smoke test) preservada.

## Estado

Generación de `requirements.md` completada. A la espera de revisión y aprobación explícita del
investigador antes de proceder a `design.md`.
