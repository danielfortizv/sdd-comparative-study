# Shift Bank — Stage 2 OpenSpec: cierre experimental

## Estado
Stage 2 queda congelado como baseline reproducible para Stage 3. En este cierre no se cambió código de aplicación ni especificaciones. stage2-banking-enhancements permanece 22/22 tasks, strict validation válida, no archivado ni sincronizado. No se creó commit.

Verificación repetida: 22 backend tests aprobados; 5 frontend tests aprobados; production build aprobado (TypeScript + Vite 5.4.21; 33 módulos); OpenSpec strict validation aprobada. Las especificaciones contienen 91 escenarios, no 91 tests ejecutados.

A01–A21: 15 PASS, 5 PARTIAL, 0 FAIL, 1 NOT EXECUTED. A21 no tuvo prueba de navegador.

## SonarQube
Inicial 74358b40-4391-4280-83df-9ae09061e287; final 5631177d-e954-42db-9a1f-795a50645944; CE final 8cb5713c-6066-44c0-b59a-84f90403a1c7. Ambos gates OK. Bugs 5, code smells 41 y deuda sqale 246 minutos no cambiaron. Coverage 0.0 no prueba que los tests no ejecutaron código: no se importó reporte usable. Sin scans adicionales.

## Especificaciones e inventario
Hay 11 archivos spec.md: 4 main heredados y 7 deltas. Tamaño total 44327 bytes, 552 líneas físicas; 22 requisitos delta y 91 escenarios delta. La suma literal de headings main+delta es 31 requisitos y 104 escenarios, contados en archivos separados (no implica requisitos independientes adicionales).

El manifiesto final contiene 50 rutas de código, tests, OpenSpec, config y skills OpenSpec. Clasificación por SHA contra E2_OPENSPEC_BASELINE_SHA256.csv: new=26; modified=5; unchanged=19; deleted=0. Excluye outputs generados, dependencias, cachés, DB runtime y otros SDD tools.

El baseline disponible preserva hashes y tamaños, no contenido completo de todos los archivos Stage 1. No se inventan diffs por línea ni LOC añadidas/eliminadas; ncloc/lines de Sonar no se usan como sustituto. No se leyeron archivos de Stage 1 para reconstruirlos.

## Desviaciones y limitaciones
- Codex CLI 0.168.0 sustituyó el Gemini CLI del plan original.
- OpenSpec observado 1.11.0 frente a preparación 1.9.0.
- Sin telemetría confiable de tokens, costos, llamadas totales, número/duración global de sesiones o runtimes de agentes.
- A21 manual/browser no ejecutado; A03/A05/A10/A12/A15 parciales.
- No disponibles descripciones individuales de los cinco bugs y 41 code smells.
- Contrato local A01–A21 no localizado; se usó el mapping provisto.
- Migración probada sobre fixture SQLite Stage 1, no DB histórica real.
- No archive/sync por falta de autorización explícita.

## Evidencia
E2_OPENSPEC_AUDITORIAS_CORRECCIONES.md; E2_OPENSPEC_SONAR_COMPARACION_FINAL.md; E2_OPENSPEC_ESPECIFICACIONES_FINAL.csv; E2_OPENSPEC_TELEMETRIA.md; E2_OPENSPEC_VALIDACION_MANUAL.md; E2_OPENSPEC_INVENTARIO_FINAL_SHA256.csv; este cierre; raw Sonar en sonarqube/; snapshots V1/V2 en especificaciones/.
