# Telemetría recuperada de Codex — Shift Bank, Etapa 4, Spec Kit

**Fecha de extracción:** 2026-11-16T10:55:24.8914210-05:00  
**Fuente:** `CODEX_SPECKIT4_TELEMETRIA_V2.json`  
**Cobertura del extractor:** 11 archivos `rollout-*.jsonl` descubiertos, 0 ilegibles y 1 sesión(es) cuyo `session_meta.cwd` inicial coincide con `Etapa 4`. Esto **no prueba** que las demás sesiones no contengan actividad relacionada si se inició Codex desde otro directorio.

## D1 — Esfuerzo y consumo del agente

| Indicador | Valor observado |
|---|---:|
| Sesiones identificadas bajo el filtro | 1 |
| ID de sesión | `01a1e3de-8e7a-7d90-b663-dffaba067317` |
| Inicio (hora de Bogotá, UTC-5) | 2026-11-16 05:19:41 |
| Último evento (hora de Bogotá, UTC-5) | 2026-11-16 10:14:22 |
| Tiempo transcurrido entre eventos | 294.69 minutos (aprox. 4 h 54 min 41 s) |
| Modelo registrado | `gpt-6-luna` |
| Razonamiento | `medium` |
| Codex CLI | `0.168.0` |
| Tokens de entrada acumulados | 105.024.622 |
| Tokens de entrada en caché | 103.443.456 |
| Tokens de entrada sin caché (diferencia) | 1.581.166 |
| Proporción de entrada desde caché | 98.49% |
| Tokens de salida acumulados | 485.334 |
| Tokens de razonamiento (subconjunto de salida) | 204.528 |
| Tokens totales reportados | 105.509.956 |
| Llamadas a herramientas (`response_item`) | 709 |
| Inicios de turno (`task_started`) | 12 |
| Eventos contadores de tokens | 730 |
| Líneas JSON ilegibles | 0 |
| Costo monetario real | N/D |

**Método:** se conserva el último `total_token_usage` observado por sesión. Los tokens de razonamiento **no** se agregan nuevamente al total porque están incluidos en los tokens de salida. Los tokens sin caché se calculan como entrada total menos entrada desde caché. La duración es el intervalo entre el primer y el último evento del archivo, por lo que puede incluir pausas o tiempo inactivo; no se debe interpretar como tiempo efectivo de cómputo.

## D5 — Intervención humana (indicadores indirectos)

| Indicador | Valor registrado | Interpretación |
|---|---:|---|
| Mensajes de rol `user` en `response_item` | 33 | Mensajes registrados; no necesariamente 33 intervenciones humanas independientes |
| Eventos `event_msg.user_message` | 0 | Cero en este formato de log, no cero intervenciones reales |
| Inicios de turno | 12 | Actividad del agente, no necesariamente nuevas instrucciones del investigador |
| Llamadas a herramientas | 709 | Actividad de herramientas, no cuenta decisiones humanas |
| Aprobaciones de permisos, Gate A/B y correcciones solicitadas | N/D en este extractor | Requiere cruce con bitácora y transcripciones |

## Alcance y limitaciones

1. Se encontraron 11 archivos de sesiones de Codex; se pudieron leer todos, pero solo 1 tenía como directorio inicial `Etapa 4`. No deben sumarse automáticamente los demás archivos. Conviene comprobar sus `session_meta.cwd` antes de afirmar exhaustividad de todas las sesiones de la etapa.
2. La cifra de 105.509.956 tokens corresponde a una sola sesión identificada y es un valor **acumulado**, no la suma de los 730 eventos de contadores. No debe volver a agregarse a cifras de los hitos si provienen del mismo registro.
3. El costo en USD/COP, la cantidad precisa de aprobaciones humanas y la invocación explícita de habilidades `$speckit-*` no se deducen del resumen.
4. Para comparaciones D1 con otras herramientas SDD, aplicar el mismo criterio de selección de sesiones, extracción de tokens, tiempo transcurrido, interacciones y tratamiento de caché.
5. El archivo exportado contiene un identificador de sesión y nombre de registro, pero no los contenidos de prompts/respuestas ni credenciales.

## Redacción académica sugerida

En la etapa de implementación con GitHub Spec Kit y Codex CLI se recuperó una sesión de agente mediante la lectura de registros JSONL. Para dicha sesión se observó el modelo `gpt-6-luna` con esfuerzo de razonamiento `medium`, 105.509.956 tokens acumulados (105.024.622 de entrada y 485.334 de salida). De los tokens de entrada, 98.49% estaban asociados al uso de caché. Se registraron 709 llamadas a herramientas y un intervalo de 294.69 minutos entre el primer y el último evento. Las cifras representan telemetría observada, no costo facturado ni tiempo activo. La identificación de una sola sesión depende del directorio de trabajo inicial y puede requerir verificación de otras sesiones iniciadas desde directorios diferentes. Los conteos de mensajes se consideran indicadores indirectos y no equivalen automáticamente a intervenciones humanas independientes.
