# Shift Bank — Evidencia experimental

| Etapa | Libro | Traducción |
| --- | --- | --- |
| 1 | [Español](Etapa%201/metrics_stage_1.xlsx) | [English](Etapa%201/metrics_stage_1_english.xlsx) |
| 2 | [Español](Etapa%202/metrics_stage_2.xlsx) | [English](Etapa%202/metrics_stage_2_english.xlsx) |
| 3 | [Español](Etapa%203/metrics_stage_3.xlsx) | [English](Etapa%203/metrics_stage_3_english.xlsx) |
| 4 | [Español](Etapa%204/metrics_stage_4.xlsx) | [English](Etapa%204/metrics_stage_4_english.xlsx) |

BMAD Method se interrumpió en Etapa 1 y se excluyó deliberadamente de Etapas 2–4 por costo operativo y financiero. Excluido / Excluded identifica esa decisión, N/A indica una métrica ajena a la plataforma y N/D indica una medición no consolidable. Los comentarios delimitan las cifras parciales. Un cero numérico corresponde a una medición o cálculo sustentado.

Las cuatro semillas están en [seeds](../../seeds/). E1 preserva byte a byte la variante Tessl como referencia. Su uso común por las cinco herramientas sigue sin acreditarse. E2 conserva la propuesta histórica y el [contrato de alineación](Etapa%202/E2_COMMON_FUNCTIONAL_CONTRACT.md). E3 y E4 conservan sus originales comunes. En E1/E2, los mínimos y los cruces de cumplimiento se identifican como retrospectivos. Parcial señala que el registro respalda la observación dentro de su alcance y que la comparación se hizo contra una referencia.

## Criterios de lectura

- D1 usa subtotales de sesiones identificadas con el alcance en comentarios. Interacciones cuenta prompts o intervenciones humanas identificables, separados de aprobaciones y eventos automáticos. Los registros de Calculadora carecen de una regla de recuento reproducible. La tarifa Kiro se aplica solo a créditos acreditados. La tarifa depende del modelo efectivo de Gemini o Codex. Las extracciones históricas Codex distinguen su fase y su fuente. Los archivos telemetria_recuperada.json contienen metadatos y cifras, omiten el contenido de prompts y salidas, y conservan el hash de procedencia.
- D2 utiliza ncloc, deuda en minutos y categorías tradicionales del mismo análisis. Los resultados MQR, PRE, POST y Quality Gate se preservan por separado. Los diffs retrospectivos comparan código de producción versionado de la misma herramienta entre etapas. Los reemplazos cuentan como altas y bajas, con pares registrados en soporte. Los movimientos de ruta cuentan como bajas y altas.
- D3 cuenta Markdown para el agente, incluidos documentos heredados que siguen en el árbol. Excluye evidencia, informes de migración y documentación operativa. El libro usa archivos/LOD. El CSV incluye LOD/archivo y cinco números por interpolación inclusiva equivalente a QUARTILE.INC. Se cuentan IDs explícitos solo en su documento de definición. Los conteos bajo criterios alternativos conservan su origen.
- D4 distingue resultados automatizados, revisión manual y afirmaciones del agente. Los fallos, parciales y resultados sin verificar siguen en los informes de soporte. D5 conserva interacciones, correcciones y auditorías en sus formatos históricos.

## Trazabilidad

- [Procedencia por celda](provenance.json) y [manifest de migración](migration_manifest.json).
- [Diff de código](loc_evolution.csv), [distribución de especificaciones](spec_distribution.csv) y [feedback y validación](functional_feedback.json).
- El manifest conserva rutas históricas, destinos canónicos, excepciones operativas y ubicación del respaldo local. Las utilidades de organización se archivaron fuera del repositorio.

Las rutas con prefijo `~/` se resuelven desde la carpeta del usuario que custodia los originales. El manifiesto indexa los exports restringidos mediante su ruta local, su hash y su condici?n de acceso.
