# Tessl — Etapa 2 — Telemetría de la sesión de implementación

## 1. Identificación

- Proyecto: Shift Bank.
- Etapa: 2 — Brownfield inicial.
- Herramienta SDD: Tessl.
- Agente: Gemini CLI.
- Fecha: 13 de noviembre de 2026.
- Session ID: `42bc44ee-b2c5-4042-8524-a249ef3b692f`.
- Autenticación: Vertex AI.
- Fuente: Comandos `/stats session`, `/stats model`, `/stats tools` y `/quit`.

## 2. Consumo de modelos

| Modelo | Solicitudes | Tokens de entrada totales | Caché | Salida |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | 94 | 9.990.626 | 9.583.054 | 56.122 |
| Gemini 3 Flash Preview | 5 | 95.780 | 0 | 675 |
| Gemini 3.5 Flash Lite | 1 | 274 | 0 | 8 |
| **Total** | **100** | **10.086.680** | **9.583.054** | **56.805** |

Los tokens de entrada incluyen los recuperados de caché. Por tanto, no deben sumarse nuevamente a la columna de caché.

- Entrada no cacheada: 503.626 tokens.
- Pensamiento reportado por los modelos: 41.809 tokens.
- Modelo principal: Gemini 3.8 Flash.
- Modelos auxiliares: Gemini 3 Flash Preview y Gemini 3.5 Flash Lite.

Los resultados corresponden únicamente a esta sesión identificada.

## 3. Tiempo de ejecución

| Métrica | Resultado |
|---|---|
| Tiempo total al cerrar la sesión | 25 min 55 s |
| Agent Active | 21 min 9 s |
| API Time | 14 min |
| Tool Time | 7 min 8 s |

El tiempo de pared incluye esperas e interacción humana. No debe interpretarse exclusivamente como tiempo de programación autónoma.

## 4. Llamadas a herramientas

| Herramienta | Llamadas |
|---|---:|
| `update_topic` | 5 |
| `activate_skill` | 4 |
| `list_directory` | 2 |
| `read_file` | 39 |
| `ask_user` | 16 |
| `replace` | 4 |
| `write_file` | 28 |
| `run_shell_command` | 10 |
| **Total** | **108** |

- Llamadas exitosas: 106.
- Llamadas fallidas: 2.
- Tasa de éxito: 98,1 %.

## 5. Intervención humana

La herramienta registró:

- 16 llamadas a `ask_user`.
- 102 sugerencias revisadas y aceptadas.
- 0 sugerencias rechazadas.
- 0 sugerencias modificadas.
- Agreement Rate: 100 %.

El resumen general también reportó 107 elementos revisados. La diferencia entre contadores se conserva sin equipararlos automáticamente, ya que pueden representar unidades distintas.

Las llamadas a preguntas, las sugerencias revisadas y los mensajes humanos no deben tratarse como un único conteo de interacciones.

## 6. Cambios de código reportados

Gemini CLI informó:

- Adiciones: 4.873.
- Eliminaciones: 1.318.
- Cambio neto de las operaciones registradas: +3.555.

Estas cifras son contadores acumulados de edición de la sesión y no equivalen necesariamente a la diferencia real entre la línea base y el resultado final.

La comparación definitiva deberá realizarse contra el manifiesto SHA-256 de los 66 archivos iniciales.

## 7. Evidencia de utilización de Tessl

La sesión registró la activación de las cuatro habilidades del flujo SDD:

1. `requirement-gathering`.
2. `spec-writer`.
3. `spec-verification`.
4. `work-review`.

Además, el agente utilizó las reglas y convenciones de especificación instaladas en el proyecto mediante Tessl.

Se documentaron aprobación de requisitos, generación de especificaciones, aprobación humana e implementación posterior.

Por tanto, la ejecución corresponde a Gemini CLI utilizando el flujo SDD instalado de Tessl, aunque no se atribuyen todas las operaciones a llamadas remotas de servicios Tessl.

## 8. Limitaciones

- No existe costo monetario facturado atribuible a esta sesión.
- Los contadores acumulados de edición no son un diff Git.
- No se midió por separado el tiempo efectivo de cada decisión humana.
- La auditoría independiente y las métricas finales del código aún están pendientes.

Este documento cierra el registro de telemetría de la sesión inicial de implementación de la Etapa 2.