# Registro de estadísticas de sesión — Gemini CLI

**Fecha de captura:** 13 de noviembre de 2026  
**ID de sesión:** `62228169-34da-4c19-a456-5a4362ac3702`  
**Ruta visible de terminal:** `Shift-Bank\Etapa 2\Tessl`  
**Etapa atribuida provisionalmente:** E2 Tessl

## Estadísticas operativas

| Indicador | Valor |
|---|---:|
| Tool Calls | 251 |
| Tool Calls exitosas | 244 |
| Tool Calls fallidas | 7 |
| Success Rate | 97,2 % |
| User Agreement | 100 % |
| Code Changes (+) | 274 |
| Code Changes (-) | 0 |
| Wall Time | 5.516 s |
| Agent Active | 4.593 s |
| API Time | 2.593 s |
| Tool Time | 1.999 s |

## Consumo por modelo

| Modelo | Reqs | Tok In | Tok Cache | Tok Out |
|---|---:|---:|---:|---:|
| gemini-3.8-flash | 241 | 39.201.010 | 34.891.601 | 120.065 |
| gemini-3-flash-preview | 8 | 73.085 | 0 | 986 |
| gemini-3.5-flash-lite | 1 | 0 | 0 | 0 |

El volumen de entrada reportado por Gemini incluye información reutilizada desde caché. No corresponde interpretar `Tok In + Tok Cache` como un total adicional de tokens de entrada.

No se calculó el costo financiero porque falta validar el modelo de facturación y las tarifas aplicables.

## Consideraciones metodológicas

La ruta de PowerShell visible en la captura corresponde a `Etapa 2\Tessl`, pero se recomienda confirmar la atribución mediante la exportación JSONL de la sesión.

Los tiempos corresponden al resumen de una sesión completa y no a un único prompt.

Las 274 líneas añadidas reportadas por Gemini CLI no sustituyen las métricas de diferencias entre versiones del repositorio.

Este registro es una transcripción derivada de una captura original, que debe conservarse por separado como fuente empírica.