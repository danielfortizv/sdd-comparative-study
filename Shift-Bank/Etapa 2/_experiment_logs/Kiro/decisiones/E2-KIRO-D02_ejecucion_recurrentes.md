# Decisión del investigador E2-KIRO-D02 — Modelo de ejecución de pagos recurrentes

- **ID:** E2-KIRO-D02
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** descubrimiento de requisitos y clarificación (previa a la generación de specs)
- **Estado:** APROBADA

## Contexto

El contrato funcional común (sección 3, REC-05) exige que un proceso automático ejecute los
pagos recurrentes vencidos "sin una acción humana fresca para cada ciclo". La implementación
heredada de Etapa 1 de Kiro **no tiene proceso de fondo**: usa expiración **perezosa**
(el estado se recalcula al leer o confirmar). El mecanismo de ejecución recurrente no estaba
fijado por los documentos aprobados y requería decisión del investigador por su impacto
arquitectónico.

Alternativas planteadas: (1) perezoso en acceso + disparador solo-de-test, (2) scheduler
activo en segundo plano, (3) barrido al arranque + perezoso.

## Decisión aprobada

**Opción 2 — Scheduler activo en segundo plano.** Los pagos recurrentes se ejecutan mediante
un proceso programado que corre mientras el backend está en ejecución, sin requerir acción
del usuario.

### Comportamiento funcional aprobado

1. Los pagos recurrentes se ejecutan automáticamente al vencer, sin que el usuario abra la
   app, haga una petición a la API, ni dispare la ejecución manualmente.
2. El scheduler opera mientras el backend está en ejecución.
3. Soporta recurrencia diaria, semanal y mensual conforme al contrato común aprobado
   (REC-02: incrementos de 1, 7 y 30 días respectivamente).
4. Los schedules en estado `paused` y `cancelled` nunca se ejecutan.
5. Cada ejecución revalida fondos disponibles, límites de transacción (E2-KIRO-D01) y las
   reglas de negocio aplicables.
6. Una ocurrencia programada individual no se ejecuta más de una vez, aun si el procesamiento
   se reintenta (ejecución idempotente / exactamente-una-vez por ocurrencia).
7. El scheduler soporta arranque y apagado limpios de la aplicación.
8. Las ejecuciones automáticas no requieren MFA interactiva por cada ocurrencia; se preservan
   las reglas de autorización del contrato aprobado (REC-09: autorización en la creación del
   schedule; las corridas automáticas no piden PIN interactivo).
9. La implementación debe ser probable de forma determinista, sin depender exclusivamente de
   espera en tiempo real.
10. No se introduce un endpoint administrativo público cuyo único fin sea disparar los pagos
    recurrentes (coherente con el contrato, sección 3 y 7).

### Libertad arquitectónica

El investigador aprueba el **comportamiento requerido**, no una librería concreta. No se
prescribe APScheduler ni ninguna otra. Kiro elegirá una implementación apropiada durante su
fase de diseño nativa, considerando la arquitectura FastAPI existente y evitando dependencias
innecesarias. La exigencia de testabilidad determinista (punto 9) implica separar la lógica
de "ejecutar schedules vencidos" (pura, invocable en pruebas con reloj controlado) del
disparador temporal real.

## Requisitos afectados

- **Contrato común:** REC-01..REC-12 (en particular REC-05, REC-07, REC-08, REC-09, REC-10),
  LIM-08 (re-evaluación de límites en cada corrida).
- **Escenarios de aceptación:** A15, A16, A17, A18, A19.
- **Invariantes heredados:** HER-05 (sin estados/saldos inconsistentes), HER-06 (mantener el
  alcance de usuario mock, sin funcionalidad de Etapa 3).
- **Decisión relacionada:** E2-KIRO-D01 (los límites se revalidan en cada ejecución).

## Trazabilidad

- Esta decisión condiciona el diseño del subsistema de recurrentes en la futura
  `design.md` de Etapa 2 (componente scheduler + lógica de ejecución pura y testable).
- Precede a la generación de `requirements.md`/`design.md`/`tasks.md` de la Etapa 2.
