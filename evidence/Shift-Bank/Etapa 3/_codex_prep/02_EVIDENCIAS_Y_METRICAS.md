# 02 — Evidencias, trazabilidad y medición de E3 / Spec Kit

Este archivo aplica el protocolo de replicación de E3 y la **Guía de Estandarización de Métricas**. Codex organiza y prepara la instrumentación documental; **no debe inventar resultados** ni mezclar su trabajo preparatorio con las mediciones del agente evaluado Gemini CLI.

## A. Clasificación de evidencia

| Tipo | Se conserva en | Regla |
|---|---|---|
| E2 origen (inmutable) | `Etapa 2/_experiment_logs/Spec Kit/` | No mover ni reescribir reportes; solo referencia con hash |
| Copia E3 inicial | `Etapa 3/_experiment_logs/Spec Kit/preparacion/` | Hash por archivo origen/destino y cotejo byte a byte |
| Acción de Codex | `preparacion/E3_SPECKIT_PREPARACION_CODEX_LOG.md` | Herramienta auxiliar, fuera de la métrica Gemini de E3 |
| Gemini CLI E3 | `sesiones/` | Capturas originales `/stats`, JSONL originales, IDs y tiempo de observación |
| Aclaraciones y aprobación | `decisiones/` | Fecha, pregunta exacta, respuesta y aprobación; no decisiones retroactivas |
| Pruebas | `pruebas/` | Salida cruda, códigos, reportes coverage, antes/después sin sobrescribir |
| Carga | `locust/` | Comando exacto, duración real, CSV/JSON originales, DB sintética aislada |
| SonarQube | `sonarqube/` | Análisis previos/finales y sus IDs, scopes, coverage y Quality Gate |
| Diff E2→E3 | `diffs/` | Métodos y filtros exactamente comparables a E2, sin dependencias/cachés |

**Preferencia:** original y derivado en archivos separados. Si se genera una matriz de resultados, documentar los nombres de cada fuente cruda y su SHA-256.

## B. Reglas de métricas D1–D5

**D1 — Esfuerzo y consumo:** `Tok In`, `Tok Cache`, `Tok Out`, `Cred` (solo Kiro), `Costo ($)`, `Msgs`, `Tool Calls`, `Tiempo (s)`. Identificar ventana por `sessionId`; tokens cacheados son subconjunto de entrada y **no se suman de nuevo** a `Tok In`. No sumar dos capturas que representan una misma sesión o ventanas solapadas. No confundir `Wall Time` con `Agent Active`. El costo no observado es `N/D` (no `$0`). El trabajo de **Codex Hito 0 se separa** del esfuerzo atribuible a Gemini E3.

**D2 — Calidad:** `LOC`, `LOC Nu.`, `LOC Mod.`, `LOC Del.`, `Hallazgos`, `Hal/KLOC`, `Cob (%)`, `Bugs`, `Vulns`, `Smells`, `Deuda (m)`, `Comp. Cog.`, `Dupl. (%)`, `Rating`. Informar y conservar alcance SonarQube (`sonar.sources`, tests, exclusiones, versiones, calidad de gate). SonarQube `coverage = 0` con reportes no importados significa **sin cobertura instrumentada en ese escaneo**, no 0 % de pruebas ejecutadas. No sumar dimensiones MQR con hallazgos clásicos como si fueran incidencias adicionales independientes.

**D3 — Especificaciones:** `Archs .md`, `Lín. Spec`, `Densidad`, `Ratio C/E`, `# Req`, `Req/CLOD`, `Mínimo`, `Q1`, `Mediana`, `Q3`, `Máximo`. No incluir `README`, prompts de Codex ni reporte de evidencia en el conteo de specs. No contar arbitrariamente las viñetas como requisitos atómicos. Fijar un filtro uniforme antes de comparar herramientas. La semilla común **no es una especificación generada por Spec Kit**.

**D4 — Expectativa funcional:** `ID Req.`, `Aspecto Mín.`, `Estado`, `Reflexión`, `Extra`, `Clasif. Extra`, `Arg. Extra`. Para E3 existe una matriz externa AC-01 a AC-16, pero no es automáticamente un contrato generado por la herramienta. Distinguir automatización, validación humana, evidencia pendiente y limitación del modelo de amenazas.

**D5 — Retroalimentación:** `Nº`, `Inconveniente`, `Relevancia`, `Explicación`. Conservar aclaraciones, fallos, remediaciones y decisiones, clasificando defectos de implementación vs ambigüedad documental vs herramientas/infrastructura. No «limpiar» las iteraciones fallidas de un transcript.

**Fórmulas estandarizadas (usar solo cuando existan entradas verificadas):**

```text
Hal/KLOC = Hallazgos / (LOC / 1000)
Densidad = Lín. Spec / Archs .md
Ratio C/E = LOC / Lín. Spec
Req/CLOD = (# Req / Lín. Spec) * 100
```

Para cada etapa evolutiva, calcular variación respecto al **cierre E2 de esa misma herramienta**; en las tablas académicas la variación va en una línea separada bajo el valor, con abreviaturas/unidades oficiales. Los documentos científicos D1–D5 serán revisados y escritos por el investigador; Codex no debe presentarse como autoridad de resultados de E3.

## C. Regla de comparabilidad y neutralidad

- Entregar **idéntica `SEED-3.md`** a cada herramienta. E3 hereda la implementación **propia** de E2, no la de Tessl.
- No preprogramar cifrado RSA/AES, HMAC de auditoría, tablas de base de datos, `Locustfile` o Docker Compose por referencia a la implementación histórica de Tessl. Son futuras decisiones técnicas del agente y del investigador.
- Los parámetros comunes de carga, los límites de SLO, la matriz de aceptación AC-01..AC-16 y la metodología de medición sí son condiciones externas comparables, pero su presentación como contrato vinculante debe respetar la aprobación prospectiva común.
- Ningún resultado de Tessl es una meta de performance para Spec Kit. No imponer el mismo número de pruebas, LOC, smells, archivos o prompts.

## D. Qué congelar al cerrar Hito 0

- `SEED-3.md`: hash exacto, ruta y timestamp de verificación.
- E2 origen: SHA, inventario, commit/branch/estado Git y configuración SDD.
- E3 copia: SHA, matriz de correspondencia, ausencias/modificaciones/extra, confirmación de exclusión de SQLite/secretos.
- Dependencias y CLI: versión efectiva con comandos/salidas, sin afirmar disponibilidad si no se pudo probar.
- Regresión pre-E3: salida cruda y código de `pytest`, `vitest`, `vite build`, sin reescribir resultados.
- Instrucción de contexto para Gemini futura: referencias a artefactos de herencia y al seed, **pero sin incidentes de Tessl**.
- Log Codex con timestamp de inicio/fin, objetivos, acciones, rutas creadas, errores y decisiones bloqueadas. D1 E3 aún **no iniciado**.

## E. Control de datos y secretos

Nunca versionar o imprimir valores de `SONAR_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, claves AES/HMAC, claves privadas TLS, contraseñas, PIN privados, información bancaria real ni credenciales. El PIN `123456` es un valor simulado heredado y **no debe presentarse como mecanismo de producción**. Los historiales de pagos de la semilla son sintéticos. No copiar a E3 logs E2 con secretos o sesiones crudas. No escribir hashes en archivos originales con una finalidad de «sellado» que los modifique.

## F. Eventos que bloquean la entrega

`NO-GO`: seed con hash distinto, versión E2 fuente no verificable, destino preexistente en conflicto, heredados modificados, `.db`/sidecars copiados por error, pruebas ejecutadas sobre datos históricos, instalación que reescribe manifests o código, error en regresiones sin documentar, o desviación de carpeta/herramienta. No convertir `NO-GO` en `GO` renombrando o borrando evidencia.
