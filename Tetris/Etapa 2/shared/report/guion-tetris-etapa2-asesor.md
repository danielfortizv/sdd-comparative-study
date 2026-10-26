# Guion breve para el asesor — Tetris, etapa 2

**Autor:** Kevin Alvarez. **Duración:** aproximadamente 2–3 minutos.

## Explicación sugerida

«Profesor, mi caso de estudio es Tetris y en esta segunda etapa evalué cómo las cinco herramientas —OpenSpec, Spec Kit, Tessl, BMAD y Kiro— evolucionan una aplicación que ya existe. En la primera etapa construimos el juego básico; ahora cada herramienta continuó desde su propia versión anterior, manteniendo el backend FastAPI y el frontend React con TypeScript».

«La ampliación agregó puntuación, niveles, aumento de velocidad, vista previa de la siguiente pieza y la función Hold para guardar e intercambiar una pieza. Por ejemplo, al llegar a diez líneas el juego pasa al nivel dos y la gravedad cambia de 500 a 450 milisegundos. La rotación y la persistencia siguen fuera de este alcance».

«Usé la misma semilla de instrucciones en inglés, identificada por su hash, y un catálogo común de veinte criterios. Revisé tanto las reglas del servidor como el comportamiento del cliente: que Hold no pueda repetirse antes de fijar una pieza, que un reinicio no reciba respuestas antiguas y que el temporizador respete el nivel. Los veinte criterios quedaron respaldados en las cinco herramientas, pero algunos se validan con pruebas de dominio, otros con API, React, navegador o compilación. Las reglas de tres y cuatro filas se comprueban con estados preparados; no las presento como partidas normales».

«Registré tiempos, tokens, caché, reintentos y correcciones. En total quedaron documentados 49 intentos. Para Kiro reporto créditos porque sus registros no ofrecen tokens acumulados verificables; los datos que faltan se mantienen como no disponibles. También medí el código y las especificaciones, y utilicé SonarQube. Las cinco versiones aprobaron el gate experimental: al menos 80 % de cobertura del código nuevo, máximo 3 % de duplicación nueva y cero incidencias nuevas. Eso no significa que todo el código esté libre de hallazgos heredados».

«El resultado principal es una comparación trazable de cómo cada flujo maneja una ampliación real. No puedo afirmar que una herramienta sea siempre mejor: las bases heredadas, los reintentos y las intervenciones fueron distintos. Por eso dejé documentadas las limitaciones y las correcciones manuales, y consolidé las tablas, gráficas y capturas en la tesis».

## Si pregunta por detalles

- **¿Misma semilla significa mismas piezas?** No. Se congeló el mismo texto de instrucciones; cada aplicación conservó su generador heredado. Para verificar reglas específicas se usaron fixtures y secuencias controladas. Kiro mantuvo su bolsa de siete piezas con semilla 20260929.
- **¿Qué hallazgos quedaron en Sonar?** OpenSpec y Spec Kit finalizaron sin bugs, vulnerabilidades ni olores reportados. Tessl conserva una vulnerabilidad y nueve olores; BMAD, una y doce; Kiro, siete olores. El gate de código nuevo y los hallazgos totales son medidas distintas.
- **¿Cómo quedaron las coberturas?** Cobertura global Sonar: OpenSpec 90,3 %; Spec Kit 83,9 %; Tessl 86,9 %; BMAD 89,6 %; Kiro 93,2 %. Cobertura de código nuevo: 83,0 %; 86,6 %; 82,7 %; 85,8 % y 88,7 %, respectivamente. No se deben confundir con la cobertura exclusiva de backend o frontend.
- **¿Se generó todo automáticamente?** No de forma estricta. OpenSpec incluyó un ajuste manual de dos literales de código y pruebas del investigador. También quedaron registradas desviaciones de revisión previa de specs en Tessl y Kiro, reintentos de BMAD y una corrección de su XML de cobertura. No se atribuye ese trabajo íntegramente a la herramienta.
- **¿Es el costo real pagado?** No. Los tokens y créditos son los observados; el escenario económico del documento usa coeficientes de referencia y no equivale a una factura completa. El tiempo instrumentado tampoco es tiempo humano ni duración calendario.

## Qué mostrar durante la reunión

1. El apartado **9.3.2, Caso de Estudio 2.2: Tetris Web**, en el [proyecto de Overleaf](https://www.overleaf.com/project/6a99e23073b642f16984b2ff).
2. La tabla de condiciones de código nuevo y la gráfica de cobertura, para diferenciar calidad global y ampliación.
3. Una captura de Hold y el fixture de paso a nivel dos, para conectar los requisitos con un resultado visible.
4. El [registro de métricas y evidencias en Drive](https://docs.google.com/document/d/1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao) si se requiere la trazabilidad completa.

Los porcentajes y límites proceden de los cierres verificados de la etapa 2, con corte de consolidación del 26 de octubre de 2026. Este guion no incorpora nuevos experimentos ni nuevos consumos a los resultados históricos.
