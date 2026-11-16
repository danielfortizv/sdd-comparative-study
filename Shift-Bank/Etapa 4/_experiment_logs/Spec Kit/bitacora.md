### E4-SK-01 — Inspección inicial y preparación de Gate A
**Fecha:** 16 de noviembre de 2026
**Estado:** Prompt preparado; ejecución pendiente.

**Objetivo:** Verificar la línea base de Spec Kit E4 y preparar la decisión humana sobre incompatibilidades monetarias y contractuales antes de generar especificaciones.

**Acciones ejecutadas:**
- Revisión investigadora de SEED-4 y del paquete preparatorio.
- Identificación del conflicto COP/USD y de aprobaciones pendientes.
- Elaboración del primer prompt de inspección de solo lectura para Codex.
- Sin ejecución de Codex ni modificación del proyecto durante este hito.

**Resultados verificables:**
- Preparación previa: 105/105 archivos reportados como verificados por SHA-256; comprobación independiente por Codex pendiente.
- Especificaciones funcionales E4 nuevas: ninguna acreditada.
- Pruebas E4: no ejecutadas en este hito.
- Gate A: pendiente.

**Problemas y correcciones:**
- Divergencia documentada entre saldos/umbrales COP de E3 y la referencia USD de D-02/D-07.
- Aprobación completa de D-01–D-14 no acreditada.
- Procedencia de la semilla original pendiente de cotejo.
- Correcciones aplicadas: ninguna.

**Evidencias:**
- Paquete SHIFT_BANK_E4_SPECKIT_PREPARACION.
- Documentos de preparación de GitHub Copilot.
- Prompt E4-SK-01.
- Salida de Codex: pendiente.

**Implicaciones D1–D5:**
- D1: consumo, tiempo, mensajes y herramientas Codex E4: N/D hasta ejecución.
- D2: línea base histórica disponible; calidad E4 no medida.
- D3: sin especificaciones E4 nuevas.
- D4: requisitos REQ-01–REQ-06 todavía no verificados.
- D5: bloqueos identificados para revisión humana; sin correcciones implementadas.

**Decisión humana:** Gate A no aprobado. Se solicita inspección independiente antes de resolver las reglas contractuales.

**Próximo paso:** Ejecutar E4-SK-01, revisar evidencia y decidir la reconciliación COP/USD y aprobación D-01–D-14.

### E4-SK-01 — Auditoría inicial de línea base y Gate A
**Fecha:** 16 de noviembre de 2026
**Estado:** Inspección finalizada. Gate A pendiente.

**Objetivo:** Comprobar la integridad de la copia E4 de Spec Kit, identificar las diferencias entre el legado E3 y SEED-4 y preparar decisiones humanas antes de especificar.

**Acciones ejecutadas:**
- Inspección de repositorio, código, especificaciones y evidencias preparatorias.
- Verificación independiente de 105 hashes SHA-256.
- Comparación de contratos monetarios, límites, MFA, ACH, seguridad y arquitectura.
- Revisión de D-01–D-14 y su estado de aprobación.
- Inspección de configuración Spec Kit y versión de Codex.
- Comparación adicional del SEED-4 preparado contra el Anexo A de la guía de replicación por el supervisor.

**Resultados verificables:**
- 105/105 archivos coincidentes; 1.279.387 bytes.
- E3 heredada usa cuentas COP 5.000.000 y COP 15.000.000.
- Conflictos reales con D-02, D-07 y tratamiento de COP en D-01/D-08.
- Spec Kit 1.0.6; Codex CLI 0.168.0.
- Proyecto configurado inicialmente con integración Gemini.
- SEED-4 coincide exactamente con el anexo de la guía salvo el salto de línea final.
- Ninguna prueba E4 ejecutada y ninguna modificación funcional realizada.

**Problemas y correcciones:**
- Incompatibilidad contractual COP/USD: sin resolver.
- Aprobaciones originales D-01–D-14: no acreditadas.
- Configuración Codex/Spec Kit: pendiente de adecuación.
- Algunos comandos de inspección fallaron por rutas ausentes y política PowerShell; la verificación SHA-256 sí se completó.
- Correcciones funcionales: ninguna.

**Evidencias:**
- Salida completa de Codex E4-SK-01.
- BASELINE_FILES_SHA256.tsv.
- PREPARACION_E4_SPECKIT.md.
- D01_D14_PENDING_REVIEW.md.
- SEED-4.md y Anexo A de la guía de replicación.
- Referencias de código y contratos E3 señaladas por Codex.

**Implicaciones D1–D5:**
- D1: Codex reportó 4 min 29 s de trabajo; tokens, costo, llamadas totales y modelo efectivo N/D.
- D2: línea base inspeccionada; métricas de calidad E4 todavía N/D.
- D3: cero especificaciones E4 nuevas; métricas formales pendientes.
- D4: REQ-01–REQ-06 no verificados en E4; conflictos de compatibilidad documentados.
- D5: discrepancias contractuales y bloqueo de integración identificados; aprobación humana requerida, sin retrabajo funcional.

**Decisión humana:** Mantener Gate A bloqueado. La alternativa 3 de preservación del legado COP fue recomendada, pero no aprobada. Se autoriza continuar únicamente con la preparación técnica no funcional de la integración Codex.

**Próximo paso:** E4-SK-02 — adecuación y validación de integración nativa Codex, seguida de revisión humana de Gate A.

