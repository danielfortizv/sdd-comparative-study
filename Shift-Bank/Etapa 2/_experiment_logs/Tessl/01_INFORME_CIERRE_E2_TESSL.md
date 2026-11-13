# Informe de cierre experimental — Shift Bank, Etapa 2, Tessl

**Corte de observación:** 13/11/2026. **Caso:** aplicación bancaria Shift Bank. **Etapa:** 2 — complejidad funcional y estado. **Variante:** Tessl mediante Gemini CLI. **Condición experimental:** extensión *brownfield* de la Etapa 1. **Opción:** A, transferencias ACH/interbancarias a terceros, pagos recurrentes y límites dinámicos.

## 1. Resumen ejecutivo

Se reutilizó la implementación de Shift Bank de la Etapa 1 tras copiar y verificar por SHA-256 66 archivos. La nueva etapa amplió el sistema con beneficiarios y transferencias ACH simuladas, ejecución programada de pagos recurrentes y límites por operación y por día, conservando el sistema heredado de cuentas, transferencias internas, movimientos y MFA. Tessl operó como flujo SDD instalado (reglas, especificaciones y *skills*), mientras Gemini CLI realizó las lecturas, ediciones y ejecuciones.

La primera implementación cerró con 66 pruebas automatizadas aprobadas (35 backend, 31 frontend). Tras una auditoría del agente, se ajustaron especificaciones y comportamientos de programación/cancelación y validación ACH. Dos de las nuevas pruebas fallaron por errores de lógica del propio test y por comparación de fechas de distinta representación; una corrección posterior dejó **43/43 pruebas backend y 35/35 frontend aprobadas**, además de compilación TypeScript/Vite exitosa. La auditoría final **reportó** satisfacción de 121/121 requisitos de siete especificaciones. Este valor no debe confundirse con verificación externa ni cobertura exhaustiva.

SonarQube analizó 4.230 LOC no comentadas antes de la corrección y 4.267 LOC después; las incidencias MQR permanecieron en 0 de seguridad, 26 de fiabilidad y 42 de mantenibilidad, con ratings A/C/A. El inventario final corregido registra 82 archivos físicos relevantes frente a 66 originales: 51 intactos, 15 modificados, 16 nuevos y 0 eliminados. Las siete especificaciones finales sumaron 575 líneas. La aplicación se inició localmente con FastAPI y Vite y el investigador informó funcionamiento satisfactorio; no existe una matriz de aceptación por escenario documentada.

## 2. Diseño, contexto y preparación

La alternativa A corresponde al módulo bancario definido para la Etapa 2 en la matriz de evaluación. La preparación se registró el 04/11/2026 y el desarrollo/las mediciones principales, el 13/11/2026. Se copió el proyecto E1 a un directorio E2 independiente, excluyendo dependencias, builds, cachés, enlaces y la base de datos SQLite modificable; se verificaron 66 hashes idénticos y se reconstruyeron ocho enlaces locales a las habilidades de Tessl. Las pruebas previas a la evolución fueron 22 backend y 23 frontend, todas aprobadas.

**Entorno observado:** Windows/PowerShell 5.1, Python 3.13.2, Node 24.19.0, npm 11.17.0, Gemini CLI 0.65.0, Tessl CLI 0.118.1, tile `tessl-labs/spec-driven-development@2.0.1`; backend FastAPI/SQLAlchemy/SQLite, frontend React/TypeScript/Vite/Vitest. No debe declararse que el CLI de Tessl escribió código por sí solo; el agente operativo fue Gemini CLI, integrado al flujo Tessl. En la auditoría se confirmó conexión al servidor MCP de Tessl y estado `ready`.

## 3. Dimensión 1 — Esfuerzo y consumo

La documentación identifica **dos sesiones de Gemini CLI**, no todas las conversaciones humanas fuera del agente. Las estadísticas se agregaron una única vez desde los resúmenes finales de cada sesión.

| Indicador estandarizado | Sesión 01 — implementación | Sesión 02 — verificación/correcciones | Total observado E2 |
|---|---:|---:|---:|
| Tok In (incluye caché) | 10.086.680 | 12.186.484 | **22.273.164** |
| Tok Cache | 9.583.054 | 10.864.250 | **20.447.304** |
| Tok In sin caché (derivado) | 503.626 | 1.322.234 | **1.825.860** |
| Tok Out | 56.805 | 35.810 | **92.615** |
| Solicitudes de modelo | 100 | 96 | **196** |
| Tool Calls | 108 | 129 | **237** |
| Llamadas exitosas | 106 | 128 | **234** |
| Llamadas fallidas | 2 | 1 | **3** |
| Tiempo activo del agente (s) | 1.269 | 1.837 | **3.106** |
| Tiempo de pared (s) | 1.555 | 5.604 | **7.159** |
| Msgs (prompts humanos) | N/D | N/D | **N/D** |
| Costo financiero ($ USD) | N/D | N/D | **N/D** |

El 91,80 % de las entradas agregadas corresponde a recuperación desde caché. `Tok In` **ya incluye** `Tok Cache`, que no debe sumarse nuevamente. La sesión inicial utilizó principalmente `gemini-3.8-flash` (94 solicitudes) y la segunda el mismo modelo (93 solicitudes); los modelos auxiliares fueron `gemini-3-flash-preview` y `gemini-3.5-flash-lite`. Los contadores de *thoughts* son una categoría diferente y no se agregan a `Tok Out`.

En las capturas aparecen 107 sugerencias revisadas para la sesión 01 (102 en la pantalla específica de herramientas) y 128 revisadas en la sesión 02. Estas unidades no son los mensajes humanos solicitados por `Msgs`. Las dos sesiones acumulan `+5.419/-1.348` cambios de líneas **reportados por el agente**, que incluyen ediciones intermedias y no son un diff real entre E1 y E2. Para la etapa anterior se habían registrado 16.640.788 tokens de entrada, 15.464.495 de caché, 71.214 de salida, 153 llamadas, 7.454 segundos activos y 9.807 de pared, **de una sola sesión identificable**; la cobertura de captura no es necesariamente idéntica.

## 4. Dimensión 2 — Calidad del código generado

Se utilizó SonarQube Community Build 26.9.0.129388 y SonarScanner 8.1.0.6389 con 57 archivos indexados en Python, TypeScript y CSS; se excluyeron dependencias, builds, cachés, entornos virtuales y bases SQLite. Se guardaron dos cortes independientes:

| Métrica | E1 (referencia) | E2 inicial | E2 poscorrección |
|---|---:|---:|---:|
| LOC — `ncloc` SonarQube | 2.182 | 4.230 | **4.267** |
| Líneas totales bajo análisis (`lines`) | N/D | 4.966 | **5.004** |
| Bugs (métrica tradicional) | 0 | 0 | **0** |
| Vulnerabilidades (tradicional) | 0 | 0 | **0** |
| Code smells (tradicional) | 21 | 51 | **51** |
| Hallazgos tradicionales (Bugs + Vulns + Smells) | 21 | 51 | **51** |
| Hal/KLOC (tradicional) | 9,62 | 12,06 | **11,95** |
| Deuda técnica tradicional (min) | 82 | 276 | **276** |
| Complejidad cognitiva | 98 | 329 | **337** |
| Duplicación (%) | 0,0 | 0,8 | **0,8** |
| Cobertura importada (%) | N/D | 0,0 | **0,0** |
| MQR: incidencias fiabilidad | N/D | 26 | **26** |
| MQR: incidencias mantenibilidad | N/D | 42 | **42** |
| MQR: incidencias seguridad | N/D | 0 | **0** |
| Ratings MQR (Seg./Fiab./Mant.) | N/D | A/C/A | **A/C/A** |
| Esfuerzo remediación MQR (min) | N/D | 231 | **231** |

El volumen de producción analizado aumentó **2.085 ncloc, +95,55 %** respecto de E1; entre E2 inicial y E2 final aumentó solo 37 ncloc. Los code smells y el esfuerzo de remediación no disminuyeron tras las correcciones, aunque los tests concluyeron exitosamente. El `Quality Gate` informó `OK`, pero **no tenía condiciones configuradas**, por lo cual no acredita umbrales de calidad. El `0,0 %` mostrado corresponde a **ausencia de cobertura importada**, no a ausencia de pruebas. Conforme a la guía, la cobertura de E1/E2 no debe utilizarse como criterio formal comparable si solo se evaluará desde E3.

**No mezclar métricas:** la API tradicional reportó `bugs=0`, `code_smells=51`, `reliability_rating=A`, mientras el panel MQR mostró 26 incidencias de fiabilidad y calificación C. Son taxonomías distintas: la fila de `Hallazgos` sigue la definición clásica de la guía; las incidencias MQR se consignan en apartado complementario. El análisis de seguridad de Community Build es limitado; cero hallazgos no demuestra ausencia de SQLi/XSS.

## 5. Dimensión 3 — Especificaciones

Se finalizaron **7 archivos `.spec.md`, 575 líneas físicas, 28.677 bytes de especificación y 121 requisitos según el agente**. Los tres archivos nuevos suman 331 líneas; los cuatro heredados contienen 244 líneas en su estado final. Las especificaciones heredadas en E1 sumaban 241 líneas.

| Archivo | Origen | Líneas |
|---|---|---:|
| accounts.spec.md | E1, sin cambios | 53 |
| transfers.spec.md | E1, modificado | 79 |
| transactions.spec.md | E1, sin cambios | 53 |
| mfa.spec.md | E1, sin cambios | 59 |
| ach_transfers.spec.md | Nuevo E2 | 137 |
| recurring_payments.spec.md | Nuevo E2 | 123 |
| transfer_limits.spec.md | Nuevo E2 | 71 |
| **Total** | | **575** |

| Métrica estandarizada | E1 | E2 final |
|---|---:|---:|
| Archs .md | 4 | **7** |
| Lín. Spec | 241 | **575** |
| Densidad (líneas/archivo) | 60,25 | **82,14** |
| Ratio C/E (ncloc / Lín. Spec) | 9,05 | **7,42** |
| # Req según auditoría del agente | 51 | **121** |
| Req/CLOD (req por 100 líneas spec) | 21,16 | **21,04** |

Distribución E2 ordenada: `[53, 53, 59, 71, 79, 123, 137]`. Resumen de cinco números usando **percentil inclusivo (interpolación lineal, como PERCENTILE.INC)**: mínimo 53, Q1 56, mediana 71, Q3 101, máximo 137. La elección de convención de cuartiles debe mantenerse uniforme para todas las herramientas.

## 6. Dimensión 4 — Expectativa funcional

La expectativa mínima identificable en el documento de etapas fue: **transferencias a terceros ACH/interbancarias, programación de pagos recurrentes y límites dinámicos**. El agente desagregó y aprobó contratos internos sobre beneficiarios guardados o ad hoc, estados ACH simulados, programación diaria/semanal/mensual, restricciones de estado, ejecución de scheduler, límites por transacción/diarios y MFA heredado. Las auditorías generadas por el propio agente clasificaron **102/118 requisitos satisfechos y 16 parciales** antes de la corrección, y **121/121 satisfechos** en el cierre después de añadir tres cláusulas. La última auditoría visible leyó especificaciones, por lo que no es evidencia independiente suficiente para asignar cumplimiento externo del 100 %.

Las pruebas automatizadas de cierre respaldan 43 escenarios backend y 35 frontend, pero no son sinónimo de cobertura íntegra de 121 requisitos. El investigador reportó que la aplicación **arrancó y funcionó correctamente en uso local**. No se recibieron capturas individuales de transferencias ACH completas, evolución automática del scheduler durante horas, reembolsos, límites al borde, estados MFA, responsividad o funcionamiento multiworker. Se conserva como **validación exploratoria satisfactoria reportada**, pendiente de certificación por escenario. Como extra se documentó el endpoint `POST /api/recurring/process-due` para disparar procesamientos simulados: fue una ampliación de la superficie HTTP propuesta por el agente, formalizada tras una aprobación genérica `yes`.

## 7. Dimensión 5 — Retroalimentación humana

El principal ciclo de aclaración inicial incluyó decisiones de negocio guiadas por Tessl antes de aprobar especificaciones. Tras implementar se encontraron: (1) cancelación de programaciones eludible mediante pausa y reanudación (**alto**); (2) fecha inicial ausente causando ejecución inmediata (**medio**); (3) validación tardía de routing number (**medio**); (4) historial de reintegro ACH potencialmente confuso (**menor, sin infracción literal del contrato**). Los tres primeros se corrigieron en especificaciones y código; el cuarto quedó sin cambios por alcance.

El mismo ciclo de corrección añadió pruebas que inicialmente fallaron por (5) sumar incorrectamente 400 + 450 + 500 dentro de un límite diario 1.000, y (6) comparar un `datetime` consciente de UTC con otro sin zona horaria devuelto desde SQLite. Se revisaron únicamente los tests, tras lo cual el conjunto completo pasó. La sesión de correcciones usó el `yes` del usuario como aprobación de **tres decisiones independientes** sin confirmación específica: intervalo de primera ejecución, reembolso sin asiento compensatorio y formalización del endpoint manual. Registrar esta ambigüedad sin reescribir las evidencias.

## 8. Rastro de pruebas y mediciones

| Hito | Backend | Frontend | Compilación | Evidencia |
|---|---:|---:|---|---|
| Antes de E2, copia brownfield | 22/22 | 23/23 | N/D | Registro 01 preparación |
| Primera implementación E2 | 35/35 | 31/31 | Correcta según agente | Transcript inicial Gemini |
| Tras primera corrección | 41/43 | 35/35 | Pendiente en esa captura | Pytest y Vitest locales |
| Tras corregir las pruebas | **43/43** | **35/35** | **TypeScript + Vite OK** | CLI Gemini y salida de test |

Los dos fallos intermedios no se excluyen del análisis: son evidencia del costo de la corrección y de defectos en las pruebas generadas. Las 78 pruebas finales superan las 45 heredadas por **33 pruebas (+73,33 %)**.

## 9. Evolución de archivos y trazabilidad SHA-256

El manifiesto inicial contiene **66 archivos** con hashes SHA-256. El primer script clasificó erróneamente 18 rutas ocultas (`.codex`, `.gemini`, `.tessl`, etc.) como eliminadas y nuevas a la vez, porque `TrimStart('./')` eliminó el punto inicial. Se conservó el CSV inicial y se generó un **CSV corregido** reparando la correspondencia de ruta con hashes. **Resultado definitivo:** 51 archivos sin cambios, 15 modificados, 16 nuevos, 0 eliminados; **82 archivos** finales considerados. Se excluyeron dependencias y artefactos generados, y no se siguieron los junctions.

Entre los archivos funcionales, 12 archivos de código de producción fueron modificados y 8 creados; también se añadieron o cambiaron 7 archivos de pruebas y 4 especificaciones. Esta clasificación es **por archivos**, no por líneas de código. La medida `Diff LOC` de la guía —LOC nuevas, modificadas y eliminadas— permanece **N/D** hasta contar ediciones reales mediante un diff reproducible sobre contenido de E1 y E2. El cambio neto `ncloc` de SonarQube (+2.085) no puede utilizarse como sustituto de `LOC Nu./Mod./Del.`.

## 10. Limitaciones y cierre

1. **Semilla común:** el registro preparatorio declara `SemillaComunAprobada=false`; no se suministró `SEED-2.md` uniforme para comparar las cinco herramientas. La fidelidad al protocolo común no está demostrada.
2. **Deriva de versión/modelo:** la matriz experimental solicitaba Gemini CLI **0.60.0** y Gemini **3.5 Flash** como modelo general; se observaron Gemini CLI **0.65.0** y modelo principal **Gemini 3.8 Flash**. Requiere explicación/control de validez entre herramientas.
3. **Alcance de E1:** la aplicación Tessl de E1 adoptó USD y umbral MFA >USD 1.000, mientras la referencia común de E1 se había formulado en COP y otro umbral. La consistencia interna de E2 no implica fidelidad a toda la semilla común.
4. **Telemetría:** dos sesiones identificadas; no se demuestra exhaustividad de otros posibles procesos fuera de esas sesiones. `Msgs` y costo monetario atribuible a Tessl son N/D.
5. **Auditoría:** cumplimiento 121/121 **declarado por Gemini/Tessl**, no validación externa ciega; las pruebas y el funcionamiento local son evidencias complementarias.
6. **SonarQube:** Quality Gate sin condiciones, cobertura no importada y análisis limitado de seguridad; ratings MQR no equivalen a clasificación tradicional.
7. **Operación:** no se probó formalmente scheduler multihora, fallos ACH forzados por interfaz, concurrencia multiworker o múltiples sesiones de usuario.

**Conclusión:** Shift Bank — Tessl E2 finalizó con implementación ejecutable, 78 pruebas exitosas, especificaciones ampliadas y mediciones estáticas y evolutivas reproducibles. El caso ilustra que un proceso SDD puede restablecer contratos y pruebas después de una auditoría, sin que ello reduzca automáticamente las incidencias de calidad estática. Su éxito debe reportarse **dentro del contrato aprobado**, distinguiéndolo de la fidelidad a las condiciones comunes del experimento y de una aceptación funcional independiente.
