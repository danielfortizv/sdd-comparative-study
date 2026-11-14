# E3_TESSL_REGISTRO_00_PREPARACION

> Registro interno del investigador. No es una especificación de Tessl ni una evidencia generada por la herramienta. No incluir este archivo en el conjunto oficial de datos empíricos salvo que el protocolo del equipo lo autorice expresamente.

## 1. Identificación del experimento

| Campo | Valor / estado |
|---|---|
| Caso de estudio | Shift Bank — sistema bancario simulado |
| Herramienta SDD | Tessl |
| Agente | Gemini CLI |
| Etapa | 3 — Arquitectura, seguridad y CI/CD |
| Opción | A |
| Fecha de inicio | 2026-11-13 |
| Entorno | Windows — PowerShell / Gemini CLI |
| Directorio de la aplicación | `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Tessl` |
| Directorio sugerido de registros internos y evidencias | `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Tessl` |
| Semilla común | `SEED-3.md` — idéntica para todas las herramientas |
| Prompt inicial | `PROMPT_GEMINI_TESSL_ETAPA3_01.md` |
| Versión objetivo de Gemini CLI según matriz experimental | `0.60.0` — **verificar y registrar versión real antes del inicio** |
| Modelo objetivo | `gemini-3.5-flash` — **verificar modelo realmente usado con `/stats model`** |
| Versión de Tessl | Pendiente de comprobar; no inferir de la Etapa 2 |
| Proyecto/región Vertex AI | Registrar el valor efectivamente usado al iniciar; no copiar valores sin verificar |
| Git commit / estado inicial | Pendiente |
| SHA-256 / manifiesto de copia | Pendiente de adjuntar o referenciar, si existe |
| Pruebas de regresión iniciales de Etapa 3 | Pendiente de verificar |

## 2. Línea base heredada y límites

La Etapa 3 evoluciona la aplicación existente de la Etapa 2; no crea una aplicación nueva. Deben preservarse: saldos, historial, transferencias entre cuentas propias, MFA simulado, transferencias ACH/interbancarias a terceros, pagos recurrentes y límites dinámicos. Backend FastAPI/Python y frontend React/TypeScript.

**Referencia histórica de cierre de Etapa 2 (NO equivale a una ejecución validada de Etapa 3):** 43/43 pruebas backend; 35/35 pruebas frontend; compilación frontend exitosa. Antes de atribuir estos resultados a E3 se requiere evidencia de la copia y/o pruebas en E3.

El prompt inicial afirma que la carpeta E3 ya está copiada y preparada. Esa preparación no ha sido verificada desde este registro: comprobar de manera externa, sin modificar otras etapas. Las Etapas 1 y 2 deben permanecer intactas.

## 3. Alcance invariable de la semilla común

1. Cifrado extremo a extremo de datos bancarios sensibles.
2. Registros inmutables de auditoría de transacciones.
3. Pruebas de carga.
4. Despliegue de la aplicación.

**Ambigüedades a resolver a través de Tessl antes de especificar e implementar:** frontera criptográfica del supuesto E2EE, nivel y modelo de inmutabilidad, carga/criterios de aceptación y objetivo de despliegue. Las respuestas se entregarán de una en una. No insertar decisiones funcionales específicas de Tessl en `SEED-3.md`.

**Fuera de alcance:** banca real, registro/login de usuarios, funcionalidades bancarias no solicitadas, modificación de otras herramientas o etapas.

## 4. Reglas de ejecución y aprobación

- Interactuar con el agente exclusivamente en inglés.
- Utilizar el flujo real de Tessl (reglas/skills del proyecto), no sustituirlo por otros frameworks SDD.
- Registrar cada pregunta y respuesta de aclaración, y si produjo cambio documental.
- No permitir cambios de código, pruebas, dependencias, infraestructura o configuración en la interacción inicial.
- Revisión y aprobación humana explícita de especificaciones **antes** de cualquier modificación funcional.
- Después de implementar, las correcciones funcionales se solicitan primero como cambios documentales/specs; nunca editar a mano el código para corregir el experimento.
- Separar: (a) aclaraciones antes de implementar, (b) correcciones humanas de specs, (c) correcciones autónomas del agente y (d) incidentes de ejecución.
- Mantener evidencia cruda inalterada; las métricas derivadas se calculan después, con procedencia identificable.

## 5. Evidencia a conservar

- `SEED-3.md` exacto (fuente común, sin modificaciones).
- Prompt exacto enviado, respuesta íntegra de Gemini y secuencia de preguntas/respuestas.
- Exportación(es) JSONL de todas las sesiones de Gemini CLI, conservando los originales.
- Capturas originales de `/stats`, especialmente desglose de tokens, modelos y herramientas al cierre de cada sesión.
- Versiones efectivas de Gemini CLI, modelo, Tessl y commit inicial/final.
- Instantáneas o reportes reproducibles de specs, pruebas, SonarQube, cobertura y diff LOC.
- Evidencia de pruebas de carga y del despliegue, identificando claramente entorno, objetivos y resultados observados (sin inventarlos).
- Registro de fallos de interpretación y correcciones: motivo, gravedad, intervención, artefacto afectado y evidencia.

**Regla de presentación:** conservar como fuentes oficiales únicamente los artefactos señalados en la guía del equipo (por ejemplo, JSONL, semilla, capturas y datos extraídos por scripts formales). Esta bitácora es ayuda interna de seguimiento, no un sustituto de dichas fuentes.

## 6. Métricas que se extraerán al cerrar E3

| Dimensión | Campos |
|---|---|
| D1 — Esfuerzo y consumo | Tok In, Tok Cache, Tok Out, Costo ($), Msgs, Tool Calls, Tiempo (s). Registrar por sesión y total agregado; no mezclar tiempo de procesamiento con tiempo de reloj sin aclaración. |
| D2 — Calidad de código | LOC, LOC Nu., LOC Mod., LOC Del., Hallazgos, Hal/KLOC, Cob (%), Bugs, Vulns, Smells, Deuda (m), Comp. Cog., Dupl. (%), Rating de SonarQube. |
| D3 — Especificaciones | Archs .md, Lín. Spec, Densidad, Ratio C/E, # Req, Req/CLOD, distribución de líneas por archivo (mínimo, Q1, mediana, Q3, máximo). Conservar universo de archivos contabilizados. |
| D4 — Expectativa funcional | Matriz de REQ-XX derivada de semilla, cumplió/no cumplió con evidencia; UX visual documentada; extras no pedidos clasificados como apoyo/redundancia. |
| D5 — Retroalimentación humana | Nº, inconveniente, relevancia (menor/medio/alto), explicación, corrección sobre especificaciones y evidencia. |
| Transversales | Nº de prompts, iteraciones de corrección, decisiones y aprobaciones, regresiones, cambios por etapa, comparaciones % E3 respecto a E2. |

No sustituir datos faltantes por ceros; usar **N/D** e indicar por qué. No calcular variaciones porcentuales hasta tener valores comparables de E2 y E3. Distinguir LOC de código fuente, LOC de tests y líneas de specs.

## 7. Lista de control previa al primer prompt

- [ ] Verificar que el directorio de trabajo es E3/Tessl y que E1/E2 están fuera de alcance.
- [ ] Comprobar que `SEED-3.md` coincide exactamente con la semilla común entregada.
- [ ] Confirmar versión efectiva de Gemini CLI y el modelo principal (sin enrutamiento no documentado).
- [ ] Registrar versión de Tessl y plugins/skills existentes, sin reinstalar ni actualizarlos.
- [ ] Guardar referencia del estado inicial del repositorio y de los tests heredados, si se dispone de evidencia.
- [ ] Iniciar una sesión de Gemini destinada solo a E3/Tessl.
- [ ] Conservar prompt 01 exactamente como fue enviado.
- [ ] No crear ni editar specs hasta completar aclaraciones y revisión humana.

## 8. Estado inicial (antes del primer prompt)

- Prompts funcionales E3 enviados: **0** (rellenar tras inicio).
- Aclaraciones formuladas por Tessl: **pendientes**.
- Especificaciones E3 aprobadas: **ninguna todavía**.
- Implementación E3 iniciada: **no**.
- Validación de requisitos E3: **pendiente**.

> Los valores anteriores describen el punto de partida planeado, no resultados empíricos de una ejecución completada.
