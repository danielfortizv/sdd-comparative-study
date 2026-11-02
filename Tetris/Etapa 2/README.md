# Tetris - Etapa 2: complejización

**Responsable:** Kevin Alvarez. **Corte:** 26 de octubre de 2026.

Cinco ampliaciones independientes de Tetris a partir de la implementación de etapa 1 de cada herramienta. La opción A agrega puntuación, nivel, gravedad variable, siguiente pieza y Hold, preservando FastAPI autoritativo en memoria y React/TypeScript. Rotación y persistencia siguen fuera del alcance.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `OpenSpec/` | Código, pruebas, cambio OpenSpec y evidencia medida. |
| `Spec Kit/` | Código, pruebas, feature nativa de Spec Kit y evidencia medida. |
| `Tessl/` | Código, pruebas, especificaciones, plugins/contexto y evidencia medida. |
| `Bmad Method/` | Código, pruebas, PRD/diseño/épicas/historias y evidencia medida. |
| `Kiro/` | Código, pruebas, requirements/design/tasks y evidencia medida. |
| `shared/seed.md` | Semilla común congelada. |
| `shared/protocol.md` y `shared/acceptance/` | Protocolo, catálogo común y verificadores del investigador. |
| `shared/report/` | Guion para el asesor, consolidación LaTeX, extracto PDF, gráficas, capturas y métricas. |
| `publication-manifest.json` | Inventario y hashes de lo exportado, más exclusiones explicadas. |

## Resultados finales

| Herramienta | Intentos | Backend / frontend propios | Cobertura global Sonar | Cobertura nueva | Gate experimental |
| --- | ---: | ---: | ---: | ---: | --- |
| OpenSpec | 10 | 20 / 5 | 90,3 % | 83,0 % | OK |
| Spec Kit | 17 | 35 / 38 | 83,9 % | 86,6 % | OK |
| Tessl | 8 | 23 / 17 | 86,9 % | 82,7 % | OK |
| BMAD | 7 | 18 / 14 | 89,6 % | 85,8 % | OK |
| Kiro | 7 | 120 / 49 | 93,2 % | 88,7 % | OK |

Los veinte criterios comunes tienen evidencia final en cada herramienta mediante mecanismos distintos. Las reglas de tres/cuatro filas se acreditan con fixtures de dominio; no se presentan como veinte partidas de navegador. Los tamaños de suite no constituyen un ranking. Kiro conserva además una regresión original marcada xfail por la ampliación intencionada del contrato.

El gate exige cobertura nueva >=80 %, duplicación nueva <=3 % y cero incidencias nuevas. Tessl, BMAD y Kiro conservan hallazgos heredados. La entrada incluye caché; pensamiento y salida candidata son contadores separados. Faltantes de tokens, API o duración siguen N/D. Kiro tiene créditos conocidos, pero no tokens acumulados verificables. El costo normalizado de la tesis no es una factura.

Las intervenciones y limitaciones se describen en los informes de cada herramienta y en la sección consolidada: ajuste manual de código en OpenSpec, incidencias de entrega/reintentos en Spec Kit, revisiones sin spec previa en Tessl/Kiro, adaptación de revisión de BMAD y regeneración de su XML de cobertura sobre fuente congelada. No se atribuye todo el proceso exclusivamente al modelo.

## Cómo consultar y reproducir

1. Leer [`shared/report/guion-tetris-etapa2-asesor.md`](shared/report/guion-tetris-etapa2-asesor.md) para una explicación de 2–3 minutos.
2. Abrir [`shared/report/Tetris-Etapa-2-comparacion.pdf`](shared/report/Tetris-Etapa-2-comparacion.pdf) o la fuente `tetris-etapa2-overleaf.tex` y sus assets. El extracto contiene las páginas físicas 111–134 del PDF consolidado. La tesis completa permanece en Overleaf.
3. Consultar `docs/metrics.json`, `docs/sonar-summary.json`, las condiciones de gate, matrices de aceptación e informes finales por herramienta. OpenSpec documenta su cierre en `docs/RESEARCH_LOG.md`.
4. Crear un entorno Python por herramienta a partir de sus manifiestos `requirements*.txt` o `pyproject.toml`. Instalar el frontend con `npm ci` desde su carpeta y usar sus scripts `npm test`/`npm run build`. No se incluye un entorno virtual preinstalado.
5. Para compilar la sección por separado, ejecutar un compilador LaTeX sobre `shared/report/tetris-etapa2-autonomo.tex` desde esa carpeta. Las gráficas son PDFs vectoriales y las capturas son las evidencias originales seleccionadas.

Los helpers históricos preservan sus rutas de trabajo registradas y pueden requerir configurar la raíz del experimento. No deben ejecutarse masivamente sin revisar sus argumentos. Los resultados medidos no se recalcularon al publicar. `coverage-final.lcov` copia, sin cambios de bytes, el LCOV final de cada frontend disponible.

Ejecutar `python shared/verify-publication.py` verifica los hashes de esta copia, la semilla, los 49 intentos y los contadores archivados sin conectarse a servicios ni consumir créditos. No vuelve a ejecutar las pruebas de las aplicaciones.

## Alcance de esta publicación

Se exportan fuentes, artefactos nativos, prompts, metadatos de invocación, estadísticas observadas, auditorías, pruebas, logs, JSON de Sonar, capturas e informes. Se preservan los registros de fallos y los estados intermedios disponibles. Los códigos fuente y las evidencias seleccionadas conservan sus bytes; los hashes históricos se refieren a los originales con su alcance declarado.

Los perfiles de autenticación/navegador, instaladores, dependencias, cachés, archivos de estado y transcritos completos JSONL se conservan localmente. Algunos transcritos superan el límite de GitHub y repiten grandes capturas/contextos; las estadísticas y auditorías derivadas sí forman parte de este snapshot. Las copias completas de la tesis/bitácora PDF se sustituyen aquí por el extracto específico y enlaces a las fuentes. Las exclusiones quedan enumeradas en el manifiesto; no se eliminaron originales ni se presentó la exportación como archivo bruto íntegro.

Los monitores personales de cuota y suspensión no pertenecen al caso de estudio y no se publican ni se reactivan.

## Fuentes

- [Bitácora y métricas de las cinco herramientas](https://docs.google.com/document/d/1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao)
- [Definición del estudio](https://docs.google.com/document/d/1Fi7XAKY2Cd379spmq7ggxgoE0rEjKx6pq66hTdLj-6c)
- [Tesis en Overleaf](https://www.overleaf.com/project/6a99e23073b642f16984b2ff)
