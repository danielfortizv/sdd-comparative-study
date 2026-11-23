# E2 Tessl — Registro de telemetría consolidada (complemento del Registro 03)

**No sobrescribir** `E2_TESSL_REGISTRO_03_TELEMETRIA.md`: ese documento registra exclusivamente la implementación inicial. Este archivo registra una segunda sesión y los totales de ambas.

## Sesiones identificadas

| Campo | Sesión 01 | Sesión 02 |
|---|---|---|
| ID | `42bc44ee-b2c5-4042-8524-a249ef3b692f` | `3ab073d2-76fc-43d7-a3aa-1c0e322ec468` |
| Alcance | Implementación inicial con aclaraciones SDD | Auditorías, refinamiento de specs, correcciones y regresión según transcripciones aportadas |
| Evidencia | `/stats session`, `/stats model`, `/stats tools`, `/quit` | Captura final `/quit` |
| Modelos principales | `gemini-3.8-flash` | `gemini-3.8-flash` |
| Herramientas | 108: 106 OK y 2 errores | 129: 128 OK y 1 error |
| Tasa de éxito | 98,1 % | 99,2 % |
| Wall time | 25 min 55 s | 1 h 33 min 24 s |
| Agent active | 21 min 9 s | 30 min 37 s |
| API time | 14 min (redondeado) | 28 min 28 s |
| Tool time | 7 min 8 s | 2 min 9 s |
| Ediciones declaradas | +4.873 / −1.318 | +546 / −30 |
| Acuerdo de usuario | 100 % (107 revisadas en summary; 102 en tools) | 100 % (128 revisadas) |
| Msgs humanos | N/D | N/D |

## Uso de modelos por sesión

| Sesión | Modelo / rol | Solicitudes | Entrada inclusiva de caché | Caché | Salida |
|---|---|---:|---:|---:|---:|
| 01 | gemini-3.8-flash / main | 94 | 9.990.626 | 9.583.054 | 56.122 |
| 01 | gemini-3-flash-preview / loop | 5 | 95.780 | 0 | 675 |
| 01 | gemini-3.5-flash-lite / summarizer | 1 | 274 | 0 | 8 |
| **01 total** | | **100** | **10.086.680** | **9.583.054** | **56.805** |
| 02 | gemini-3.8-flash / main | 93 | 12.148.493 | 10.864.250 | 35.536 |
| 02 | gemini-3-flash-preview / loop | 2 | 37.991 | 0 | 274 |
| 02 | gemini-3.5-flash-lite / summarizer | 1 | 0 | 0 | 0 |
| **02 total** | | **96** | **12.186.484** | **10.864.250** | **35.810** |
| **E2 total observado** | | **196** | **22.273.164** | **20.447.304** | **92.615** |

**Totales derivados:** entrada no cacheada = **1.825.860**; fracción cacheada = **91,80 %**; llamadas = **237**, de ellas **234 exitosas**; wall time agregado = **7.159 s**; agent active agregado = **3.106 s**. Los tiempos de distintas sesiones se suman como duraciones observadas, no como productividad neta de una persona.

**Control de doble conteo:** en la sesión 01, la salida de `/stats session` previa a `/quit` mostraba 25m43s, pero `/quit` al cierre mostraba 25m55s. Se utilizó **solo la última**, no ambas. La captura 02 corresponde a otro Session ID. Las capturas intermedias de una sesión no se acumulan nuevamente.

**No confundir:** `Input Tokens` ya incluye `Cache Reads`. Las solicitudes de modelos auxiliares sí se agregan, pero se mantienen identificadas. Los 41.809 tokens de pensamiento reportados en `/stats model` para la sesión 01 no constituyen por sí solos `Tok Out`, y no se dispone del equivalente de la segunda sesión. Las sugerencias revisadas no son `Msgs`.

**Costo:** N/D. La tarifa de otro modelo aplicada en apartados históricos de la tesis no es extrapolable sin verificar precios y unidades de estos modelos, caché y Vertex AI. No se observó factura atribuible a este caso.

## Comparación con la Etapa 1 — datos observados de alcance desigual

| Indicador | E1 (una sesión registrada) | E2 (dos sesiones registradas) | Variación descriptiva |
|---|---:|---:|---:|
| Tok In | 16.640.788 | 22.273.164 | +33,85 % |
| Tok Cache | 15.464.495 | 20.447.304 | +32,22 % |
| Tok Out | 71.214 | 92.615 | +30,05 % |
| Tool Calls | 153 | 237 | +54,90 % |
| Agent active (s) | 7.454 | 3.106 | −58,33 % |
| Wall time (s) | 9.807 | 7.159 | −27,00 % aprox. |

**Precaución:** E1 fue un registro de una sesión identificada cuya cobertura pudo ser incompleta. E2 son dos sesiones identificadas; las variaciones no son efectos causales de Tessl ni garantizan universos de captura equivalentes.

## Acciones de archivo

- Conservar exportaciones `.jsonl` originales, si están disponibles, con sus Session IDs.
- Conservar `EVIDENCIA_SESION_01_GEMINI.txt` y `EVIDENCIA_SESION_02_GEMINI.png` sin reescritura.
- No atribuir la telemetría de preparación PowerShell, pruebas humanas fuera del agente o escaneos SonarQube locales a los contadores de Gemini.
