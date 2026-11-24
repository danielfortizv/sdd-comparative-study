# Recuperación de métricas D1 de Kiro — Shift Bank, Etapas 1–3

**Fecha de análisis:** 17 de noviembre de 2026.  
**Fuentes:** tres exportaciones nativas de sesiones Kiro en ZIP, aportadas por el investigador, y *Guía de Estandarización de Reporte de Datos* (28 de octubre de 2026), pp. 1–5.  
**Objetivo:** cuantificar esfuerzo y consumo sin inferir créditos, tokens ni tiempos ausentes.

## 1. Resultado de la extracción

| Métrica (definición de este extractor) | E1 | E2 | E3 |
|---|---:|---:|---:|
| Sesiones ZIP con actividad de la etapa | N/D | 3 | 1 |
| Turnos humanos (mensajes del usuario a Kiro) | N/D | 39 | 15 |
| **Msgs**: eventos `user` + `assistant`, principal y subagentes | N/D | **1.636** | **2.477** |
| Mensajes de asistente principal, sin subagentes | N/D | 776 | 494 |
| Mensajes de asistente de subagentes | N/D | 821 | 1.968 |
| **Tool Calls**: eventos `tool_call`, principal y subagentes | N/D | **1.113** | **1.816** |
| Tool Calls de sesión principal | N/D | 501 | 459 |
| Tool Calls de subagentes | N/D | 612 | 1.357 |
| Subagentes despachados | N/D | 23 | 36 |
| Solicitudes de aprobación de herramientas | N/D | 203 | 368 |
| Respuestas a solicitudes de aprobación | N/D | 203 | 367 |
| Resultados de herramientas con `success=false` | N/D | 15 | 52 |
| **Créditos Kiro recuperados** | N/D | **383,359732** | **≥201,929535** |
| **Tiempo reportado por Kiro (segundos)** | N/D | **13.379,421** | **≥12.417,229** |
| Turnos con resumen de uso / turnos totales | N/D | 39/39 | 14/15 |

**Nota:** E2 tiene cobertura íntegra de `usage_summary` para los 39 turnos que aparecen en los ZIP aportados; esto no demuestra que no existan otras sesiones E2 no exportadas. En E3, las cifras de créditos y tiempo son límites inferiores observados, no totales cerrados.

## 2. Asignación correcta de las tres exportaciones

Las exportaciones **no** son una por etapa:

1. `sess_89c2c877-…`: 33 turnos, todos de **Etapa 2** (preparación, requisitos, diseño, plan e implementación hasta el traspaso de tareas).
2. `sess_2cd5be7f-…`: 4 turnos, todos de **Etapa 2** (tareas 27–30 de pagos recurrentes).
3. `sess_7f1b54d0-…`: 17 turnos; los **2 primeros** son E2 (finalización de tareas y pasada correctiva Sonar), y los **15 siguientes** son **Etapa 3** (descubrimiento, Specs, implementación y cierre).

No se suministró ningún ZIP con la conversación de **Etapa 1**. Sus valores se marcan **N/D**, no cero. Los números ilustrativos de la plantilla de estandarización **no se utilizan** como observaciones del proyecto.

## 3. Crédito y tiempo: hallazgo crítico de E3

El turno 12 de la tercera sesión, iniciado el **16 de noviembre de 2026 a las 20:33:19 UTC**, contiene el mandato de aprobar el plan y ejecutar `Run all Tasks`. El exportador registra:

- **996 llamadas a herramientas** dentro de ese turno (sesión principal + subagentes).
- Cierre `stopReason=cancelled` (recuperado por el exportador) el 17 de noviembre a las 16:05:13 UTC.
- **Ningún evento `usage_summary`** para el turno, por lo que no están disponibles ni sus créditos ni su `elapsedTime`.

El intervalo de reloj de ese turno abarca múltiples horas; **no puede sustituir al tiempo activo de procesamiento**: podría incluir pausas, esperas, interrupciones y actividad solapada de subagentes. Tampoco se permite estimar créditos a partir de las 996 llamadas, porque las llamadas tienen costes distintos.

Por tanto, **201,93 créditos y 12.417,23 s en E3 son mínimos recuperados**. El consumo real de E3 necesariamente puede ser mayor. El saldo de créditos mencionado en una conversación no reemplaza un registro de consumo por turno ni permite calcular el faltante sin conocer recargas y periodos de facturación.

## 4. Definiciones operativas y limitaciones de comparabilidad

- **`Msgs`**: conteo de eventos JSONL `payload.type` igual a `user` o `assistant`, incluyendo mensajes de subagentes y fragmentos internos de razonamiento. **No es la cantidad de preguntas humanas.** Para distinguir ambas, se reporta por separado el conteo de mensajes `user` de la sesión principal.
- **`Tool Calls`**: conteo de eventos `payload.type=tool_call`, tanto en `messages.jsonl` como en `sub-executions/*.jsonl`. No se cuentan `tool_result` como una segunda llamada.
- **`Cred`**: suma decimal de `usage` con `unit=credit` dentro de `promptTurnSummaries` en los eventos `usage_summary`. Los turnos sin este evento se dejan como faltantes, nunca como cero.
- **`Tiempo (s)`**: suma de `elapsedTime / 1000` de esos mismos `usage_summary`. Es el tiempo reportado por Kiro, no la suma de intervalos de reloj entre la primera y la última intervención.
- **Tokens (Tok In, Tok Cache, Tok Out)**: **N/A para Kiro**, según la tabla D1 de la guía. `session_metadata.contextUsage` contiene porcentajes de contexto, no una desagregación acumulada de tokens facturados.
- **`Costo ($)`**: **N/D**. Los ZIP no informan el costo monetario real ni una tarifa efectiva. La guía contiene una cifra de ejemplo, pero no basta para declarar una factura real. Si el estudio adopta una tasa explícita en USD/crédito, el cálculo debe etiquetarse como estimación.
- **Aprobaciones**: `pending_interaction` y `interaction_resolved` cuantifican eventos de solicitud/resolución; no demuestran por sí solos que haya ocurrido una aprobación manual individual.
- **Errores de herramientas**: los eventos `tool_result.success=false` no son equivalentes a fallos funcionales del banco; pueden corresponder a comandos, permisos o pruebas negativas.

La metodología de conteo `Msgs` debe aplicarse consistentemente a las demás herramientas del estudio; si esas exportaciones no desglosan subagentes, conviene presentar también la métrica **solo sesión principal**. E2 tiene **815 mensajes principales** (39 usuario + 776 asistente); E3 tiene **509** (15 usuario + 494 asistente).

## 5. Cambios E2 → E3 que sí son directamente observables

- Mensajes registrados en principal y subagentes: 1.636 → 2.477 (**+51,41 %**).
- Llamadas a herramientas: 1.113 → 1.816 (**+63,16 %**).
- Prompts humanos: 39 → 15 (**−61,54 %**), consecuencia compatible con la mayor delegación y `Run all Tasks`, sin demostrar causalidad por sí sola.
- Créditos y tiempo: **no calcular variaciones E2→E3 como valores definitivos**, dado que E3 carece del resumen del turno de mayor actividad.

## 6. Archivos y auditoría

El libro Excel `Metricas_D1_Kiro_Etapas_1_2_3.xlsx` contiene: resumen, detalle por turno, distribución de herramientas, manifiesto SHA-256 de ZIPs y desglose operativo. Los CSV replican los datos de base. El script `extraer_kiro_d1.py` reproduce la extracción desde los tres ZIP originales sin exportar mensajes, argumentos, resultados, tokens de autenticación ni secretos.

Para completar **E1**, solicitar la exportación nativa de sus sesiones. Para completar **créditos/tiempo de E3**, será necesaria otra fuente de consumo del turno cancelado (historial de facturación/telemetría interna de Kiro, si existe), ya que no se puede reconstruir exactamente del JSONL disponible.
