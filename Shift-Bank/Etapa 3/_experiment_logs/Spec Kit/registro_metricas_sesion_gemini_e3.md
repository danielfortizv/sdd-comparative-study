# Registro de métricas de agente — Shift Bank, Etapa 3

**Fuente:** capturas de cierre de Gemini CLI suministradas en el proyecto (`image(20261116-022142).png` e `image(20261116-082438).png`).  
**Herramienta medida:** Gemini CLI. **No corresponden a telemetría de Codex.**  
**Fecha de registro:** 2026-11-16.  
**Regla de interpretación:** los tokens de *Cache Reads* se registran por separado; no se suman a *Input Tokens* como si fueran otra clase de consumo independiente. Las solicitudes de modelo no son equivalentes a llamadas a herramientas.

## Sesión A — `803a73df-1582-49fd-bc2b-126223295031`

| Medida | Valor |
|---|---:|
| Llamadas a herramientas | 207 |
| Exitosas / fallidas | 205 / 2 |
| Tasa de éxito | 99,0 % |
| Acuerdo del usuario | 100,0 % (205 revisadas) |
| Líneas añadidas / eliminadas | 9.542 / 5.768 |
| Tiempo de pared | 1 h 57 min 33 s |
| Tiempo activo del agente | 1 h 00 min 55 s |
| Tiempo API | 46 min 58 s (77,1 % del activo) |
| Tiempo de herramientas | 13 min 56 s (22,9 % del activo) |

| Modelo | Solicitudes | Tokens de entrada | Cache Reads | Tokens de salida |
|---|---:|---:|---:|---:|
| `gemini-3.8-flash` (main) | 221 | 49.301.006 | 46.515.753 | 176.679 |
| `gemini-3-flash-preview` (utility_loop_detector) | 3 | 83.043 | 0 | 441 |
| **Total registrado** | **224** | **49.384.049** | **46.515.753** | **177.120** |

## Sesión B — `73decf2c-899f-4990-9ed0-2c112284d16b`

| Medida | Valor |
|---|---:|
| Llamadas a herramientas | 422 |
| Exitosas / fallidas | 415 / 7 |
| Tasa de éxito | 98,3 % |
| Acuerdo del usuario | 100,0 % (417 revisadas) |
| Líneas añadidas / eliminadas | 5.291 / 2.136 |
| Tiempo de pared | 6 h 02 min 21 s |
| Tiempo activo del agente | 4 h 09 min 34 s |
| Tiempo API | 1 h 06 min 24 s (26,6 % del activo) |
| Tiempo de herramientas | 3 h 03 min 10 s (73,4 % del activo) |

| Modelo | Solicitudes | Tokens de entrada | Cache Reads | Tokens de salida |
|---|---:|---:|---:|---:|
| `gemini-3.5-flash-lite` (utility_summarizer) | 1 | 0 | 0 | 0 |
| `gemini-3.8-flash` (main) | 437 | 110.475.146 | 104.170.281 | 151.850 |
| `gemini-3-flash-preview` (utility_loop_detector) | 14 | 249.440 | 0 | 1.763 |
| **Total registrado** | **452** | **110.724.586** | **104.170.281** | **153.613** |

## Alcance y cautelas

1. Estos valores corresponden solo a las dos sesiones fotografiadas y no deben interpretarse como todo el consumo de Gemini en la Etapa 3.
2. No hay, en estas capturas, costos monetarios verificables ni telemetría de Codex. El costo debe permanecer N/D salvo que se disponga de precios/tarifas y un método de imputación justificado.
3. Para el estudio comparativo, mantener atribución **Gemini CLI** separada de la intervención posterior de **Codex**.
4. Conservar las capturas originales como evidencia y referenciar este registro desde la bitácora experimental sin alterar registros previos.
