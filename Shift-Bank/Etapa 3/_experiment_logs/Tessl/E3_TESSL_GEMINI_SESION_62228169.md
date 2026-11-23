# Registro de estadísticas de Gemini CLI — E3 Tessl

**Fecha:** 13 de noviembre de 2026  
**Experimento:** Shift Bank — Etapa 3 — Tessl  
**Session ID:** `62228169-34da-4c19-a456-5a4362ac3702`

**Nota de atribución:** Aunque la terminal mostraba la ruta `Shift-Bank\Etapa 2\Tessl`, el investigador confirmó que la sesión corresponde a la ejecución de la Etapa 3. No se cambió el directorio de PowerShell antes de cerrar Gemini CLI.

## 1. Estadísticas de ejecución

| Métrica | Valor |
|---|---:|
| Tool Calls | 251 |
| Llamadas exitosas | 244 |
| Llamadas fallidas | 7 |
| Tasa de éxito | 97,2 % |
| User Agreement | 100 % (244 revisadas) |
| Líneas añadidas reportadas | 274 |
| Líneas eliminadas reportadas | 0 |
| Wall Time | 1 h 31 min 56 s |
| Agent Active | 1 h 16 min 33 s |
| API Time | 43 min 13 s |
| Tool Time | 33 min 19 s |

## 2. Consumo de modelos

| Modelo | Reqs | Tok In | Tok Cache | Tok Out |
|---|---:|---:|---:|---:|
| gemini-3.8-flash | 241 | 39.201.010 | 34.891.601 | 120.065 |
| gemini-3-flash-preview | 8 | 73.085 | 0 | 986 |
| gemini-3.5-flash-lite | 1 | 0 | 0 | 0 |
| **Total reportado** | **250** | **39.274.095** | **34.891.601** | **121.051** |

Los tokens de caché no deben sumarse nuevamente al total de entrada, puesto que representan lecturas reutilizadas.

## 3. Interpretación metodológica

Estos valores corresponden a una sesión específica de Gemini CLI asociada a la Etapa 3, no necesariamente al consumo total de toda la etapa.

Las estadísticas fueron obtenidas mediante la pantalla de resumen de `/quit`. La captura original se conserva como evidencia.

El costo económico permanece como N/D hasta verificar las tarifas aplicables y el procedimiento de cálculo.

Las líneas añadidas y eliminadas corresponden al registro interno del agente y no reemplazan las mediciones Git de cambios entre etapas.