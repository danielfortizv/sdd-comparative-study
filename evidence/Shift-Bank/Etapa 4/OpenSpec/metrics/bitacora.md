# E4_OPENSPEC_REGISTRO_01_PREPARACION.md

## 1. Identificación

**Proyecto:** Shift Bank — Estudio comparativo de herramientas SDD  
**Etapa:** 4 — Migración arquitectónica y funcional  
**Herramienta SDD:** OpenSpec  
**Agente de desarrollo:** Codex CLI  
**Iteración:** 01 — Preparación independiente y congelamiento inicial de línea base  
**Fecha de revisión:** 18 de noviembre de 2026  
**Estado:** Parcialmente verificada; cierre H0 pendiente.

## 2. Objetivo

Preparar un entorno de trabajo independiente para la evolución de Shift Bank desde su implementación OpenSpec de Etapa 3, preservando los archivos heredados y estableciendo una línea base reproducible de arquitectura, pruebas y especificaciones, previa a cualquier modificación de Etapa 4.

## 3. Procedimiento ejecutado

Según los registros entregados, el agente preparó una copia de la implementación OpenSpec E3 en el directorio correspondiente a E4. Se generaron un inventario de archivos, un manifiesto de hashes SHA-256 y documentos descriptivos del estado inicial.

Posteriormente se ejecutó la regresión backend mediante unittest, se intentó ejecutar la regresión frontend y su compilación, y se invocó la validación estricta de OpenSpec.

Finalmente, se inspeccionó la arquitectura heredada para identificar los contratos relevantes y las incompatibilidades iniciales con la evolución multimoneda.

La revisión académica examinó los archivos `inventory.md`, `frozen-baseline-discovery.md` y `backend-tests-output.txt`, además de contrastar sus afirmaciones con la guía de replicación de Etapa 4.

## 4. Inventario y preservación

El inventario reporta la inclusión de 80 archivos, equivalentes a 441.008 bytes, procedentes de las carpetas de backend, frontend, despliegue y OpenSpec.

El documento declara coincidencia de hashes SHA-256 para todos los archivos copiados y ausencia de modificaciones sobre E3.

Se excluyeron archivos de ejecución, dependencias instaladas, compilados, entornos virtuales, bases de datos SQLite y archivos auxiliares WAL/SHM, así como credenciales privadas y registros experimentales históricos.

No se recibió el manifiesto JSON original para su cotejo independiente. Por tanto, la igualdad de hashes queda documentada como resultado del procedimiento de Codex, pendiente de verificación primaria.

## 5. Resultados de las pruebas

| Verificación | Resultado observado | Interpretación |
|---|---|---|
| Backend unittest | 54/54 PASS | Regresión satisfactoria |
| Frontend | 8/9 PASS | Regresión incompleta |
| Build frontend | No ejecutable por ausencia de `tsc` | Bloqueo ambiental |
| Validación OpenSpec | `Nothing to validate` | Validación global no demostrada |

La salida original del backend registra 54 pruebas exitosas en 8,054 segundos. El resumen de descubrimiento consigna 8,096 segundos, discrepancia que deberá conservarse para su trazabilidad.

La prueba frontend fallida y el bloqueo de compilación se atribuyeron a dependencias no instaladas en el entorno aislado. No se dispone todavía de una segunda ejecución que confirme la recuperación.

La invocación de validación OpenSpec no proporcionó evidencia suficiente sobre la validez integral de las especificaciones heredadas.

## 6. Descubrimiento arquitectónico

La aplicación heredada utiliza FastAPI, SQLite, React y TypeScript. Implementa transferencias internas, transferencias ACH simuladas, programaciones recurrentes, límites dinámicos y autenticación multifactor simulada.

También incorpora cifrado de información sensible, auditoría encadenada y mecanismos transaccionales para preservar consistencia financiera.

El almacenamiento utiliza SQLite y el código de inicialización dispone de mecanismos de migración incremental. La aplicación heredada no presenta todavía un modelo explícito de moneda por cuenta.

Se identificó que las funcionalidades multimoneda, conversiones FX, Event Sourcing y CQRS requerirán modificaciones coordinadas del modelo de datos, las operaciones financieras, las interfaces HTTP, la presentación y las pruebas.

Estas modificaciones no fueron ejecutadas durante la iteración.

## 7. Incompatibilidad de datos heredados

El descubrimiento identificó dos cuentas inicializadas con identificadores `acc_checking` y `acc_savings`, cuyos importes son 5.000.000,00 y 15.000.000,00, respectivamente.

El modelo no registra una divisa explícita, aunque existen referencias a COP en el frontend y en las pruebas. Por ello, la interpretación de los importes como COP es una hipótesis respaldada por indicios del código, pero todavía requiere confirmación contractual.

La decisión común D-02 establece, en cambio, cuentas `CHK-1001` y `SAV-2001`, denominadas en USD, con saldos de 2.500,00 y 10.000,00.

Esta diferencia impide aplicar literalmente la decisión común sin resolver previamente la conservación del valor financiero, los identificadores y el historial heredado.

No se autorizó ninguna transformación de datos ni modificación de los saldos iniciales.

## 8. Intervenciones humanas

La intervención del investigador consistió en solicitar una revisión de las evidencias generadas, contrastar los resultados con el procedimiento común y establecer que no se avanzaría hacia la implementación antes de resolver las incompatibilidades materiales.

Se mantuvo explícitamente la restricción de no reinterpretar importes COP como USD, no inventar tasas de migración y no modificar la implementación heredada.

El análisis identificó la necesidad de una autorización humana específica para la futura política de migración.

## 9. Problemas y limitaciones

La preparación presenta las siguientes limitaciones:

1. El manifiesto SHA-256 no fue recibido para verificación independiente.
2. La regresión frontend y la compilación permanecen incompletas.
3. La validación global de OpenSpec no ha sido acreditada.
4. La equivalencia de la copia de SEED-4 con la fuente canónica sigue pendiente de comprobar.
5. Existe una incompatibilidad material entre el modelo de cuentas OpenSpec heredado y D-02.
6. No se dispone de evidencia primaria suficiente para cerrar todas las condiciones de reproducibilidad del entorno.

La existencia de archivos de resultados no se considera equivalente a la finalización satisfactoria de todas las verificaciones.

## 10. Interpretación académica

La iteración permite establecer una primera línea base de regresión backend y documentar la preparación independiente de la aplicación. Sin embargo, la verificación parcial de frontend, la ausencia de una validación global confirmada y la falta de inspección directa del manifiesto impiden declarar cerrado el hito H0.

El conflicto D-02 representa un resultado relevante del proceso de descubrimiento: una misma evolución funcional puede enfrentar condiciones iniciales diferentes entre herramientas SDD.

Resolver esta diferencia mediante una reinterpretación implícita de saldos comprometería tanto la integridad financiera del sistema como la comparabilidad experimental.

Por esta razón, el proceso mantiene la supervisión del investigador como requisito previo a la especificación e implementación de una política de migración.

El avance operativo provisional se estima en 7 % del total de la Etapa 4, correspondiente a trabajo parcialmente acreditado de H0. Este porcentaje es un instrumento de seguimiento, no una medición oficial de las dimensiones D1–D5.

## 11. Evidencia y rutas

**Implementación heredada:** `Etapa 3/OpenSpec/`

**Implementación de trabajo:** `Etapa 4/OpenSpec/`

**Directorio experimental:** `Etapa 4/_experiment_logs/OpenSpec/`

Archivos revisados:

- `inventory.md`
- `frozen-baseline-discovery.md`
- `backend-tests-output.txt`

Archivos adicionales reportados, pendientes de verificación directa:

- `source-manifest-sha256.json`
- `frontend-tests-output.txt`
- `frontend-build-output.txt`
- `openspec-validation-output.txt`
- `CODEX-INTERACTION-REGISTER.md`
- `SEED-4_AnexoA_replicacion.md`

## 12. Próximo paso

La siguiente iteración deberá completar la verificación de las evidencias H0 pendientes y realizar un descubrimiento H1 centrado en los contratos D-01 a D-14.

Como resultado, deberá proporcionar una matriz de impacto, alternativas explícitas para D-02 y un plan de artefactos nativos OpenSpec.

El investigador revisará y aprobará las decisiones materiales antes de iniciar la generación de especificaciones.

**Estado final:** H0 parcialmente acreditado; H1 pendiente de aprobación de contratos. No se autoriza todavía implementación de Etapa 4.


# E4_OPENSPEC_REGISTRO_02_VERIFICACION_Y_DESCUBRIMIENTO.md

## 1. Identificación

**Proyecto:** Shift Bank — Estudio comparativo SDD  
**Etapa:** 4 — Evolución multimoneda, Event Sourcing y CQRS  
**Herramienta:** OpenSpec  
**Agente:** Codex CLI  
**Iteración:** 02 — Verificación de línea base y descubrimiento de contratos  
**Fecha:** 18 de noviembre de 2026  
**Estado:** Finalizada con hallazgo de seguridad pendiente.

## 2. Objetivo

Completar las verificaciones pendientes de la preparación independiente de Shift Bank E4, recuperar el entorno frontend, comprobar los hashes SHA-256 y desarrollar un análisis preliminar de los contratos D-01 a D-14 sin modificar la aplicación ni generar especificaciones funcionales nuevas.

## 3. Procedimiento ejecutado

El agente inspeccionó los registros de preparación previamente generados, los archivos de configuración del proyecto, la estructura nativa de OpenSpec y el estado del repositorio.

Posteriormente instaló las dependencias frontend mediante `npm ci`, respetando el archivo de bloqueo de versiones. Una vez preparado el entorno, ejecutó la suite frontend y el build de la aplicación.

También ejecutó `openspec validate --all --strict` y realizó una verificación independiente de los archivos del manifiesto SHA-256.

En la fase documental produjo matrices de impacto, análisis de decisiones, alternativas para el conflicto D-02 y un plan preliminar de especificaciones.

Durante la verificación del inventario detectó la inclusión de un archivo de configuración con campos sensibles poblados, por lo que detuvo el procedimiento en el punto de control humano.

## 4. Resultados

| Verificación | Resultado |
|---|---|
| Regresión backend heredada | 54/54 PASS |
| Regresión frontend | 9/9 PASS |
| Build TypeScript/Vite | PASS |
| Validación OpenSpec estricta | 6/6 PASS |
| Archivos del manifiesto | 80 |
| Bytes verificados | 441.008 |
| Diferencias de hashes | 0 |
| Reparse points detectados | 0 |

La ejecución de las pruebas backend corresponde a la evidencia original de H0 y no a una repetición durante esta iteración.

La instalación frontend permitió resolver el bloqueo inicial. El build se completó sin errores y con código de salida cero.

La validación estricta de OpenSpec verificó seis objetivos heredados, superando la limitación de la invocación anterior que no había identificado objetivos de validación.

## 5. Hallazgo de seguridad

La verificación independiente identificó que `deployment/.env.local` estaba incluido en el inventario de archivos copiados.

Este hecho contradice la declaración inicial de exclusión de archivos privados `.env`.

Una inspección estructural reportó campos de configuración poblados con valores que no correspondían a placeholders reconocidos. No se conservaron valores de credenciales en el informe recibido.

El hallazgo constituye una desviación de la política de preparación experimental. No acredita por sí solo una filtración efectiva, pero exige revisar la clasificación del archivo, su posible exposición y el tratamiento seguro de la copia E4.

El agente no eliminó ni modificó los archivos originales y detuvo la ejecución para obtener aprobación.

## 6. Descubrimiento H1

Se generaron documentos técnicos que cubren:

- Verificación de H0.
- Matriz de impacto arquitectónico.
- Evaluación de las decisiones D-01 a D-14.
- Alternativas de migración para D-02.
- Plan de especificaciones nativas OpenSpec.
- Índice de evidencias.

Para el conflicto D-02, el agente informó cuatro alternativas: conservar las cuentas heredadas junto con cuentas nuevas de referencia; mantener identificadores y valores con una política de moneda aprobada; separar los datos de referencia en un entorno nuevo; o adoptar una política explícita de conversión y conciliación.

Ninguna alternativa fue aprobada ni implementada.

Los documentos completos no fueron aportados a esta revisión, por lo que su contenido y suficiencia técnica permanecen pendientes de análisis directo.

## 7. Intervenciones humanas

Durante la ejecución se autorizaron operaciones necesarias para guardar los archivos de evidencia fuera del directorio de aplicación.

No se autorizó modificación de código, contratos financieros, especificaciones OpenSpec ni migración de saldos.

El hallazgo sobre `.env.local` originó una nueva necesidad de intervención humana relacionada con su tratamiento seguro.

## 8. Limitaciones

La guía canónica y `SEED-4.md` no fueron localizadas por Codex en su entorno de trabajo. Por tanto, las decisiones comunes requieren cotejo completo contra sus fuentes normativas.

No se verificó la equivalencia de la copia del anexo SEED-4 con el documento maestro.

El registro de interacciones aún no proporciona una medición completa de consumo y esfuerzo de Codex. No se dispone de valores confiables para tokens, tiempos exclusivos del modelo o costo.

Además, el estado global de Git mostraba modificaciones ajenas a OpenSpec E4, que no fueron atribuidas a esta iteración ni alteradas.

## 9. Interpretación académica

La iteración permitió superar los bloqueos ambientales detectados en H0, completar la regresión frontend y confirmar la integridad binaria de los archivos registrados en el manifiesto.

No obstante, la integridad de la copia debe distinguirse de su adecuación al protocolo experimental. Un conjunto de archivos puede coincidir perfectamente con su origen y, simultáneamente, contener material sensible que debía excluirse.

El hallazgo evidencia la importancia de complementar el cotejo criptográfico con verificaciones semánticas del inventario y las reglas de seguridad de la investigación.

El trabajo documental de H1 constituye una base para el análisis de impacto, pero no representa todavía la aprobación de los contratos ni el cierre de las decisiones de migración.

## 10. Próximo paso

Realizar una revisión controlada del archivo de configuración sensible, definir su tratamiento autorizado y preservar la evidencia histórica del incidente.

Posteriormente, inspeccionar los documentos completos de H1, verificar las referencias normativas y solicitar aprobación del investigador para la política de migración D-02.

No iniciar H2 ni implementación mientras permanezcan pendientes las decisiones materiales.

**Avance operativo acumulado: 9 %.**

**Estado final:** H0 técnicamente verificado en sus comprobaciones principales, pendiente de regularización de seguridad. H1 en descubrimiento, sin contratos aprobados.

# E4_OPENSPEC_REGISTRO_03_SEGURIDAD_Y_TRANSFERENCIA_H1.md

## 1. Identificación

**Proyecto:** Shift Bank — Estudio comparativo de herramientas SDD  
**Etapa:** 4 — Evolución multimoneda, Event Sourcing y CQRS  
**Herramienta:** OpenSpec  
**Agente:** Codex CLI  
**Iteración:** 03 — Revisión de seguridad y transferencia de evidencia H1  
**Fecha:** 18 de noviembre de 2026  
**Estado:** Completada; pendiente de autorización del investigador para la corrección de la copia E4.

## 2. Objetivo

Revisar la inclusión de un archivo de configuración sensible durante la preparación independiente de E4, evaluar los riesgos de exposición y preservar las evidencias originales. Adicionalmente, consolidar los resultados documentales de H1 para su posterior revisión y aprobación.

## 3. Procedimiento ejecutado

El agente inspeccionó los metadatos de los archivos `deployment/.env.local` presentes en E3 y E4, así como su estado frente al control de versiones Git.

Se revisaron las referencias de configuración utilizadas por Docker Compose y las dependencias de las pruebas existentes respecto al archivo.

Posteriormente se realizó una búsqueda limitada de asignaciones con apariencia de credenciales en el directorio de evidencia.

Finalmente, el agente revisó los documentos de descubrimiento y decisiones generados en la iteración 02 y produjo tres registros nuevos de seguridad, transferencia y aprobación.

No se ejecutaron nuevas pruebas, compilaciones ni validaciones OpenSpec.

## 4. Resultados de seguridad

Se comprobó que ambos archivos `.env.local` tienen un tamaño de 415 bytes, están ignorados por Git y no forman parte de los archivos versionados.

La copia E4 fue el único archivo con ese nombre localizado dentro de Etapa 4.

Docker Compose utiliza dicha configuración, mientras que las pruebas backend y la compilación frontend no dependen directamente de ella.

El análisis de patrones no encontró asignaciones con apariencia de credenciales en 27 archivos de evidencia. Este resultado constituye una comprobación limitada y no permite descartar todas las formas posibles de exposición.

No se mostraron valores de credenciales y los archivos sensibles permanecieron intactos.

## 5. Análisis del hallazgo

La presencia de `.env.local` contradice la declaración inicial del inventario, según la cual los archivos privados habían sido excluidos.

La coincidencia SHA-256 de la copia no elimina esta contradicción: demuestra fidelidad respecto del origen, pero no cumplimiento de las reglas de selección del material transferido.

Se propuso conservar E3 sin modificaciones, preservar el manifiesto original y tratar separadamente la copia sensible E4 mediante un procedimiento autorizado de aislamiento.

La rotación de credenciales quedó condicionada a la verificación de reutilización, exposición o acceso no autorizado.

## 6. Transferencia de H1

Se comprobó la existencia de los seis documentos de análisis producidos durante la iteración 02.

El agente resumió las decisiones D-01 a D-14, las alternativas de migración D-02 y el plan de especificaciones OpenSpec, sin regenerar ni modificar los documentos originales.

Las cuatro alternativas de migración permanecen sin aprobación.

No se creó ningún artefacto funcional nuevo de OpenSpec.

## 7. Referencias normativas

Durante la ejecución, el agente no encontró localmente las fuentes normativas completas y no pudo demostrar la equivalencia del anexo SEED-4 con una fuente canónica.

En una revisión independiente posterior se extrajo el texto literal del Anexo A de la guía de replicación disponible para el investigador.

El texto contiene 24 líneas y 4.240 bytes UTF-8, con SHA-256:

`9714ef4854501fb1000eb5790a5d3f27c0e787a00f97eff9f88d8c5d61871bf9`

El hash coincide con el registrado previamente para el anexo SEED-4 de OpenSpec. Esta correspondencia permite corroborar el contenido reportado respecto del Anexo A, aunque todavía debe cotejarse directamente el archivo local utilizado por Codex.

## 8. Evidencias

Directorio:

`Etapa 4/_experiment_logs/OpenSpec/`

Archivos generados:

- `E4_OPENSPEC_I03_SECURITY_REVIEW.md`
- `E4_OPENSPEC_I03_H1_HANDOFF.md`
- `E4_OPENSPEC_I03_RESEARCHER_CHECKPOINT.md`

Los registros anteriores se conservaron.

## 9. Intervenciones humanas y métricas

El investigador autorizó las operaciones necesarias para guardar los nuevos documentos de evidencia.

No autorizó modificaciones de credenciales, migración de cuentas ni cambios funcionales.

La salida de Codex informa cinco lotes de ejecución de herramientas y una interacción del investigador identificable. El agente reportó una duración de trabajo de 6 minutos y 34 segundos; esta cifra no debe interpretarse como tiempo exclusivo de procesamiento del modelo.

Los tokens, costos y demás métricas no disponibles permanecen clasificados como N/D.

## 10. Interpretación académica

La iteración documenta la importancia de diferenciar la integridad de una transferencia de archivos del cumplimiento de las reglas experimentales de preparación.

El incidente de configuración no implica necesariamente un fallo funcional ni una exposición efectiva de credenciales. Sin embargo, demuestra que el aislamiento debe verificarse también frente a los tipos de información admitidos.

Asimismo, la revisión permitió consolidar la fase de descubrimiento sin iniciar prematuramente la implementación, preservando la separación entre análisis automatizado y decisiones humanas.

## 11. Próximo paso

Contrastar las matrices de H1 con las referencias normativas completas y preparar una decisión documentada sobre la migración D-02.

Solicitar la aprobación del investigador para el procedimiento de contención de `.env.local`, el tratamiento de los saldos históricos y el plan de artefactos OpenSpec.

Solo después de aprobar los contratos materiales podrá iniciarse H2.

**Avance operativo acumulado: 9 %.**

# E4_OPENSPEC_REGISTRO_04_CONCILIACION_NORMATIVA.md

## 1. Identificación

**Proyecto:** Shift Bank — Estudio comparativo de herramientas SDD  
**Etapa:** 4 — Evolución multimoneda, Event Sourcing y CQRS  
**Herramienta:** OpenSpec  
**Agente:** Codex CLI  
**Iteración:** 04 — Conciliación normativa y revisión de contratos  
**Fecha:** 18 de noviembre de 2026  
**Estado:** Iteración ejecutada; punto de aprobación H1 pendiente.

## 2. Objetivo

Contrastar los análisis de impacto y las decisiones identificadas en las iteraciones anteriores con la semilla común de Etapa 4 y la guía de replicación, verificando su disponibilidad, integridad textual y correspondencia con la implementación OpenSpec heredada.

Adicionalmente, evaluar alternativas para resolver la incompatibilidad entre los saldos iniciales OpenSpec y los valores de referencia establecidos en D-02, sin ejecutar cambios financieros ni modificar especificaciones.

## 3. Procedimiento ejecutado

El agente buscó las fuentes normativas en las rutas inicialmente previstas. Al no encontrarlas, amplió la búsqueda dentro del proyecto y localizó la semilla y la guía de replicación en otros directorios de Etapa 4.

Posteriormente comparó dos copias del Anexo A mediante SHA-256, examinó la diferencia respecto de `SEED-4.md` y extrajo los contratos de la guía.

También revisó los registros de descubrimiento H1 y las especificaciones heredadas de OpenSpec, con el propósito de identificar contradicciones, decisiones previamente establecidas y asuntos que requieren autorización adicional.

Durante el procedimiento se presentaron errores relacionados con rutas, sintaxis de comandos Python y codificación de caracteres en consola. Estos errores fueron superados mediante nuevas invocaciones y no implicaron modificaciones funcionales del sistema.

Finalmente, el agente creó un documento de revisión contractual y detuvo la ejecución en el punto de aprobación humana.

## 4. Verificación normativa

Las dos copias locales del Anexo A presentaron un tamaño de 4.240 bytes y el hash SHA-256 esperado:

`9714ef4854501fb1000eb5790a5d3f27c0e787a00f97eff9f88d8c5d61871bf9`

El archivo `SEED-4.md` localizado en la raíz de Etapa 4 contiene 4.241 bytes debido a un salto de línea final adicional.

Según la comparación realizada, el contenido textual de la semilla coincide con el Anexo A de la guía después de normalizar los saltos de línea introducidos por el formato Word.

Se considera demostrada la equivalencia textual reportada, sin afirmar identidad binaria entre todas las versiones del archivo.

La guía de replicación permitió recuperar los compromisos D-01 a D-14. Las actas individuales originales de aprobación no fueron localizadas, lo que constituye una limitación de trazabilidad histórica.

## 5. Conciliación de decisiones

El análisis confirmó que los contratos D-01 a D-14 ya están definidos en la guía común y no deben reinterpretarse como preguntas abiertas por cada herramienta.

Se identificó que la implementación OpenSpec heredada requiere adaptaciones para introducir moneda explícita, FX, eventos de dominio, CQRS, versiones de cuenta e idempotencia, preservando sus funcionalidades y garantías anteriores.

La decisión D-07 establece límites por operación y diarios expresados en USD equivalente, además del umbral MFA. Estos valores no requieren una nueva definición de negocio.

Sin embargo, permanece pendiente establecer cómo los importes y las obligaciones heredadas se relacionarán con estos límites tras la migración.

## 6. Conflicto D-02

La implementación OpenSpec E3 presenta dos cuentas con identificadores `acc_checking` y `acc_savings`, cuyos importes iniciales registrados son 5.000.000,00 y 15.000.000,00, respectivamente.

El sistema contiene referencias a COP, pero no almacena explícitamente la moneda de cada cuenta.

La referencia D-02 contempla, en cambio, cuentas USD con saldos de 2.500,00 y 10.000,00, además de cuentas EUR y GBP inicialmente vacías.

La transformación de los dos saldos heredados a los importes exactos de referencia exigiría tasas implícitas distintas para cada cuenta, bajo la hipótesis de que los importes originales están denominados en COP.

Por tanto, una tasa única no permite satisfacer simultáneamente la preservación del valor inicial y la reproducción exacta de ambos saldos D-02.

El agente recomendó evaluar la alternativa D, consistente en una conversión y conciliación explícitamente aprobadas por el investigador, acompañadas de trazabilidad de los importes originales.

La recomendación no constituye una autorización ni resuelve por sí sola la incompatibilidad.

## 7. Seguridad y preservación de evidencia

El hallazgo de inclusión indebida de `deployment/.env.local` permanece abierto.

Durante esta iteración no se modificaron, eliminaron ni trasladaron archivos de configuración sensibles.

Se mantuvo la propuesta de aislar exclusivamente la copia E4, sin alterar E3 ni sobrescribir los manifiestos históricos.

La ejecución tampoco modificó código, pruebas, especificaciones, saldos, registros transaccionales ni credenciales.

## 8. Evidencia

**Directorio experimental:**

`Etapa 4/_experiment_logs/OpenSpec/`

**Documento generado:**

`E4_OPENSPEC_I04_H1_CONTRACT_REVIEW.md`

**Fuentes utilizadas:**

- `SEED-4.md`
- `SEED-4_AnexoA_replicacion.md`
- `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx`
- Registros de impacto y decisiones de las iteraciones 02 y 03.
- Implementación y especificaciones OpenSpec heredadas.

Esta revisión académica se fundamenta en la salida entregada por Codex y la consulta de la guía normativa. El contenido íntegro del registro I04 no fue adjuntado para una auditoría independiente adicional.

## 9. Intervenciones humanas y esfuerzo

El investigador proporcionó las instrucciones de la iteración y autorizó las operaciones necesarias para guardar el nuevo documento de evidencia.

No se aprobó la política de migración D-02 ni se concedió autorización para generar especificaciones o implementar funcionalidades.

La salida de Codex reportó una duración de trabajo de 10 minutos y 44 segundos. Esta duración no equivale necesariamente al tiempo exclusivo de inferencia del modelo.

No se dispone de una exportación primaria suficiente para determinar tokens, costo o tiempo exclusivo de procesamiento; estas métricas permanecen como N/D.

## 10. Interpretación académica

La iteración permitió resolver una incertidumbre documental que condicionaba el descubrimiento de Etapa 4. La localización de las fuentes normativas y la comparación de sus contenidos reducen el riesgo de generar especificaciones a partir de contratos incompletos.

El análisis también confirmó que la existencia de decisiones comunes no garantiza su compatibilidad automática con todas las aplicaciones heredadas.

En particular, la tensión entre la preservación de los importes originales y la reproducción exacta de los saldos de referencia constituye un problema material de migración, no una simple elección de estructura de datos.

Desde la perspectiva experimental, cualquier desviación respecto de D-02 debe registrarse explícitamente, ya que puede afectar la comparabilidad de la implementación y de sus pruebas de aceptación.

La participación humana continúa siendo necesaria para definir las prioridades cuando los contratos comunes y el estado heredado resultan incompatibles.

## 11. Próximo paso

Solicitar aprobación del investigador para el tratamiento seguro de la copia `.env.local` de E4 y la política de conciliación monetaria de D-02.

Una vez aprobadas las decisiones materiales, congelar los contratos de H1 y autorizar el plan de artefactos nativos OpenSpec.

La implementación de Etapa 4 permanecerá prohibida hasta que se generen, validen y aprueben las especificaciones H2.

**Avance operativo acumulado: 9 %.**

**Estado final:** revisión normativa completada, decisiones materiales pendientes y aplicación sin modificaciones funcionales.


# E4_OPENSPEC_REGISTRO_06_DECISIONES_PREVIAS.md

**Fecha:** 18 de noviembre de 2026  
**Herramienta:** OpenSpec + Codex CLI  
**Estado:** Decisiones humanas registradas; iteración 06 pendiente de ejecución.

## Objetivo

Establecer las autorizaciones necesarias para corregir la excepción de seguridad de H0 y avanzar en la formulación de una política de conciliación monetaria D-02.

## Decisiones del investigador

**Seguridad:** Se autorizó trasladar exclusivamente el archivo `deployment/.env.local` de E4 a una ubicación externa protegida bajo `C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\`. Se exige conservar E3 y la evidencia histórica, sin rotación automática de credenciales.

**Conciliación D-02:** Se estableció como prioridad preservar el valor financiero y el historial heredados. No se aprobó ninguna tasa de conversión ni correspondencia definitiva de identificadores.

**Metodología OpenSpec:** Se aprobó en principio el alcance del plan de artefactos nativos, condicionado a la resolución de D-02 y a la revisión humana de las especificaciones antes de implementar.

## Propuesta técnica pendiente de aprobación

Se planteó utilizar una tasa simulada fija de 4.000 COP por USD y conservar los identificadores internos heredados, incorporando referencias públicas alineadas con D-02.

Esta propuesta debe someterse a verificación técnica y aprobación explícita. No constituye una modificación de las decisiones comunes.

## Resultados y limitaciones

Al momento de este registro, las autorizaciones todavía no han sido ejecutadas por Codex. No existen resultados nuevos de pruebas, modificaciones de archivos, migraciones ni especificaciones atribuibles a la iteración 06.

## Próximo paso

Ejecutar el prompt de la iteración 06, verificar la contención de seguridad y revisar la propuesta de migración. Solo después de aprobar la política financiera podrá autorizarse la generación de especificaciones H2.

**Avance acumulado verificado: 9 %.**

# E4_OPENSPEC_REGISTRO_06_CONTENCION_Y_CONCILIACION.md

**Proyecto:** Shift Bank — Comparación de herramientas SDD  
**Etapa:** 4 — Evolución multimoneda, Event Sourcing y CQRS  
**Herramienta:** OpenSpec  
**Agente:** Codex CLI  
**Iteración:** 06 — Contención de configuración y propuesta de migración D-02  
**Fecha:** 18 de noviembre de 2026  
**Estado:** Ejecutada; resolución parcial de seguridad y decisiones financieras pendientes.

## 1. Objetivo

Ejecutar la contención previamente autorizada del archivo de configuración sensible incluido en la copia E4, producir un inventario saneado y evaluar una política de migración de las cuentas heredadas sin modificar el sistema bancario ni sus especificaciones.

## 2. Procedimiento

El agente inspeccionó las rutas de origen y destino, verificó la ausencia de enlaces inesperados y preparó un directorio externo con permisos restringidos mediante ACL de Windows.

Posteriormente trasladó exclusivamente el archivo `.env.local` de E4 y verificó los permisos y la presencia de los archivos después de la operación.

Durante la elaboración del inventario saneado se identificaron errores de comparación de rutas y un nuevo hallazgo: el manifiesto original incluía dos archivos TLS de desarrollo.

El agente corrigió el procedimiento de filtrado y generó un manifiesto complementario que excluye los tres archivos sensibles o potencialmente sensibles.

Finalmente evaluó una tasa simulada de conversión COP/USD y una correspondencia de cuentas para la futura migración D-02, sin ejecutar cambios financieros.

## 3. Resultados de seguridad

El traslado autorizado de `deployment/.env.local` finalizó satisfactoriamente.

El archivo quedó almacenado fuera del repositorio, con permisos protegidos para el usuario actual, SYSTEM y Administrators.

La ubicación original en E4 quedó sin el archivo. La copia de E3 conservó sus metadatos y permisos originales.

Adicionalmente se identificaron:

- `deployment/certs/dev-cert.pem`
- `deployment/certs/dev-key.pem`

Ambos fueron excluidos del manifiesto saneado, pero permanecen físicamente en E4 porque su traslado no había sido autorizado.

No se ejecutó despliegue ni se alteró la configuración Docker Compose.

## 4. Inventario saneado

| Indicador | Resultado |
|---|---:|
| Archivos originales | 80 |
| Archivos saneados verificados | 77 |
| Bytes saneados | 437.819 |
| Coincidencias SHA-256 | 77/77 |
| Archivos excluidos del manifiesto nuevo | 3 |

Se conservaron íntegros el manifiesto y el inventario originales.

El manifiesto saneado documenta el subconjunto verificado de archivos no sensibles, sin pretender representar la totalidad de los archivos físicamente presentes en la implementación.

## 5. Análisis financiero D-02

Se evaluó una tasa simulada fija de 4.000 COP por USD, propuesta para la migración inicial.

Los importes observados en la inicialización heredada producirían:

| Cuenta | COP inicial | USD propuesto |
|---|---:|---:|
| `acc_checking` | 5.000.000,00 | 1.250,00 |
| `acc_savings` | 15.000.000,00 | 3.750,00 |

El valor agregado bajo dicha equivalencia sería USD 5.000,00, inferior en USD 7.500,00 a los saldos agregados de referencia D-02.

No se propusieron operaciones de compensación artificial para alcanzar los importes de referencia.

El análisis también identificó dos transferencias iniciales, una de ahorros a corriente por 500.000,00 COP y otra en dirección inversa por 100.000,00 COP.

La documentación disponible no demuestra que sea correcto reaplicar dichos movimientos sobre los saldos iniciales observados. Por ello se propuso preservar el historial como evidencia y definir una frontera de migración que evite contabilizaciones duplicadas.

## 6. Correspondencia de cuentas propuesta

Se evaluó mantener las identidades internas heredadas e introducir referencias públicas `CHK-1001` y `SAV-2001`, además de las nuevas cuentas EUR y GBP requeridas por D-02.

La propuesta permitiría preservar relaciones internas, pero requiere confirmar su compatibilidad con los contratos HTTP y las pruebas existentes.

Una referencia pública adicional no demuestra por sí sola el cumplimiento literal de la identidad exigida en D-02.

## 7. Intervenciones humanas

El investigador autorizó previamente el traslado exclusivo de `.env.local` de E4, la preservación de E3 y la no rotación automática de credenciales.

También estableció como prioridad preservar el valor y el historial bancario heredados.

No aprobó la tasa COP/USD, los nuevos saldos, la correspondencia definitiva de cuentas ni las desviaciones respecto de los importes de referencia.

El agente respetó estas restricciones y detuvo la ejecución antes de crear especificaciones.

## 8. Problemas y limitaciones

La contención de seguridad permanece parcialmente abierta debido a los archivos TLS que continúan en E4.

La política financiera propuesta utiliza una equivalencia simulada que requiere aprobación expresa.

Todavía deben definirse los tratamientos de operaciones ACH pendientes, autenticaciones MFA en curso, recurrencias y límites diarios heredados.

La implementación no dispone de una migración Event Sourcing/CQRS ejecutada; el mecanismo de snapshot constituye únicamente una propuesta arquitectónica.

No se repitieron pruebas, compilaciones ni validaciones anteriores. La salida del agente reportó una duración de trabajo de 14 minutos y 50 segundos, sin evidencia suficiente para interpretarla como tiempo exclusivo del modelo.

Las métricas de tokens, costo y procesamiento exclusivo permanecen como N/D.

## 9. Evidencia

Directorio: `Etapa 4/_experiment_logs/OpenSpec/`

Se generaron los siguientes documentos:

- `E4_OPENSPEC_I06_SECURITY_CONTAINMENT.md`
- `E4_OPENSPEC_I06_SANITIZED_INVENTORY.md`
- `E4_OPENSPEC_I06_SANITIZED_MANIFEST.json`
- `E4_OPENSPEC_I06_D02_RATE_AND_MAPPING_PROPOSAL.md`
- `E4_OPENSPEC_I06_RESEARCHER_DECISION_CHECKPOINT.md`

No se modificaron archivos de código, pruebas, especificaciones, datos financieros ni registros históricos.

## 10. Interpretación académica

La iteración permitió separar la fidelidad de la copia original de la conformidad de su contenido con las reglas experimentales.

La generación de un manifiesto saneado constituye una medida complementaria de trazabilidad, sin alterar la evidencia de las condiciones iniciales.

El análisis monetario evidenció que una migración determinista puede preservar una equivalencia de valor definida y, simultáneamente, producir saldos diferentes de los establecidos por un contrato común.

Esta diferencia requiere documentación explícita, ya que afecta la comparabilidad entre herramientas. Asimismo, la preservación del historial exige separar los registros anteriores a la migración de los nuevos eventos que generan efectos financieros.

## 11. Próximo paso

Obtener autorización para tratar los archivos TLS restantes y aprobar una política concreta de migración D-02, incluyendo tratamiento de operaciones pendientes y preservación histórica.

Después de congelar las decisiones H1, podrá autorizarse la generación de especificaciones nativas OpenSpec.

**Avance acumulado acreditado: 9 %.**

# E4_OPENSPEC_REGISTRO_07_CONTROL_APROBACIONES.md

**Fecha:** 18 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Detenida sin modificaciones.

## Objetivo

Iniciar el cierre de H0 y la transición hacia H2, respetando las aprobaciones humanas requeridas para los cambios de seguridad, migración financiera y generación de especificaciones.

## Procedimiento y resultados

Codex examinó las condiciones de autorización del prompt y detectó que las propuestas técnicas todavía no habían sido aprobadas explícitamente por el investigador.

Por esta razón, detuvo la ejecución antes de realizar operaciones sobre archivos, credenciales, especificaciones o datos financieros.

No se ejecutaron nuevas pruebas ni validaciones. Los resultados anteriormente verificados permanecen vigentes.

## Intervención humana

Continúan pendientes las autorizaciones para:

1. Trasladar los archivos TLS de E4.
2. Aprobar la tasa de migración, correspondencia de cuentas y desviaciones D-02.
3. Establecer el tratamiento de operaciones heredadas pendientes.
4. Autorizar la generación de especificaciones nativas OpenSpec.

## Interpretación académica

La detención evidencia el funcionamiento del control de aprobación humana establecido para el experimento. No representa un defecto funcional del sistema.

Sin embargo, también muestra que el procedimiento requiere consolidar las decisiones pendientes para evitar iteraciones sin producción de nuevos resultados técnicos.

## Próximo paso

Preparar un contrato final de decisiones H1, sustentado en el código heredado, que permita al investigador autorizar conjuntamente las políticas materiales antes de iniciar H2.

**Avance acumulado: 9 %.**

# E4_OPENSPEC_REGISTRO_08_DECISIONES_FINALES_H1.md

**Fecha:** 18 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Completada; aprobación H1 pendiente.

## Objetivo

Analizar los estados bancarios heredados que condicionan la migración D-02 y preparar las decisiones necesarias para autorizar las especificaciones de Etapa 4.

## Procedimiento

Codex examinó el código y las especificaciones heredadas correspondientes a transferencias ACH, autorizaciones MFA, pagos recurrentes y límites diarios.

Posteriormente consolidó las propuestas de migración, seguridad TLS y planificación OpenSpec en un nuevo documento de decisiones.

## Resultados

El análisis confirmó que las transferencias ACH pendientes ya han debitado fondos, mientras que su liquidación no realiza un segundo débito y el fallo contempla un reintegro único.

Las autorizaciones MFA pendientes todavía no han generado el movimiento financiero correspondiente.

Las programaciones activas se ejecutan automáticamente al vencer; las pausadas permanecen inactivas.

Se propuso aplicar condiciones de rechazo seguro a la migración cuando existan operaciones u obligaciones heredadas cuyo tratamiento no esté aprobado.

Se mantuvieron como propuestas la tasa simulada de 4.000 COP/USD, la correspondencia de identificadores y la desviación respecto de los saldos D-02.

## Evidencia

Se generó:

`Etapa 4/_experiment_logs/OpenSpec/E4_OPENSPEC_I08_FINAL_H1_DECISIONS.md`

No se modificaron archivos de aplicación, pruebas, especificaciones, datos financieros ni material criptográfico. Tampoco se repitieron las verificaciones anteriores.

## Intervención humana

Permanecen pendientes cuatro autorizaciones: contención TLS, política de migración D-02, tratamiento de estados pendientes y generación de especificaciones H2.

## Interpretación académica

El descubrimiento permitió identificar condiciones financieras que podrían ocasionar doble contabilización o ejecución indebida durante una migración. La propuesta de rechazo seguro prioriza la conservación de invariantes, aunque limita los estados heredados que podrían migrarse automáticamente.

Esta limitación deberá documentarse en la evaluación comparativa.

## Próximo paso

Obtener las cuatro aprobaciones explícitas y, según las decisiones adoptadas, generar y validar las especificaciones nativas de OpenSpec antes de implementar.

**Avance acumulado: 9 %.**

# E4_OPENSPEC_REGISTRO_09_APROBACIONES_H1.md

**Fecha:** 18 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Detenida por aprobación pendiente.  
**Avance acumulado:** 9 %.

## Objetivo

Obtener las autorizaciones del investigador para cerrar la preparación de seguridad, aprobar la política de migración D-02 y comenzar las especificaciones nativas OpenSpec.

## Procedimiento y resultados

Codex presentó cuatro decisiones para aprobación explícita:

1. Traslado seguro de los certificados TLS de E4.
2. Política de migración COP/USD, correspondencia de cuentas y desviaciones D-02.
3. Condiciones de rechazo seguro para estados bancarios heredados.
4. Autorización para generar y validar los artefactos H2.

La ejecución se detuvo antes de recibir las respuestas.

No se modificaron archivos, credenciales, manifiestos, especificaciones ni datos financieros. Tampoco se ejecutaron pruebas o validaciones.

## Interpretación académica

La detención corresponde al mecanismo de control humano previo a cambios materiales. Las políticas propuestas todavía no constituyen decisiones aprobadas hasta recibir la autorización expresa del investigador.

## Próximo paso

Registrar las cuatro respuestas del investigador y ejecutar únicamente las operaciones autorizadas.

Una vez generadas las especificaciones H2, deberán revisarse y aprobarse antes de iniciar implementación.

**Resultado:** Sin modificaciones técnicas y sin incremento del avance.

# E4_OPENSPEC_REGISTRO_09_ESPECIFICACIONES_H2.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** H2 generado y validado; aprobación final pendiente.  
**Avance acumulado:** 40 %.

## Objetivo

Ejecutar las decisiones aprobadas de H1, completar la contención de los archivos TLS y generar las especificaciones nativas OpenSpec para la evolución multimoneda, Event Sourcing y CQRS.

## Procedimiento y resultados

Codex trasladó los certificados TLS de E4 a la ubicación externa autorizada y verificó permisos ACL restringidos. Las copias de E3 permanecieron intactas.

Posteriormente creó el cambio nativo `stage4-multicurrency-event-sourcing-cqrs`, compuesto por propuesta, diseño, 15 especificaciones delta y tareas de implementación.

Se registraron 27 requisitos y 76 escenarios de aceptación.

La validación inicial identificó incompatibilidades relacionadas con nombres de escenarios heredados. Estas fueron corregidas y se ejecutó nuevamente la validación estricta, obteniendo 7/7 verificaciones satisfactorias.

## Decisiones y limitaciones

Las especificaciones incorporaron la política D-02 aprobada, incluyendo la conversión simulada de 4.000 COP/USD, la preservación histórica y la desviación explícita respecto de los saldos de referencia.

Se identificó una decisión todavía pendiente sobre la migración de límites configurables almacenados bajo el modelo monetario heredado.

La capacidad de despliegue con la nueva ubicación de los archivos TLS no fue verificada.

## Evidencias

Los registros generados incluyen:

- `E4_OPENSPEC_I09_RESEARCHER_APPROVAL.md`
- `E4_OPENSPEC_I09_APPROVAL_AND_H2_EVIDENCE.md`
- `E4_OPENSPEC_I09_H2_TRACEABILITY.md`
- `E4_OPENSPEC_I09_H2_FINALIZATION_ADDENDUM.md`

No se modificaron archivos de aplicación, pruebas ni datos financieros. Tampoco se ejecutaron migraciones, despliegues o commits.

## Interpretación académica

La iteración evidencia la utilización del flujo nativo OpenSpec para transformar decisiones funcionales aprobadas en contratos estructurados y verificables.

La validación estricta permitió identificar y corregir incompatibilidades de especificación antes de la implementación. Sin embargo, superar la validación sintáctica y estructural no demuestra todavía cumplimiento funcional.

La decisión pendiente sobre límites heredados confirma la necesidad de mantener controles humanos sobre las políticas financieras durante una evolución arquitectónica.

## Próximo paso

Resolver el tratamiento de los límites configurables, completar la revisión de H2 y solicitar aprobación explícita para iniciar H3.

**Avance E4 OpenSpec: 40 %.**

# E4_OPENSPEC_REGISTRO_10_REVISION_H2.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Revisión completada, aprobación pendiente.  
**Avance acumulado:** 40 %.

## Objetivo

Revisar las especificaciones H2 e identificar la política necesaria para migrar los límites configurables de la implementación heredada.

## Procedimiento y resultados

Codex inspeccionó el código, las pruebas y las especificaciones relacionadas con los límites de transferencias.

Se identificó que los límites son configurables por usuario y tienen valores predeterminados de 5.000.000 COP por operación y 10.000.000 COP diarios.

Con la tasa de migración aprobada de 4.000 COP/USD, estos valores equivalen a USD 1.250 y USD 2.500, respectivamente.

Se recomendó la alternativa A, consistente en convertir los límites almacenados mediante aritmética exacta, aplicar redondeo `ROUND_HALF_UP`, respetar los máximos D-07 y rechazar de forma segura los valores inválidos.

La revisión del agente no identificó otros vacíos materiales de especificación.

## Evidencia

Se generaron:

- `E4_OPENSPEC_I10_LIMITS_DECISION.md`
- `E4_OPENSPEC_I10_H2_FINAL_REVIEW.md`

No se modificaron especificaciones, código ni datos financieros. Tampoco se ejecutaron nuevas pruebas o validaciones.

## Intervención humana

La política de migración de límites permanece pendiente de aprobación explícita del investigador.

## Interpretación académica

La iteración evidencia que la evolución multimoneda requiere preservar no solamente los saldos y movimientos, sino también las configuraciones financieras heredadas.

La conversión propuesta busca mantener las restricciones personalizadas sin superar los límites establecidos para E4. Su aprobación permitirá completar las especificaciones antes de iniciar la implementación.

## Próximo paso

Obtener aprobación de la alternativa A, actualizar las especificaciones afectadas, ejecutar la validación estricta y solicitar aprobación final de H2.

**Avance acumulado: 40 %.**

# E4_OPENSPEC_REGISTRO_10_REVISION_H2.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Especificaciones finalizadas y validadas; aprobación final pendiente.  
**Avance acumulado:** 44 %.

## Objetivo

Incorporar la política aprobada de migración de límites configurables y finalizar las especificaciones H2 de Shift Bank.

## Procedimiento y resultados

Codex actualizó las especificaciones de límites y migración, el diseño arquitectónico y la lista de tareas.

Se incorporaron la conversión COP/USD mediante la tasa aprobada de 4.000, el redondeo `ROUND_HALF_UP`, los topes D-07, el mínimo de USD 0,01, la trazabilidad de ajustes y las garantías de migración idempotente y reversión segura.

La validación estricta de OpenSpec finalizó satisfactoriamente: **7 verificaciones aprobadas y 0 fallidas**.

El cambio contiene **28 requisitos y 83 escenarios**. Se generó y verificó un manifiesto SHA-256 de 20 archivos.

## Evidencias

- `E4_OPENSPEC_I10_H2_APPROVAL_EVIDENCE.md`
- `E4_OPENSPEC_I10_FINAL_ARTIFACT_HASHES.json`

No se modificaron archivos de aplicación, pruebas, datos financieros ni contenido de E3. No se ejecutaron migraciones ni despliegues.

## Interpretación académica

La iteración completó la formalización de los contratos técnicos antes de la implementación. La validación estructural exitosa proporciona evidencia de consistencia formal, pero todavía no demuestra cumplimiento funcional.

La revisión final y la autorización de implementación permanecen bajo responsabilidad del investigador.

## Próximo paso

Revisar y aprobar las especificaciones H2. Posteriormente, autorizar H3 e implementar progresivamente las tareas documentadas, verificando su cumplimiento mediante pruebas automatizadas.

**Avance acumulado: 44 %.**

# E4_OPENSPEC_REGISTRO_11_APROBACION_H2.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Revisión H2 completada; autorización H3 pendiente.  
**Avance acumulado:** 44 %.

## Objetivo

Revisar la consistencia final de las especificaciones OpenSpec antes de iniciar la implementación de Etapa 4.

## Procedimiento y resultados

Codex examinó la propuesta, el diseño, las 15 especificaciones delta, la lista de tareas y las evidencias de validación de la iteración 10.

La revisión incluyó migración COP/USD, Event Sourcing, CQRS, conversiones monetarias, concurrencia, idempotencia, ACH, MFA, operaciones recurrentes, auditoría y compatibilidad con el sistema heredado.

El agente no identificó contradicciones materiales que impidieran aprobar H2.

Se conservaron los resultados anteriores de validación estricta (7/7 PASS), sin repetir pruebas innecesarias.

## Limitaciones

La revisión corresponde a las especificaciones. La implementación, el comportamiento en ejecución y la capacidad de despliegue todavía no han sido verificados.

No se modificaron archivos ni se inició H3.

## Interpretación académica

La iteración constituye un punto de control entre la formalización de requisitos y la implementación. La revisión permite reducir el riesgo de desarrollar funcionalidades sobre contratos incompletos, sin confundir la validación de especificaciones con la verificación del sistema implementado.

## Próximo paso

Obtener autorización explícita del investigador e iniciar el primer bloque de implementación H3, verificando los cambios mediante pruebas automatizadas.

**Avance acumulado: 44 %.**

# E4_OPENSPEC_REGISTRO_12_EVENT_STORE.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Implementación parcial H3 completada.  
**Avance acumulado:** 45 %.

## Objetivo

Iniciar la implementación de Etapa 4 mediante un componente fundamental para Event Sourcing, preservando el comportamiento del sistema bancario heredado.

## Procedimiento

Codex examinó las especificaciones aprobadas, las dependencias de las tareas y el esquema SQLite existente.

Se implementó un módulo independiente de almacenamiento de eventos de dominio y se integró su inicialización con la base de datos.

El nuevo componente permite registrar eventos persistentes con ordenamiento global y secuencias por cuenta, importes expresados en unidades monetarias menores enteras y moneda explícita.

Se incorporaron restricciones para impedir modificaciones o eliminaciones ordinarias de eventos registrados.

Las inserciones utilizan transacciones controladas por el llamador, preparando la futura integración atómica con comandos financieros, proyecciones y auditoría.

## Resultados

- **Tarea completada:** 4.1.
- **Pruebas nuevas:** 4/4 aprobadas.
- **Regresión backend:** 58/58 aprobadas.
- **Duración de las pruebas backend:** 9,237 segundos.
- **Validación OpenSpec:** PASS.

Se modificaron o crearon `backend/event_store.py`, `backend/database.py`, `backend/tests/test_event_store.py` y `tasks.md`.

## Evidencia

`Etapa 4/_experiment_logs/OpenSpec/E4_OPENSPEC_I12_H3_IMPLEMENTATION_REPORT.md`

No se accedió a bases de datos reales. Las pruebas utilizaron bases temporales.

## Limitaciones

El Event Store todavía no está integrado con los comandos financieros, las proyecciones CQRS, la idempotencia ni la auditoría transaccional.

Las garantías de atomicidad de una operación financiera completa no han sido verificadas.

No se realizaron cambios de frontend, despliegues, migraciones reales ni commits.

## Interpretación académica

La implementación constituye el primer incremento funcional de H3 y establece la infraestructura para registrar eventos de dominio de manera persistente.

Las pruebas permiten comprobar las propiedades básicas del almacenamiento, pero no demuestran todavía las garantías de consistencia del sistema completo.

El desarrollo incremental facilita detectar regresiones antes de integrar los componentes financieros más complejos.

## Próximo paso

Implementar la estructura de cuentas con moneda explícita y compatibilidad de identificadores, conforme a la tarea 2.1.

**Avance acumulado: 45 %.**

# E4_OPENSPEC_REGISTRO_13_CUENTAS_MULTIMONEDA.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Implementación parcial verificada.  
**Avance acumulado:** 46 %.

## Objetivo

Preparar las cuentas bancarias heredadas para incorporar monedas explícitas y referencias públicas sin modificar sus saldos ni transacciones históricas.

## Procedimiento y resultados

Codex implementó `backend/account_model.py` y modificó la inicialización de SQLite, las consultas bancarias y los endpoints relacionados con cuentas.

Se incorporaron metadatos de moneda, referencias públicas y el estado `legacy_unmigrated`, que identifica las cuentas pendientes de conversión.

Se conservaron los identificadores internos `acc_checking` y `acc_savings` y se añadieron mecanismos para resolver sus referencias públicas.

También se verificó que utilizar dos referencias diferentes de una misma cuenta no permita evadir la validación de transferencias a sí mismo.

**Resultados:**

- Pruebas específicas: **8/8 PASS**.
- Regresión backend: **66/66 PASS**.
- Validación OpenSpec: **PASS**.
- Tarea 4.1: completada.
- Tarea 2.1: parcialmente implementada, sin marcar como completada.

## Evidencia

`E4_OPENSPEC_I13_H3_ACCOUNT_FOUNDATION.md`

Las pruebas utilizaron bases SQLite temporales. No se ejecutó la migración financiera ni se modificaron bases de datos reales.

## Limitaciones e interpretación

La estructura permite representar y resolver identidades de cuentas, pero las cuentas heredadas todavía no tienen una moneda activa asignada. Tampoco se han creado las cuentas EUR/GBP ni ejecutado la conversión COP/USD.

Por tanto, los resultados acreditan la compatibilidad estructural inicial, no el funcionamiento completo del sistema multimoneda.

## Próximo paso

Implementar las verificaciones previas a la migración y sus pruebas aisladas. Posteriormente desarrollar el snapshot de conversión y conciliación financiera, evitando duplicar movimientos históricos.

**Avance acumulado: 46 %.**

# E4_OPENSPEC_REGISTRO_14_PREFLIGHT_MIGRACION.md

**Fecha:** 19 de noviembre de 2026  
**Herramientas:** OpenSpec y Codex CLI  
**Estado:** Implementación parcial verificada.  
**Avance acumulado:** 47 %.

## Objetivo

Implementar las verificaciones previas a la migración financiera, garantizando que los estados heredados incompatibles sean detectados antes de modificar los datos.

## Procedimiento y resultados

Codex implementó `backend/migration_preflight.py` y creó fixtures y pruebas automatizadas utilizando bases de datos SQLite temporales.

El componente verifica transacciones ACH pendientes, autorizaciones MFA, programaciones recurrentes, consumo diario de límites, conflictos de identidad y consistencia de auditoría.

La verificación exige una transacción SQLite activa y reutiliza funciones existentes del sistema heredado.

**Resultados:**

- Pruebas específicas: **14/14 PASS**.
- Regresión backend: **80/80 PASS**.
- Validación estricta OpenSpec: **PASS**.
- Tarea 1.3: completada.
- Tareas 2.1 y 2.4: pendientes.

## Evidencia

`Etapa 4/_experiment_logs/OpenSpec/E4_OPENSPEC_I14_H3_MIGRATION_PREFLIGHT.md`

No se accedió a bases de datos reales ni se modificaron saldos o transacciones financieras.

## Interpretación académica

Las pruebas demuestran que el preflight puede detectar condiciones incompatibles y rechazar la migración sin alterar el estado bancario.

Sin embargo, todavía no se ha implementado el procedimiento de conversión COP/USD ni se ha verificado la atomicidad de una migración completa.

## Próximo paso

Implementar una migración sintética con conversión y conciliación de saldos, integrando el preflight dentro de la misma transacción y verificando la reversión ante fallos.

**Avance acumulado: 47 %.**

