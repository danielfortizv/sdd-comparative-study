# Guion para presentar Tetris, Etapa 1

**Duración sugerida:** 10–12 minutos. **Comparación vigente:** cinco herramientas; BMAD corresponde únicamente al flujo de planificación completa.

## 1. Pregunta y diseño experimental

«Profesor, comparamos OpenSpec, GitHub Spec Kit, Tessl, BMAD Method y Kiro con la misma semilla en inglés y la misma opción A de Tetris. Cada herramienta tiene su propio directorio, especificaciones nativas, aplicación, pruebas y datos de SonarQube. Queremos describir esfuerzo, documentación, calidad estática y límites de la evidencia, no declarar un ganador absoluto».

«El producto común tiene tablero de 10 × 20, siete piezas clásicas en orientación inicial, gravedad cada 500 ms, flechas izquierda, derecha y abajo, colisiones, fijación, borrado de líneas, fin de partida y reinicio. El backend FastAPI mantiene el estado en memoria y React con TypeScript presenta el tablero. No incluye rotación, puntuación ni persistencia. Guardamos el hash SHA-256 de la semilla para auditar el alcance».

## 2. Método de medición

«La dimensión A comprende invocaciones, tiempo acumulado del agente, tráfico de tokens y costo teórico; no incluye instalación, pruebas externas ni escaneo. La B usa medidas originales de SonarQube: LOC, bugs, vulnerabilidades, *code smells*, complejidad, deuda, duplicación y cobertura. La C cuenta documentos y líneas de especificación, su densidad y la relación código/spec. Las dimensiones D y E de validación funcional e intervención humana siguen provisionales porque todavía no aplicamos una batería de aceptación ni un cronometraje humano común a las cinco variantes».

«Gemini CLI usó Vertex AI con los créditos del proyecto GCP autorizado. El costo presentado resulta de tarifas y tokens observables; no es la factura del proyecto. En OpenSpec falta una traza de tokens, en Spec Kit una y en Tessl tres, de modo que sus totales son mínimos. Kiro no dejó tokens o créditos verificables y se muestra N/D».

## 3. Esfuerzo y especificación

«Los tiempos acumulados son: Kiro 9,10 minutos; OpenSpec 51,08; Spec Kit 55,98; BMAD 54,99; Tessl 81,68. BMAD recorrió *product brief*, PRD, arquitectura, épicas e historias, implementación y corrección del alcance. Sus nueve invocaciones suman 3.299,511 segundos, incluidos un intento de inicio fallido y una continuación sin producción. Las 19 transcripciones muestran 17.653.626 tokens de entrada, 12.533.513 cacheados, 237.579 de salida y 342 llamadas a herramientas; el costo teórico es 11,6984 USD».

«BMAD produjo seis documentos principales, 1.120 líneas físicas y 30 identificadores funcionales únicos en el PRD. Dos memorias de proceso y el estado YAML del sprint quedan fuera del conteo de especificación. En comparación, Spec Kit produjo ocho archivos y 1.002 líneas; OpenSpec cuatro y 442; Tessl dos y 136; Kiro tres y 608. Más líneas describen mayor volumen, no demuestran automáticamente mejor calidad o conformidad».

«La comparación con Calculadora requiere cautela: allí se reportan 18 archivos y una duración distinta, pero la granularidad de historias y el registro de sesiones del compañero no son idénticos a los nuestros. Nuestra evidencia demuestra el resultado del flujo completo de BMAD en Tetris; no permite atribuir toda diferencia a la herramienta por sí sola».

## 4. Calidad y radar

«Las cinco variantes pasaron el *quality gate* observado. Todas tuvieron cero bugs y cero duplicación, pero conservan hallazgos. OpenSpec: 1 vulnerabilidad, 15 *smells*, 76 de complejidad y 60,2 % de cobertura global. Spec Kit: 2, 7, 78 y 62,0 %. Tessl: 1, 13, 69 y 60,4 %. BMAD: 1, 13, 97 y 63,2 %. Kiro: 0, 10, 45 y 72,6 %. La cobertura global del escáner no debe confundirse con la cobertura de pruebas de backend».

«En BMAD SonarQube midió 669 LOC, 84 minutos de deuda y 20,93 hallazgos clásicos por mil LOC. Sus 13 pruebas de backend pasaron, con 98 % de cobertura de ese módulo; el frontend compiló y una verificación independiente ejercitó colisiones, fijación, borrado de una a cuatro líneas, rutas HTTP y reinicio. Quedó una vulnerabilidad relacionada con pseudoaleatoriedad; debe interpretarse según el uso real de la selección de piezas».

«El radar emplea cinco ejes y normaliza dentro de Tetris: bugs, vulnerabilidades, *code smells*, complejidad cognitiva y duplicación. El exterior significa menor valor observado. Bugs y duplicación empatan en cero en las cinco variantes y no distinguen resultados. El radar acompaña a los números originales; tampoco se puede comparar directamente con el radar normalizado por separado para Calculadora».

## 5. Validación, intervención y conclusión

«Las suites propias pasaron: OpenSpec 13 pruebas backend, Spec Kit 18 backend y 5 frontend, Tessl 9 backend y 2 frontend, BMAD 13 backend y Kiro 39 backend. Cada suite tiene distinto tamaño y escenarios; ese éxito interno no constituye todavía una tasa de aceptación funcional comparable. El tiempo de revisión humana y los defectos detectados exclusivamente por personas siguen como N/D hasta medirlos con un protocolo uniforme».

«El resultado principal es una comparación auditable de cinco rutas sobre el mismo alcance. BMAD, en su flujo completo, generó el mayor volumen de especificación y consumió un tiempo comparable a OpenSpec y Spec Kit, pero también mostró la mayor complejidad cognitiva estática. Debemos leer esfuerzo, documentación, pruebas y calidad juntos y mantener explícitos los límites de la medición».

## Preguntas probables

- **¿Por qué BMAD tiene seis documentos y Calculadora 18?** La cantidad depende de cómo se agrupan historias y otros artefactos. En Tetris las épicas e historias están reunidas; excluimos memorias de proceso y YAML. Sin una regla de conteo idéntica, el número de archivos no demuestra que falte un módulo.
- **¿El gate OK implica ausencia de defectos?** No. El gate puede evaluar condiciones de código nuevo y el conjunto conserva vulnerabilidades y *smells*.
- **¿Por qué Kiro no tiene costo?** Sus trazas conservadas no dan tokens o créditos comprobables. N/D evita asumir cero.
- **¿El 100 % de pruebas exitosas es aceptación común?** No. Se necesita ejecutar los mismos casos sobre las cinco variantes.
- **¿Por qué BMAD tiene una vulnerabilidad?** SonarQube señala pseudoaleatoriedad; corresponde revisar si la elección de piezas requiere aleatoriedad criptográfica en este caso.

## Evidencia para abrir durante la reunión

1. `shared/seed.md` y `shared/bmad-metrics.json`.
2. `shared/report/Tetris-Etapa-1-comparacion.pdf`: páginas de Tetris extraídas de la tesis compilada, con tablas y radar actualizados.
3. `Bmad Method/_bmad-output/`: seis documentos principales de planificación e implementación.
4. `Bmad Method/docs/`: pruebas, compilación, escaneo, calidad y métricas JSON de SonarQube.
5. [Proyecto de Overleaf](https://www.overleaf.com/project/6a99e23073b642f16984b2ff) y [repositorio](https://github.com/danielfortizv/sdd-comparative-study/tree/main/Tetris/Etapa%201).
