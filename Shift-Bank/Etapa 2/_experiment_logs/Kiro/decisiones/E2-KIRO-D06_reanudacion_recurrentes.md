# Decisión del investigador E2-KIRO-D06 — Reanudación de recurrentes y ocurrencias perdidas

- **ID:** E2-KIRO-D06
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** refinamiento de requisitos tras auditoría (previa a diseño)
- **Estado:** APROBADA

## Contexto

La auditoría de `requirements.md` identificó un caso límite no resuelto (Observación 5): al
reanudar un schedule que estuvo `paused`, ¿se ejecutan retroactivamente las ocurrencias cuyo
vencimiento cayó durante la pausa (catch-up) o se saltan? El escenario A18 del contrato no lo
fija, y el diseño necesita una política determinista. El investigador resuelve la ambigüedad.

## Decisión aprobada

**Política de reanudación sin catch-up.** Al reanudar, la siguiente fecha de vencimiento se
recalcula desde la fecha de reanudación usando el intervalo configurado; las ocurrencias
perdidas durante la pausa no se ejecutan retroactivamente.

### Comportamiento aprobado

1. Los schedules en estado `paused` nunca se ejecutan.
2. Las ocurrencias cuya fecha de ejecución programada pasa mientras el schedule está `paused`
   se **saltan**.
3. Al reanudar un schedule `paused`, las ocurrencias perdidas **no** se ejecutan de forma
   retroactiva.
4. La siguiente fecha de ejecución se **recalcula desde la fecha de reanudación** usando el
   intervalo de recurrencia aprobado.
5. Los intervalos diario, semanal y mensual permanecen consistentes con el contrato
   (1, 7 y 30 días).
6. La reanudación no debe provocar pagos duplicados ni débitos acumulados inmediatos.
7. Los schedules `cancelled` permanecen terminales y no pueden reanudarse.

## Requisitos afectados

- **Contrato común:** REC-06, REC-07, REC-08, REC-02.
- **Escenario de aceptación:** A18.
- **Decisiones relacionadas:** E2-KIRO-D02 (scheduler, exactamente-una-vez).
- **Requisito Etapa 2 modificado:** R9 (nuevos criterios de aceptación 9.6 y 9.7).

## Trazabilidad

- Resuelve la Observación 5 de la auditoría de requisitos (Registro 02).
- Se incorpora a `requirements.md` como criterios independientes y verificables en R9.
