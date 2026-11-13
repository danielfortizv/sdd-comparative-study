# Tessl — Etapa 2 — Registro de implementación inicial

## 1. Identificación del experimento

- Proyecto: Shift Bank.
- Herramienta SDD: Tessl.
- Etapa: 2 — Complejidad funcional y estado (brownfield inicial).
- Alcance: Opción A — Transferencias ACH/interbancarias, pagos recurrentes y límites dinámicos.
- Entorno: Windows, PowerShell y Gemini CLI.
- Fecha de la evidencia: 13 de noviembre de 2026.
- Fuente: Transcripción de la primera sesión de desarrollo de Etapa 2.
- Estado: Implementación reportada como terminada por el agente; auditoría independiente y validación manual pendientes.

## 2. Estado inicial

La Etapa 2 comenzó a partir de una copia independiente de la Etapa 1, cuya integridad había sido comprobada mediante un manifiesto SHA-256 de 66 archivos.

La línea base contenía:

| Indicador | Etapa 1 |
|---|---:|
| Especificaciones | 4 |
| Líneas de especificación | 241 |
| Pruebas backend aprobadas | 22 |
| Pruebas frontend aprobadas | 23 |
| Total pruebas aprobadas | 45 |

La ejecución recibió instrucciones de preservar los componentes existentes, seguir el flujo SDD de Tessl y aprobar las especificaciones antes de modificar el código.

## 3. Recopilación de requisitos

Gemini activó la habilidad `requirement-gathering`, inspeccionó las cuatro especificaciones heredadas, los modelos, los esquemas y servicios principales, y realizó una entrevista interactiva.

Se registraron **14 decisiones funcionales**:

| Área | Decisión aprobada por el usuario |
|---|---|
| Beneficiarios ACH | Guardados y ad hoc |
| Liquidación ACH | Ciclo simulado `pending` a `settled` |
| Disparador de liquidación | Planificador automático |
| Débito ACH | Inmediato al crear la transferencia |
| Validación de beneficiarios | Validación de formato |
| Pagos recurrentes | Transferencias internas y ACH |
| Ejecución recurrente | Planificador automático |
| Estados de programación | `active`, `paused`, `cancelled` |
| Límites | Por transacción y acumulado diario |
| Límites y MFA | Límites estrictos, MFA para importes superiores a USD 1.000 |
| Configuración de límites | Panel de ajustes del usuario |
| Frecuencias recurrentes | Diaria, semanal y mensual |
| MFA recurrente | PIN al crear la programación; límites comprobados en ejecución |
| Fallos recurrentes | Registrar el fallo y avanzar a la siguiente fecha |

Además de estas decisiones, se registraron dos aprobaciones:

1. Confirmación del resumen de requisitos.
2. Aprobación de las especificaciones para comenzar la implementación.

En total, se observaron 16 respuestas mediante la interfaz `Ask User`.

No se midió el tiempo humano de revisión.

## 4. Especificaciones

Tras activar `spec-writer`, el agente generó tres nuevas especificaciones:

- `specs/ach_transfers.spec.md`.
- `specs/recurring_payments.spec.md`.
- `specs/transfer_limits.spec.md`.

También extendió `specs/transfers.spec.md` para incorporar los límites dinámicos a las transferencias internas.

El inventario resultante pasó de cuatro a **siete archivos de especificación**.

Las operaciones iniciales reportaron 137 líneas para ACH, 112 para pagos recurrentes, 71 para límites dinámicos y dos líneas agregadas a transferencias internas.

Posteriormente, durante `spec-verification`, el agente ajustó las rutas de archivos objetivo declaradas en las especificaciones ACH y de pagos recurrentes. Estos ajustes se realizaron después de la aprobación humana y fueron de trazabilidad técnica; no se observó una segunda aprobación específica de esas modificaciones.

El número final de líneas, caracteres, hashes y requisitos aún no fue medido independientemente.

## 5. Implementación del backend

Se observaron modificaciones y creaciones en los siguientes componentes.

### Modelos y contratos

- `backend/app/models.py`: modelos de beneficiarios, límites de transferencia y programaciones recurrentes; ampliación de transferencias y transacciones.
- `backend/app/schemas.py`: contratos de entrada y salida, validaciones bancarias y nuevas respuestas.

### Servicios

- `account_service.py`: inicialización de límites predeterminados.
- `transfer_service.py`: transferencias internas con límites y nuevas transferencias ACH.
- `limit_service.py`: consulta, actualización y validación de límites.
- `recurring_service.py`: programación y ejecución de pagos recurrentes.
- `scheduler.py`: procesamiento automático de operaciones pendientes y programadas.

### Rutas y aplicación

- `routers/transfers.py`: incorporación de transferencias ACH.
- `routers/beneficiaries.py`: administración de beneficiarios.
- `routers/limits.py`: consulta y configuración de límites.
- `routers/recurring.py`: creación, consulta, pausa, reanudación y cancelación de programaciones.
- `main.py`: incorporación de nuevas rutas y activación del planificador durante el ciclo de vida de la aplicación.

Los valores predeterminados de los límites fueron USD 5.000 por transacción y USD 10.000 diarios.

La solución utiliza operaciones ACH simuladas y no integra redes bancarias reales.

## 6. Implementación del frontend

Se observaron cambios en:

- `frontend/src/api/types.ts`.
- `frontend/src/api/client.ts`.
- `frontend/src/components/TransferModal.tsx`.
- `frontend/src/components/TransferLimits.tsx`.
- `frontend/src/components/RecurringPayments.tsx`.
- `frontend/src/components/TransactionHistory.tsx`.
- `frontend/src/components/Navbar.tsx`.
- `frontend/src/App.tsx`.

La interfaz resultante permite, según el informe del agente:

- Seleccionar transferencias internas o ACH.
- Seleccionar o registrar beneficiarios externos.
- Configurar límites de transferencia.
- Crear y administrar pagos recurrentes.
- Mostrar estados de operaciones ACH.
- Integrar la verificación MFA en los nuevos flujos.

Estos comportamientos todavía no habían sido validados manualmente en el navegador al cierre de la transcripción.

## 7. Pruebas automatizadas

El agente creó los archivos:

- `backend/tests/test_ach_transfers.py`.
- `backend/tests/test_recurring_payments.py`.
- `backend/tests/test_transfer_limits.py`.
- `frontend/src/__tests__/TransferLimits.test.tsx`.
- `frontend/src/__tests__/RecurringPayments.test.tsx`.

También modificó las pruebas existentes de `TransferModal`.

### Resultados finales reportados

| Indicador | Línea base | Etapa 2 | Cambio |
|---|---:|---:|---:|
| Backend | 22 | 35 | +13 |
| Frontend | 23 | 31 | +8 |
| Total | 45 | 66 | +21 |

La última ejecución de Pytest informó **35 pruebas aprobadas y una advertencia**.

La última ejecución de Vitest informó **31 pruebas aprobadas**, distribuidas en seis archivos.

El comando `npm --prefix frontend run build` completó correctamente la compilación TypeScript y Vite.

No se generaron métricas de cobertura de código.

## 8. Verificación del flujo SDD

Durante la ejecución se observaron las cuatro habilidades principales de Tessl:

1. `requirement-gathering`.
2. `spec-writer`.
3. `spec-verification`.
4. `work-review`.

La secuencia general respetó la aprobación de requisitos y especificaciones antes de la implementación.

Sin embargo, la solicitud inicial pedía detenerse después de la primera pregunta de aclaración. En la práctica, la sesión continuó automáticamente a través de la entrevista completa, generación de especificaciones, aprobación e implementación.

Esta diferencia entre el control secuencial previsto y la ejecución real debe conservarse como observación metodológica.

## 9. Base de datos y estado del proyecto

El agente ejecutó las pruebas, consultó el estado de Git y eliminó posteriormente el archivo local `shift_bank.db` si existía.

La base SQLite era un artefacto mutable excluido de la copia inicial de la línea base. No obstante, la eliminación constituye una acción observada sobre el estado local del proyecto y debe quedar registrada.

La transcripción no proporciona un diff Git completo y fiable respecto de los 66 archivos iniciales.

Por ello, las cifras exactas de líneas añadidas, modificadas y eliminadas no se consolidan todavía. Se calcularán posteriormente comparando el estado final con el manifiesto de Etapa 2.

## 10. Aspectos pendientes de verificación

Antes de cerrar la Etapa 2 es necesario:

1. Recuperar las estadísticas de consumo de la sesión Gemini.
2. Ejecutar una auditoría de cumplimiento de los requisitos heredados y nuevos.
3. Medir especificaciones, código, pruebas y cambios respecto de la línea base.
4. Verificar el planificador automático, la persistencia y las transiciones de estado.
5. Comprobar manualmente las tres funcionalidades nuevas.
6. Ejecutar SonarQube en un proyecto independiente de la Etapa 1.
7. Registrar defectos, limitaciones y eventuales correcciones humanas.

Las pruebas automatizadas aprobadas no constituyen, por sí solas, evidencia de ausencia de defectos funcionales o de concurrencia.

## 11. Resultado del checkpoint

El agente reportó la implementación completa de las tres capacidades previstas para la Etapa 2, integradas con la aplicación heredada.

Se observaron 66 pruebas automatizadas aprobadas y una compilación de producción exitosa.

El checkpoint de implementación inicial se considera completado en términos de entrega del agente, pero **la Etapa 2 experimental permanece abierta** hasta finalizar la auditoría, las métricas y las pruebas manuales.

Las conclusiones de etapas anteriores no se modifican retroactivamente.