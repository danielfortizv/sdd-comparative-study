# Guion para explicar Tetris, Etapa 1, al profesor asesor

**Duración sugerida:** 10–12 minutos, más preguntas. **Estado:** cinco variantes originales y repetición BMAD de planificación completa verificadas. Presentar esta última como análisis de sensibilidad, no como una sexta herramienta.

## 1. Apertura: pregunta experimental (45 s)

«Profesor, mi parte compara cinco herramientas de desarrollo guiado por especificaciones usando exactamente el mismo caso inicial: un Tetris web. La pregunta no es cuál produjo el juego más vistoso, sino qué esfuerzo, qué documentación y qué calidad de código observamos cuando cada herramienta recibe el mismo alcance funcional. Ejecutamos OpenSpec, GitHub Spec Kit, Tessl, BMAD Method y Kiro en directorios separados. Conservamos la semilla, los artefactos nativos, el código, las pruebas y los resultados de SonarQube para que la comparación sea auditable».

## 2. Control del alcance (1 min)

«Elegimos la opción A de la primera etapa. Exigimos un tablero de 10 por 20, las siete piezas clásicas en su orientación inicial, caída automática cada 500 milisegundos, movimiento a izquierda, derecha y abajo, colisiones, fijación, eliminación de líneas, fin de partida y reinicio. FastAPI conserva en memoria el estado y las reglas; React con TypeScript lo representa. A propósito excluimos rotación, puntaje, persistencia, clasificaciones y demás funciones posteriores. La semilla inglesa fue idéntica para las cinco ejecuciones; guardamos su hash. La instrucción también pedía de 25 a 40 requisitos atómicos y criterios de aceptación observables».

«Eso controla el *qué* se debía construir. No elimina las diferencias del *cómo*: cada herramienta tiene su propio flujo de especificación y algunos servicios de modelo tuvieron reintentos o registros incompletos».

## 3. Qué se midió (1 min)

«Organizamos el análisis en cinco dimensiones. A: esfuerzo y consumo, con tiempo de agente, solicitudes, llamados, tokens y costo teórico cuando hay trazas. B: calidad estática de SonarQube, con LOC sin comentarios, bugs, vulnerabilidades, *code smells*, complejidad, deuda, duplicación y densidad de hallazgos. C: volumen de especificación: archivos, líneas, densidad y relación código/especificación. D: validación funcional. E: intervención humana. D y E se presentan como provisionales porque aún falta aplicar un mismo catálogo de pruebas y cronometrar la revisión humana de igual forma en todos».

## 4. Esfuerzo y consumo (1 min 30 s)

«En el experimento original de Tetris, Kiro registró una invocación de 546 segundos; BMAD dos invocaciones por 1.146 segundos; OpenSpec seis por 3.065; Spec Kit seis por 3.359; y Tessl ocho por 4.901. Son segundos acumulados de invocaciones del agente, excluida la instalación, las pruebas externas y el escaneo. No son horas de trabajo humano. Tessl sufrió respuestas de Vertex 429 y reintentos; BMAD tuvo una corrección para desglosar requisitos; Spec Kit corrigió un escenario de prueba imposible sin rotación. Por eso no atribuyo toda la diferencia de tiempo a la herramienta misma».

«El costo publicado para Gemini es una estimación calculada con el tráfico de tokens observable, no una factura de GCP. Faltan registros de tokens en una sesión de OpenSpec, una de Spec Kit y tres de Tessl; esos totales son mínimos. Kiro no expone en las trazas conservadas tokens y créditos verificables, así que lo dejamos como N/D en costo, en lugar de inventar un valor. Los créditos del proyecto GCP cubren la ejecución, pero no cambian la definición de esta métrica».

«La repetición de BMAD tuvo nueve invocaciones y 3.299,511 segundos de agente, equivalentes a 54,99 minutos. Sus transcripciones registran 17,65 millones de tokens de entrada, 12,53 millones cacheados y 237.579 de salida. Aplicando las tarifas teóricas usadas en la tesis da 11,6984 USD; esa cifra tampoco es un cobro comprobado de GCP. Incluimos el intento fallido de arranque, una parada en modo de planificación y la corrección posterior, porque son parte del esfuerzo real observado».

## 5. Calidad del código (1 min 30 s)

«Las cinco variantes pasaron su *quality gate* de SonarQube. No hubo bugs clásicos ni duplicación en los cinco análisis, pero sí hubo diferencias de seguridad y mantenibilidad. OpenSpec tuvo 1 vulnerabilidad y 15 *smells*; Spec Kit, 2 y 7; Tessl, 1 y 13; BMAD original, 2 y 8; Kiro, 0 y 10. Kiro obtuvo el menor volumen medido, 497 LOC, y la menor complejidad cognitiva, 45, además del rating A/A/A. Sin embargo, como su base de código es pequeña, sus diez hallazgos equivalen a 20,12 por cada mil LOC, la mayor densidad del conjunto. Spec Kit tiene menos hallazgos absolutos, nueve, y la menor deuda estimada, 35 minutos. La cobertura global oscila entre 57,6 % y 72,6 %, pero no la usamos para puntuar esta etapa según el protocolo».

«Incluí un radar con los mismos cinco ejes que la figura de Calculadora. En cada eje, una cifra menor recibe mejor puntuación dentro de Tetris. Bugs y duplicación están empatados en cero, así que esas dos puntas no distinguen herramientas. El radar ayuda a ver el perfil; siempre lo leo junto con los valores originales y la densidad. La normalización de Tetris es independiente de la de Calculadora y no permite comparar los polígonos entre casos».

«La repetición BMAD tiene un análisis SonarQube separado: gate OK, 669 LOC, 0 bugs, 1 vulnerabilidad, 13 smells, 97 de complejidad cognitiva, 84 minutos de deuda, 63,2 % de cobertura global y 0 % de duplicación. Frente a BMAD corto mejoró vulnerabilidades y cobertura, pero empeoraron complejidad, deuda y smells. El flujo documental más largo no garantiza por sí mismo un código estáticamente mejor. La vulnerabilidad restante señala el uso de pseudoaleatoriedad para elegir piezas; requiere interpretación en contexto».

## 6. Especificaciones y BMAD (1 min 30 s)

«Spec Kit fue el más extenso en documentación inicial de Tetris: ocho archivos y 1.002 líneas. OpenSpec produjo cuatro y 442; BMAD original, cuatro y 402; Kiro, tres y 608; Tessl, dos y 136. Más líneas no prueban por sí solas mayor calidad; lo importante es que los requisitos sean verificables y se correspondan con el código y las pruebas. En el caso de BMAD original, tuvimos que convertir capacidades amplias en 30 requisitos atómicos; en Spec Kit se corrigió una prueba incompatible con la prohibición de rotación».

«La comparación con Calculadora reveló una diferencia metodológica importante: allí BMAD aparece con 18 archivos, 1.421 líneas y 4.947 segundos. Tetris original tuvo cuatro archivos, 402 líneas y 1.146 segundos. Verificamos que BMAD 6.12.0 sí estaba instalado correctamente en Tetris; se había elegido la ruta corta `bmad-spec` seguida de `bmad-build`. Reinstalamos la misma versión en un directorio aislado y recorrimos producto, PRD, arquitectura, épicas e historias, y construcción con la misma semilla. La repetición produjo seis documentos principales y 1.120 líneas en 3.299,511 segundos. Esto acerca mucho el volumen de líneas y el tiempo a Calculadora, aunque no reproduce sus 18 archivos ni sus 82 minutos. Las historias están reunidas en un documento de épicas, y no conocemos la regla exacta de conteo ni las trazas crudas del compañero. Por tanto, concluimos que el camino de trabajo explica parte del contraste dentro de Tetris, no que la instalación anterior estuviera mal o que hayamos aislado una causa única para Calculadora».

«En esa repetición revisamos dos veces el alcance: Gemini había añadido objetivos no pedidos de 100 sesiones, 256 MB y latencia p95 de 50 ms; eliminamos esas metas desde los artefactos nativos. Después pasaron 13 pruebas de backend con 98 % de cobertura de ese código, la compilación de React y una verificación independiente de colisiones, fijación, borrado de una a cuatro líneas, API y reinicio. Esta intervención también explica parte del tiempo adicional».

## 7. Validación, límites y cierre (1 min)

«Las suites propias pasaron: 13 pruebas en OpenSpec, 23 entre backend y frontend en Spec Kit, 11 en Tessl, 7 en BMAD original y 39 en Kiro. Cada suite prueba cosas distintas, por lo cual ese 100 % interno no es todavía una tasa de aceptación funcional comparable. Tampoco tenemos una medida homogénea de tiempo de revisión humana o defectos detectados exclusivamente por personas. Registrarlos como N/D es una decisión de rigor, no una ausencia demostrada de defectos».

«Mi conclusión para esta etapa es que las cinco herramientas pudieron producir la funcionalidad inicial, pero dejaron perfiles distintos de documentación, esfuerzo y hallazgos. El dato más útil para el estudio es la trazabilidad: semilla fija, artefactos nativos, código separado, pruebas y SonarQube. La repetición BMAD muestra cuánto cambian tiempo y documentación al usar el flujo completo; también muestra que más planificación no elimina automáticamente hallazgos de mantenibilidad. No atribuimos la diferencia con Calculadora a una instalación defectuosa sin sus trazas originales».

## Respuestas breves a preguntas probables

- **¿Por qué Tetris parece más rápido que Calculadora en BMAD?** «La instalación de Tetris fue válida. La ruta usada fue más corta. La repetición completa pasó de 19,10 a 54,99 minutos y de 402 a 1.120 líneas de especificación, sin llegar a los 82,45 minutos de Calculadora. No tenemos las trazas de Calculadora para aislar versión, instrucciones, reintentos y granularidad de archivos».
- **¿Por qué la repetición solo tiene seis archivos y Calculadora 18?** «BMAD reunió historias en un solo documento; la cantidad de archivos depende de cómo se empaqueten los artefactos. Excluimos memorias de proceso y el estado YAML del conteo. Sin la regla exacta del compañero no presento esa diferencia como prueba de que falten módulos».
- **¿La ruta completa mejoró la calidad?** «La cobertura y el número de vulnerabilidades mejoraron, pero crecieron los smells, la complejidad y la deuda. Informamos todo el perfil, no un ganador automático».
- **¿Quality gate aprobado equivale a código sin problemas?** «No. El gate puede usar condiciones de código nuevo y los conteos globales aún muestran vulnerabilidades y *smells*».
- **¿Por qué Kiro no tiene costo?** «El protocolo conservado no entrega tokens o créditos verificables; asignarle cero sería incorrecto».
- **¿El radar dice que Kiro es universalmente mejor?** «No. Resume cinco recuentos normalizados dentro de Tetris; en densidad de hallazgos Kiro tiene el peor resultado. Tampoco recoge toda la funcionalidad o mantenibilidad».
- **¿Por qué no llaman tasa de aceptación al 100 % de pruebas?** «Porque las suites tienen distinto tamaño y escenarios; falta una batería común aplicada a los cinco productos».

## Evidencia para mostrar en la reunión

1. Semilla `shared/seed.md` y hash en `PROGRESS.md`.
2. Tabla de tiempo y costos observables, explicando los N/D.
3. Tabla SonarQube, radar y tabla Issues/KLOC.
4. Tabla de especificaciones y ejemplo de una corrección de requisito.
5. Repositorio público `Tetris/Etapa 1`, con artefactos separados por herramienta, y repetición aislada en `Bmad Method Full/`.
6. Auditoría `shared/report/auditoria-bmad-calculadora-tetris.md`, métricas `shared/bmad-full-metrics.json`, trece pruebas y SonarQube `tetris-stage1-bmad-full`.
