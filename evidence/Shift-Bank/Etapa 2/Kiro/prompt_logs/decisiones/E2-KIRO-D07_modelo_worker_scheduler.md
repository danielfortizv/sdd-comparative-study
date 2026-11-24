# Decisión del investigador E2-KIRO-D07 — Modelo operativo de worker y scheduler

- **ID:** E2-KIRO-D07
- **Fecha:** 2026-11-16
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta:** Kiro
- **Decidido por:** investigador (aprobación explícita)
- **Fase:** refinamiento del diseño tras auditoría (previa a tasks.md)
- **Estado:** APROBADA

## Contexto

La auditoría del diseño identificó dos hallazgos HIGH relativos a la idempotencia del scheduler
de pagos recurrentes (F10 e idempotencia transaccional, F10-bis despliegue multi-worker). El
investigador fija la restricción operativa del experimento.

## Decisión aprobada

**La aplicación se ejecuta con un único proceso/worker de backend FastAPI y una única instancia
del scheduler de fondo.**

### Alcance y límites

1. Esta decisión limita el alcance de **despliegue** del experimento actual; **no** elimina el
   requisito de idempotencia financiera.
2. El diseño DEBE seguir evitando efectos financieros duplicados causados por: ciclos repetidos
   del scheduler, llamadas asíncronas solapadas, peticiones HTTP concurrentes, caídas y
   reinicios del proceso, y operaciones reintentadas.
3. El despliegue de producción multi-worker queda **fuera** del alcance operativo aprobado de la
   Etapa 2.
4. **No** se introduce infraestructura distribuida innecesaria, elección de líder (leader
   election) ni servicios de bloqueo externos.
5. La restricción de un solo worker **no** sustituye a la idempotencia durable: la garantía de
   exactamente-una-vez debe residir en el modelo de datos (restricción UNIQUE + transacción
   atómica), no en la suposición de un único proceso.

## Limitación operativa futura

Un despliegue futuro con múltiples workers requeriría revisar el arranque del scheduler (evitar
múltiples instancias) y, en su caso, un mecanismo de toma de trabajo. Para la Etapa 2 esto se
documenta como limitación conocida; la idempotencia durable del diseño hace que, aun con un
segundo disparador, la restricción UNIQUE impida el doble efecto financiero.

## Requisitos afectados

- **Requisitos Etapa 2:** R10 (scheduler), R11 (ejecución recurrente).
- **Contrato común:** REC-05, ACH-08; §3/§7 (sin endpoint admin público, sin infraestructura
  impuesta).
- **Decisiones relacionadas:** E2-KIRO-D02 (scheduler en segundo plano).
- **Hallazgos de auditoría resueltos:** F10-bis (y apoyo a F10).

## Trazabilidad

- Se incorpora a `design.md` en la sección del scheduler (modelo de worker) y en la de
  idempotencia durable de ejecuciones recurrentes.
