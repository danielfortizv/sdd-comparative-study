# Bitácora — Etapa 4, Iteración 3

**Fecha:** 18 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** Spec-Driven Development (SDD) nativo  
**Fase:** M0 — Baseline y preparación; M1 — Implementación inicial.

### Actividades realizadas

Se ejecutó la línea base funcional de la implementación heredada de Etapa 3. Se configuraron dependencias aisladas, se crearon directorios de evidencia y se registraron los datos iniciales de consumo de la nueva cuenta de Kiro.

Se validaron las condiciones de aprobación del gate G-SPEC (T4).

Posteriormente, se inició M1 mediante la implementación del motor de conversión FX, con aritmética racional exacta y reglas de redondeo HALF_UP.

### Resultados

- Regresión backend heredada: 372 pruebas aprobadas.
- Pruebas frontend Vitest: 3 aprobadas.
- Build frontend: exitoso, 41 módulos transformados.
- Nuevas pruebas FX: 10 aprobadas.
- Regresión backend posterior: 382 pruebas aprobadas.
- Tareas principales marcadas como completadas: 4/31.
- Tarea 7: validación funcional reportada, pendiente actualización del estado SDD.

### Observaciones

Se observó una diferencia entre la versión de Node.js utilizada en la preparación previa (24.19.0) y la ejecución actual de Kiro (20.17.0).

Las tasas simuladas propuestas para FX coinciden con la tabla oficial D-03, por lo que pueden conservarse.

### Evidencia

Registros de baseline, pruebas, entorno y D1 en `Etapa 4/_experiment_logs/Kiro/E4/`, según las rutas reportadas por Kiro.

### Consumo

- Línea base inicial: 30,24 créditos utilizados de 1.000.
- Consumo específico de esta iteración: N/D.
- Duración y llamadas a herramientas: N/D hasta recuperar telemetría original.

### Siguiente actividad

Completar T5 y T6 para la migración de cuentas y la inicialización controlada de datos experimentales; verificar el cierre de T7 y continuar con los hitos posteriores mediante Run All Tasks.

# Bitácora — Etapa 4, Iteración 4

**Fecha:** 18 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** Spec-Driven Development (SDD) nativo  
**Fase:** M1 — Migración multimoneda y motor FX  
**Avance:** 7/31 tareas principales (22,58 %).

### Actividades realizadas

Se implementó la evolución del esquema SQLite para incorporar identificadores públicos de cuentas, monedas y versiones, junto con las estructuras iniciales necesarias para Event Sourcing, CQRS e idempotencia.

Se creó un fixture experimental para las cuatro cuentas definidas en D-02, preservando el escenario anterior de Etapa 3.

Se completó el motor de conversión FX utilizando tasas racionales exactas y redondeo HALF_UP.

### Resultados

- Pruebas FX: 11 aprobadas.
- Pruebas de migración: 25 aprobadas.
- Pruebas del esquema E4: 7 aprobadas.
- Pruebas del fixture: 4 aprobadas.
- Regresión backend completa: 394 aprobadas, código de salida 0.

### Decisiones técnicas

Se adoptó una estrategia de fixtures separados para preservar las pruebas heredadas de Etapa 3 y evaluar independientemente el escenario multimoneda de Etapa 4.

Esta estrategia exige diferenciar las pruebas de compatibilidad heredada de las pruebas de aceptación funcional de E4.

### Incidentes y correcciones

La sustitución inicial del fixture produjo 78 fallos en pruebas heredadas. Kiro identificó las dependencias respecto a los saldos COP y corrigió el aislamiento de los entornos de prueba, recuperando el estado satisfactorio de la regresión.

### Evidencia

- `E4_Iteracion_01.md`, generado por Kiro.
- Registros de pruebas de migración, FX y regresión.
- `tasks.md` y `tasks.meta.json` actualizados.

### Métricas D1

Consumo de créditos, tiempo de ejecución, tokens y llamadas a herramientas: N/D hasta recuperar la telemetría correspondiente.

### Siguiente actividad

Implementar el almacén de eventos de dominio (T8), las proyecciones CQRS (T9) y la envoltura transaccional atómica de comandos (T10), continuando con el plan completo de implementación.

# Bitácora — Etapa 4, Iteración 5

**Fecha:** 18 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** Spec-Driven Development (SDD) nativo  
**Fases:** M2 — Event Sourcing y CQRS; M3 — Idempotencia y concurrencia.  
**Avance:** 11/31 tareas principales (35,48 %).

### Actividades realizadas

Se implementó el almacenamiento de eventos de dominio mediante `app/events.py`, separado del sistema de auditoría heredado.

Se desarrolló `app/projections.py` para mantener proyecciones de cuentas y reconstruirlas determinísticamente mediante reproducción de eventos.

Se implementó `app/command.py`, que agrupa las actualizaciones financieras, eventos, proyecciones, auditoría y versiones dentro de una operación transaccional.

Finalmente, se desarrolló `app/idempotency.py`, incorporando identificación de solicitudes repetidas, detección de reutilización de claves con diferentes cargas y control optimista de versiones.

### Pruebas y resultados

- Event Store: 4 aprobadas.
- Proyecciones CQRS: 4 aprobadas.
- Atomicidad de comandos: 3 aprobadas.
- Idempotencia y concurrencia: 5 aprobadas.
- Regresión backend completa: 410 aprobadas, código de salida 0.

### Verificaciones relevantes

Se comprobó que los reintentos idempotentes no duplican efectos, que los conflictos de versión producen respuestas 409 y que el reintento de una operación previamente confirmada se evalúa antes de la versión de la cuenta.

También se verificó el rollback ante fallos inyectados y la reconstrucción determinista de las proyecciones.

### Incidentes y limitaciones

No se reportaron bloqueos técnicos. La integración de estos componentes con transferencias, conversiones y demás operaciones bancarias continúa pendiente.

### Evidencia

`E4_Iteracion_02.md`, `E4_Iteracion_03.md`, `tasks.md` y `tasks.meta.json`, además de los resultados de pruebas registrados por Kiro.

### Métricas D1

Créditos consumidos, tiempo de ejecución y llamadas a herramientas: N/D hasta revisar la telemetría de la sesión.

### Siguiente actividad

Implementar M4 (T12–T15), integrar los contratos multimoneda en las operaciones bancarias y continuar con el resto de tareas mediante el flujo nativo de Kiro.

# Bitácora — Etapa 4, Iteración 6

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** SDD nativo  
**Fases:** M4 — Operaciones multimoneda; M5 — Frontend.  
**Avance:** 17/31 tareas principales (54,84 %).

### Actividades realizadas

Se implementaron endpoints de conversión de divisas y transferencias internas con soporte de idempotencia, control de versiones y restricciones de moneda.

Se incorporaron funciones para la validación de límites monetarios expresados en USD equivalente y reglas de moneda para ACH y pagos recurrentes.

En frontend, se desarrollaron utilidades para representar monedas, un cliente API para operaciones multimoneda, un dashboard y un formulario de conversión. Los nuevos componentes fueron integrados en la aplicación React.

### Resultados

- Pruebas backend acumuladas: 428 aprobadas.
- Vitest frontend: 14 aprobadas.
- Build de producción: exitoso, 45 módulos.
- Se verificaron conversiones, reintentos idempotentes, conflictos de versión y rechazo de transferencias entre monedas diferentes.

### Incidentes

Se corrigió un error en un literal SQL utilizado en pruebas. También se detectó que los componentes React nuevos inicialmente no estaban incluidos en el bundle de producción, situación corregida mediante su integración en App.tsx.

### Limitaciones pendientes de verificación

No se evidenció aún la aplicación completa del flujo MFA en los endpoints nuevos ni la invocación efectiva de las restricciones de moneda en los servicios ACH y recurrentes. Se requiere verificación integrada antes del escaneo SonarQube PRE.

### SonarQube

Proyecto de Etapa 4 identificado: Shift-Bank---Stage-4---Kiro. No se ha ejecutado el análisis PRE ni POST.

### Evidencia

Archivos generados por Kiro: E4_Iteracion_04.md y E4_Iteracion_05.md, junto con resultados de pruebas y estado actualizado del plan SDD.

### Consumo y esfuerzo

Créditos consumidos, duración y llamadas a herramientas: N/D hasta extracción de la telemetría original.

### Siguiente actividad

Completar verificaciones e integración funcional pendientes, continuar T18–T27, ejecutar las pruebas planificadas y detener la ejecución en T28 para medir SonarQube PRE.

# Bitácora — Etapa 4, Iteración 7

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** SDD nativo  
**Fase:** M6 — Verificación funcional, rendimiento y despliegue.

### Actividades realizadas

Se completó la integración de la autenticación multifactor en los endpoints multimoneda y se incorporaron las restricciones de moneda en los servicios reales ACH y recurrentes.

Se ejecutaron pruebas de atomicidad, concurrencia, Event Sourcing, reconstrucción CQRS y regresión funcional.

También se implementó una verificación determinista de invariantes bajo operaciones simuladas y se validó la estructura Docker Compose.

### Resultados

- Regresión backend: 444 pruebas aprobadas.
- Cobertura backend: 94 %.
- Vitest: 14 pruebas aprobadas.
- Cobertura frontend: 7,24 %.
- Build frontend: exitoso.
- Configuración Docker Compose: válida.
- Benchmark Locust real: no ejecutado.
- Despliegue Docker y pruebas HTTPS reales: no ejecutados.

### Hallazgos

Kiro había dado por completadas T14 y T15 antes de demostrar la integración efectiva de sus validaciones. Ambas tareas fueron reabiertas, corregidas y verificadas con pruebas de integración.

Se identificó además que T24 se encontraba marcada como completada pese a no haber ejecutado el benchmark real planificado. T25 seguía parcialmente ejecutada.

### Estado

25 tareas marcadas en el plan, pero 24 consideradas plenamente verificadas, sujetas a conciliación de T24. T25 continúa pendiente.

### Evidencia

`E4_Iteracion_06.md`, resultados de pruebas y cobertura, configuración SonarQube de E4 y registros de validación de Docker Compose.

### Consumo D1

Sin nueva medición verificada de créditos, tiempos o llamadas a herramientas. Se mantienen como N/D.

### Siguiente actividad

Ejecutar el benchmark Locust real y el despliegue Docker completo, recopilar evidencia y posteriormente iniciar el análisis SonarQube PRE.

Fecha: 19 de noviembre de 2026
Herramienta: Kiro
Metodología: Spec-Driven Development
Fase: M6 — Benchmark y despliegue
Avance: 26/31 tareas principales (83,87 %).
Actividades
Se ejecutó el benchmark Locust sobre un servidor HTTP real con base de datos sintética aislada y operaciones multimoneda.

Posteriormente, se construyó y levantó el despliegue Docker Compose con backend FastAPI y frontend Nginx. Se ejecutaron verificaciones de HTTPS, proxy, persistencia, auditoría y configuración fail-closed.
Resultados
- Locust: 8.409 solicitudes, 0 fallidas.
- Distribución aproximada de tráfico: 60 % cuentas, 30 % historial y 10 % operaciones financieras.
- p95 lecturas: 53 y 61 ms.
- p95 operaciones: 73 y 71 ms.
- Throughput: aproximadamente 128,7 solicitudes/s.
- Verificación posterior de invariantes: aprobada en una ejecución HTTP adicional.
- Docker: dos servicios saludables.
- HTTPS y conversión multimoneda: verificadas.
- Persistencia y auditoría después del reinicio: verificadas.
- Configuración sin claves: arranque rechazado.
Incidentes
Se presentaron dificultades con OpenSSL en Windows, la codificación cp1252 y la ejecución de comandos PowerShell. Kiro corrigió los problemas y conservó evidencia de los intentos.
Evidencias
Registros de carga, despliegue y respuestas HTTP en Etapa 4/_experiment_logs/Kiro/E4/.

Bitácora automática: E4_Iteracion_07.md.
Métricas de esfuerzo D1
Créditos utilizados durante esta iteración, duración atribuible a Kiro y llamadas a herramientas: N/D hasta exportar la sesión y recuperar su telemetría.
Siguiente actividad
Ejecutar SonarQube PRE, conservar resultados originales, revisar los hallazgos y aprobar la ronda correctiva antes del escaneo POST.

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** SonarScanner / SonarQube  
**Fase:** T27 — Análisis de calidad PRE.  
**Avance:** 26/31 tareas principales completadas.

**Actividad:** Se ejecutó SonarScanner CLI 8.1.0 sobre el proyecto de Etapa 4 de Kiro, utilizando los reportes de cobertura backend y frontend.

**Resultado:** Escaneo finalizado correctamente, código de salida 0. Se indexaron 103 archivos y se envió el informe al servidor SonarQube 26.9.0.

**Evidencia:** `20261119-004700_T27_PRE_scanner.log`.

**Identificador CE:** `c69bea55-1738-4d87-a4ca-26e169a4934d`.

**Incidentes:** PowerShell interpretó incorrectamente bloques `elseif` y `else` copiados por separado. El scanner terminó exitosamente, pero aún se requiere verificar las métricas de cobertura procesadas.

**Estado:** Análisis enviado; pendiente verificar procesamiento del servidor, exportar métricas y aprobar T28.

**Consumo D1:** N/D. No se realizó implementación adicional.

**Siguiente actividad:** Exportación autenticada del análisis PRE y revisión de problemas antes de autorizar las correcciones.

# Bitácora — Etapa 4: Revisión SonarQube PRE

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** Kiro y SonarQube 26.9.0  
**Metodología:** SDD nativo  
**Fase:** T27 — Análisis PRE; T28 — Revisión investigadora.  
**Avance:** 27/31 tareas principales (87,10 %).

### Actividades realizadas

Se verificó el procesamiento exitoso del análisis SonarQube PRE, identificado con `cd37bcc9-6884-4dd4-a92a-d4e8f374cb62`.

Se recuperaron las métricas de calidad, los problemas detectados, el Quality Gate y las evidencias de importación de cobertura. La exportación contiene 162 problemas, coincidentes con el total reportado por SonarQube.

### Resultados

Se identificaron 161 code smells y una vulnerabilidad, sin bugs según la clasificación tradicional. La cobertura global fue del 49,7 %, la duplicación del 0 % y la deuda técnica estimada de 783 minutos.

El Quality Gate fue OK, aunque sin condiciones configuradas.

Se identificó una diferencia entre el modelo tradicional de fiabilidad, calificado A, y el modelo MQR, calificado D. Ambas mediciones se conservarán para el análisis comparativo.

### Decisión investigadora

Se autoriza una única ronda correctiva dirigida a la vulnerabilidad detectada y a problemas de mantenibilidad que puedan corregirse sin alterar los contratos funcionales.

La configuración de análisis, las exclusiones, el alcance de cobertura y las especificaciones aprobadas deberán mantenerse estables para garantizar comparabilidad entre PRE y POST.

### Evidencia

Exportación de SonarQube PRE bajo `_experiment_logs/Kiro/E4/sonarqube/`, archivos de cobertura, registro del scanner y bitácora `E4_Iteracion_08.md`.

### Consumo D1

Créditos, tiempo atribuido a Kiro y llamadas a herramientas: N/D hasta consolidar la telemetría de la sesión.

### Siguiente actividad

Ejecutar T29, verificar las regresiones y preparar el escaneo SonarQube POST sin ejecutarlo hasta la aprobación correspondiente.

# Bitácora — Etapa 4, Iteración 10

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** Kiro  
**Metodología:** SDD nativo  
**Fase:** M7 — Corrección de calidad estática (T28–T29)  
**Avance:** 29/31 tareas principales (93,55 %).

### Actividades realizadas

Se aprobó el análisis SonarQube PRE y se ejecutó una única ronda correctiva, concentrada en la seguridad de la generación de identificadores de idempotencia y en mejoras de mantenibilidad de componentes React correspondientes a Etapa 4.

Se reemplazó la generación insegura de UUID basada en `Math.random()` por mecanismos criptográficamente seguros. También se modificaron las propiedades de dos componentes React para declararlas de solo lectura.

### Resultados

- Regresión backend: 444 pruebas aprobadas.
- Vitest frontend: 14 pruebas aprobadas.
- Build frontend: exitoso, 45 módulos.
- Coberturas backend y frontend: regeneradas.
- Vulnerabilidad S2245: corregida en código, pendiente confirmar en SonarQube POST.
- Dos hallazgos S6759: corregidos en código.

### Decisiones y limitaciones

Se conservaron sin modificación 124 hallazgos relacionados con reglas de estilo de pruebas Python heredadas, al considerar que su corrección masiva no justificaba el riesgo de modificar las pruebas históricas.

No se modificaron las exclusiones, el Quality Gate ni las especificaciones SDD aprobadas.

### Evidencias

`T29_CORRECTIVE_RECORD.md`, resultados de regresión y cobertura, y bitácora automática `E4_Iteracion_09.md`.

### Métricas D1

Consumo de créditos, tiempo de implementación y llamadas a herramientas: N/D hasta recuperar la telemetría original.

### Siguiente actividad

Ejecutar SonarQube POST, comparar resultados con PRE y completar la consolidación experimental de T30 y T31.

# Bitácora — Etapa 4, Iteración 11

**Fecha:** 19 de noviembre de 2026  
**Herramienta:** Kiro y SonarQube 26.9.0  
**Metodología:** Spec-Driven Development nativo  
**Fase:** M7 — Verificación POST y aprobación de cierre  
**Avance previo al cierre:** 29/31 tareas principales (93,55 %).

### Actividades realizadas

Se verificó el análisis SonarQube POST y se compararon sus resultados con la medición PRE. Se confirmó que ambos análisis utilizaron la misma configuración y metodología de cobertura.

Se revisaron los problemas resueltos, las métricas tradicionales y MQR, la deuda técnica, la cobertura y las calificaciones de calidad.

### Resultados

Se redujeron los problemas detectados de 162 a 158. La vulnerabilidad de seguridad registrada en PRE fue corregida y confirmada como resuelta mediante SonarQube.

La calificación de seguridad MQR mejoró de C a A, mientras que la fiabilidad MQR pasó de D a C. La deuda técnica se redujo de 783 a 768 minutos.

La cobertura global se mantuvo aproximadamente estable, disminuyendo de 49,7 % a 49,6 %. No se reportaron nuevos problemas.

### Observaciones metodológicas

La mejora de calidad se obtuvo mediante una ronda correctiva acotada, sin modificar las especificaciones SDD ni las exclusiones de análisis.

El Quality Gate permaneció en estado OK, pero sin condiciones configuradas.

El script PowerShell presentó un error durante la elaboración de su resumen final; sin embargo, el scanner finalizó satisfactoriamente y Kiro pudo recuperar los resultados exportados.

### Evidencias

- SonarQube PRE: análisis `cd37bcc9-6884-4dd4-a92a-d4e8f374cb62`.
- SonarQube POST: análisis `bb7434e4-29e5-424e-8799-8f2c8b1cc936`.
- Bitácora automática `E4_Iteracion_10.md`.
- Exportaciones y registros en `_experiment_logs/Kiro/E4/sonarqube/`.

### Decisión investigadora

Se aprueba T30 y se autoriza la consolidación documental final T31.

### Siguiente actividad

Generar los informes consolidados de Etapa 4, verificar la trazabilidad de las 31 tareas y recuperar las métricas de consumo disponibles para el análisis comparativo del proyecto de grado.

