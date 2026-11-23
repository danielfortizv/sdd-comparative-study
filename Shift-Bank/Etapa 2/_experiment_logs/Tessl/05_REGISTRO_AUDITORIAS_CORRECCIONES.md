# E2 Tessl — Auditorías, decisiones y ciclos de corrección

## Línea temporal de evidencias

| Hito | Resultado | Fuente |
|---|---|---|
| Preparación brownfield | 66 hashes idénticos; 8 junctions Tessl; 45/45 tests heredados | Registro 01 |
| Levantamiento de requisitos | Preguntas interactivas mediante habilidades Tessl; specs aprobadas | Transcript inicial |
| Implementación inicial | 3 especificaciones nuevas; 35/35 backend + 31/31 frontend | Transcript inicial |
| Auditoría de cumplimiento inicial | 118 requisitos, 102 satisfechos, 16 parciales; 4 hallazgos y brechas | Transcript auditoría |
| Propuesta de enmiendas | 3 specs a ajustar, decisiones de fecha/reembolso/endpoint | Transcript de correcciones |
| Respuesta humana | `yes` (aprobación genérica, sin 3 decisiones explícitas) | Transcript de correcciones |
| Edición de specs y código | Corregidas cancelación, fecha y validación ACH; formalizado endpoint | Transcript de correcciones |
| Primera regresión tras cambios | 41/43 backend; 35/35 frontend | Salida Pytest/Vitest |
| Corrección de pruebas | Se corrigieron sumas y comparación de datetimes sin editar producción | Transcript de regresión |
| Regresión final | 43/43 backend; 35/35 frontend y build OK | Transcript de regresión |
| Auditoría final agente | 121/121 declarados, 0 parciales | Transcript de auditoría final |

## Defectos y decisiones

| ID | Severidad reportada | Problema | Acción aplicada | Estado metodológico |
|---|---|---|---|---|
| DEFECT-01 | Alta | Una programación `cancelled` podía pasar a `paused` y luego a `active`. | Guards HTTP 400 en pausa/reanudación; pruebas. | Corregido y comprobado por tests. |
| DEFECT-02 | Media | Sin `start_date`, primer pago se ejecutaba inmediatamente. | Se definió primera ejecución en próximo intervalo; pruebas. | Corregido según contrato aprobado, fechas pasadas aún requieren atención si el contrato se amplía. |
| DEFECT-03 | Media | Validación de routing number solo al enviar. | Validación `onChange`, error visible y botón deshabilitado; tests. | Corregido según test UI. |
| DEFECT-04 | Baja | Reintegro ACH no tiene crédito compensatorio visible en historial. | No se creó nuevo movimiento; se mantuvo el contrato literal de restaurar saldo y estado failed. | Observación de UX/ledger, NO incumplimiento literal demostrado. |
| EXTRA-01 | No aplica | Endpoint manual `POST /api/recurring/process-due` no documentado. | Se agregó a `recurring_payments.spec.md`; test. | Ampliación de contrato tras aprobación genérica. |
| TEST-01 | Media | Prueba ACH sumó transferencias que superaban el límite y esperaba HTTP 200. | Cambiadas cantidades y aserciones, incluyendo frontera exacta. | Falla del test, no del límite en código. |
| TEST-02 | Media | Comparación `datetime` naive/aware causó TypeError. | Se comparan `created_at` y `next_execution_date` de la misma respuesta. | Error de test, aunque no prueba interoperabilidad de zonas horarias en producción. |

## Enmiendas a especificaciones

- `specs/recurring_payments.spec.md`: rechazo HTTP 400 al intentar pausar estados `cancelled`/`paused`; inmutabilidad de cancelados; fecha inicial omitida = próximo intervalo; endpoint manual de simulación.
- `specs/ach_transfers.spec.md`: validación de routing de nueve dígitos en tiempo real mientras se escribe y bloqueo de envío.
- `specs/transfers.spec.md`: vínculo adicional al test de límites.
- `specs/ach_transfers.spec.md` preservó la condición ACH `failed` → restaurar saldo, marcar estado fallido, sin obligación nueva de movimiento contable separado.

**Observación de control experimental:** el agente recibió `yes` ante una solicitud de tres respuestas independientes. Es legítimo documentar que la implementación continuó, pero **no debe afirmarse que el investigador eligió explícitamente cada alternativa de forma individual**. Además, se modificaron especificaciones antes del código dentro de ese ciclo, consistente con la intención SDD.

## Auditoría final: alcance y prudencia

El reporte final declaró 121/121 requisitos satisfechos. La traza visible de esa auditoría final muestra activación de `spec-verification` y `work-review`, seguida de lectura de los siete `.spec.md`. No consta una nueva inspección exhaustiva de implementación durante ese turno; el informe parece reutilizar evidencia de pasos previos. Esto es **evidencia de evaluación reportada por el agente**, no un censo externo auditable de requisito→test→línea de código.

**Regresión funcional:** la ejecución real de pruebas finales respalda que no se rompieron los escenarios cubiertos por las suites heredadas; no prueba regresión cero para cualquier interacción posible.
