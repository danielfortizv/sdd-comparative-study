# Tessl — Etapa2, opciónA: informe del investigador

Implementación local aceptada contra el catálogo común de20criterios, con los mecanismos y límites de este informe. Sin commits ni push.

## Verificación final

- Backend23/23, frontend17/17, dominio17/17, HTTP7/7 registros y contrato9/9controles; concurrencia6/6 +caso adicional1/1.
- Sonar gateOK, análisis `15649d89-fd29-4e66-a610-0f15d72066a3`; cobertura nueva82.7%, duplicación nueva0%, incidencias nuevas0.
 - Instalación desde lockfile, build y auditorías completa/producción aprobadas. Fuente y XML/LCOV vinculados por SHA-256.

## Métricas cerradas

CLI conocido: 3642.237s. Tokens: {"input_tokens": 39704775, "cached_tokens": 32103483, "output_tokens": 120725, "thought_tokens": 149603}. Entrada incluye caché. API: {"api_requests": 400, "api_errors": 53, "api_successful_requests": 347}. Intento02sin contadores, nunca sustituido por cero.
Correcciones externas: 3 intentos para 2 objetivos(Q01/Q02).

## Catálogo común

| Criterio | Resultado | Mecanismo |
|---|---|---|
| S2-01 | PASS | api.json / domain.json |
| S2-02 | PASS | api.json / domain.json |
| S2-03 | PASS | api.json / domain.json |
| S2-04 | PASS | domain.json |
| S2-05 | PASS | domain.json |
| S2-06 | PASS | Fixture aislado de filas completas |
| S2-07 | PASS | Fixture aislado de filas completas |
| S2-08 | PASS | domain.json |
| S2-09 | PASS | domain.json |
| S2-10 | PASS | api.json / domain.json |
| S2-11 | PASS | api.json / domain.json |
| S2-12 | PASS | api.json / domain.json |
| S2-13 | PASS | domain.json |
| S2-14 | PASS | domain.json |
| S2-15 | PASS | api.json / domain.json |
| S2-16 | PASS | api.json / contract.json |
| S2-17 | PASS | browser-hold-button.ax.txt / browser-hold-key.ax.txt / final-hold-key.jpg / final-hud-button.jpg |
| S2-18 | PASS | falsey-vitest.json / final-threshold-fixture.jpg / races-vitest.json |
| S2-19 | PASS | backend.stdout.log / domain.json / frontend-vitest.json |
| S2-20 | PASS | build.stdout.log |

## Límites y procedencia

- Production pieces.py keeps inherited unseeded random.choice; common seed means identical prompt. Researcher fixtures use20260929/explicit canonical sequences.
- Tessl remote skill search unauthenticated; actual pinned local MCP/plugin workflow retained, no invented native generator.
- Historical CLI auxiliary loop detector used gemini-3-flash-preview in05/07; main model3.5Flash; aliases corrected in08. Past calls not erased.
- 02token/APIcounters unavailable after BILLING_DISABLED; known totals are not a complete billing total.
- Internal05/07fixes without prior spec revision are recorded workflow deviations; initial spec-before-code order alone is not blanket compliance.
- Four qa02-command.txt summaries contain model-authored timing metadata; not used as authoritative measurements.
- Native session_notes retains an old present-tense ERROR paragraph despite completed checkboxes; final exact-task JSON is authoritative. Document quality is not declared perfect.
- Sonar retains inherited S2245 game PRNG vulnerability and9smells; newviolations0 does not mean zero total findings.
- No Sonar scalability score or BERTopic model score is invented; corpus is prepared for later analysis.
- Inherited browser tab title and welcome message still mentionStage1; visible application HUD identifiesStage2. Cosmetic legacy labels are retained.

## Archivos principales

- `final-acceptance.json`:criterios y vínculos exactos.
- `metrics.json`:contadores por sesión/modelo, diffs y densidades.
- `native-command-index.json`:salidas originales y notas de medición adjudicadas.
- `RESEARCH_LOG.md`:cronología, incidentes y desviaciones.
- `bertopic-corpus/`:Markdown separado/unificado, sin modelado.

La bitácora central de Drive conserva tablas, capturas, fallos y controles. No se han añadido credenciales a los informes.
