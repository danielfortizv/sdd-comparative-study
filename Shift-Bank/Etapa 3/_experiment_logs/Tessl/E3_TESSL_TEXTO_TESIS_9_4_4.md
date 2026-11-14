# 9.4.4. Shift Bank — Etapa 3: Evaluación Experimental de Tessl (Spec-Driven Development)

## 1. Introducción y Contexto Metodológico

La Etapa 3 del estudio comparativo sobre la aplicación bancaria **Shift Bank** evaluó la capacidad de la metodología **Spec-Driven Development (SDD)**, implementada a través de la herramienta **Tessl** y operada mediante el agente de desarrollo **Gemini CLI**, para abordar la evolución arquitectónica de un sistema *brownfield*. Partiendo de la base funcional consolidada en la Etapa 2 (cuentas, transferencias internas, historial de movimientos, autenticación multifactor simulada, transferencias interbancarias ACH, pagos recurrentes programados y límites dinámicos), la Etapa 3 (Opción A) exigió la integración de cuatro capacidades avanzadas de nivel empresarial:

1. **Cifrado extremo a extremo de datos bancarios sensibles:** Implementación de un esquema híbrido cliente-servidor (RSA-OAEP de 2048 bits con SHA-256 para el intercambio de claves de sesión efímeras y AES-256-GCM para el cifrado de campos sensibles a nivel de atributo), complementado con cifrado en reposo en la base de datos y una rutina de migración atómica e idempotente.
2. **Libro mayor de auditoría criptográfica inmutable:** Construcción de un registro de eventos transaccionales encadenado criptográficamente mediante HMAC-SHA256 desde un bloque Génesis determinístico, con garantías transaccionales de fallo cerrado (*fail-closed*), disparadores (*triggers*) a nivel de base de datos para impedir mutaciones, y un punto de acceso administrativo de verificación.
3. **Pruebas de carga y verificación de acuerdos de nivel de servicio (SLA):** Diseño y ejecución automatizada de una carga distribuida representativa mediante Locust sobre una base de datos aislada, verificando latencias de percentil 95 inferiores a 200 ms y tasas de fallo inferiores al 1,0 %.
4. **Despliegue contenerizado y endurecimiento de seguridad:** Orquestación multicontenedor mediante Docker Compose con proxy inverso Nginx TLS (TLSv1.2 y TLSv1.3), ejecución con usuarios no privilegiados (*non-root*), mapeo de puertos no privilegiados y gestión estricta de secretos sin valores predeterminados.

El marco metodológico de Tessl rigió todo el proceso mediante sus reglas fundamentales de gobernanza: la prohibición de escribir código sin especificaciones aprobadas (*spec-before-code*), el formato estandarizado con metadatos YAML y enlaces de prueba bidireccionales (*spec-format-compliance*), y la formulación interactiva estructurada (*one-question-at-a-time*).

---

## 2. Resultados de Implementación y Gobernanza de Especificaciones (Dimensión 3)

La fase de especificación consolidó un total de **11 archivos contractuales .spec.md**, de los cuales 7 correspondieron a módulos funcionales heredados y evolucionados de las etapas previas y 4 a nuevas especificaciones de arquitectura y seguridad:

| Especificación | Módulo Funcional / Arquitectónico | Líneas Físicas | Tamaño (Bytes) | Requerimientos Formales | Enlaces [@test] |
|---|---|---:|---:|---:|---:|
| ccounts.spec.md | Cuentas y Saldos | 53 | 2.285 | 13 | 9 |
| 	ransfers.spec.md | Transferencias Propias | 92 | 4.714 | 24 | 23 |
| 	ransactions.spec.md | Historial de Movimientos | 53 | 2.414 | 13 | 9 |
| mfa.spec.md | Desafío MFA y Bloqueo | 78 | 3.972 | 23 | 25 |
| ch_transfers.spec.md | Transferencias ACH y Beneficiarios | 157 | 8.463 | 44 | 41 |
| 
ecurring_payments.spec.md | Pagos Recurrentes y Scheduler | 140 | 8.298 | 40 | 35 |
| 	ransfer_limits.spec.md | Límites Dinámicos | 71 | 3.791 | 20 | 16 |
| encryption.spec.md | Cifrado Híbrido E2E y en Reposo | 137 | 10.269 | 44 | 27 |
| udit_log.spec.md | Auditoría Criptográfica Inmutable | 117 | 9.049 | 38 | 29 |
| load_testing.spec.md | Pruebas de Carga y SLAs | 83 | 6.260 | 26 | 17 |
| deployment.spec.md | Despliegue Docker y Nginx HTTPS | 112 | 5.865 | 38 | 17 |
| **Total General** | | **1.093** | **65.380** | **323** | **248** |

### Análisis Métrico de las Especificaciones:
- **Crecimiento volumétrico:** Las especificaciones aumentaron de 575 líneas en la Etapa 2 a 1.093 líneas en la Etapa 3 (+90,1 % de incremento), reflejando la complejidad de modelar formalmente primitivas criptográficas, topologías de red y protocolos de fallo.
- **Densidad contractual:** El promedio de líneas por archivo alcanzó **99,36 líneas/spec** (frente a 82,14 en E2 y 60,25 en E1), con una densidad de **29,36 requerimientos por especificación**.
- **Ratio Código / Especificación (/E$):** La relación entre líneas de código de producción no comentadas y líneas de especificación se situó en **5,06** (.536 / 1.093$), mostrando una marcada reducción frente a 7,42 en la Etapa 2 y 9,05 en la Etapa 1. Este descenso continuo corrobora una hipótesis central del paradigma SDD: a medida que el sistema incorpora restricciones de seguridad no funcionales y de infraestructura, la proporción de esfuerzo formal dedicado a la especificación crece más rápido que el volumen neto de código generado.
- **Trazabilidad bidireccional:** Se establecieron **248 etiquetas [@test]** verificadas en la suite de pruebas, garantizando que ninguna cláusula crítica careciera de una contraparte automatizada de validación.

---

## 3. Calidad del Código, Evolución Estática y Pruebas Automatizadas (Dimensión 2)

### 3.1. Evaluación Longitudinal en SonarQube
La calidad estática del código se evaluó de forma rigurosa y reproducible utilizando SonarQube Community Build v26.9.0. Para garantizar la pureza metodológica y desacoplar analíticamente el impacto de la ingesta de reportes de cobertura respecto a las correcciones reales de código, se registraron cuatro estados estáticos independientes:

1. **Línea Base Original (Pre-remediación, sin cobertura importada):** Identificó 85 defectos (12 bugs críticos en el servicio de migración bajo la regla python:S5779, 2 vulnerabilidades en los Dockerfiles bajo la regla docker:S6471 por ejecución como root, y 71 code smells). La deuda técnica fue de 450 minutos y la complejidad cognitiva de 585 sobre 5.507 ncloc. El Quality Gate reportó OK de manera incondicionada debido a la **ausencia total de condiciones configuradas sobre el código general** (conditions: []).
2. **Línea Base Intermedia (Pre-remediación, con cobertura importada):** Se configuraron los reportes de pytest-cov y itest sin modificar una sola línea de código de producción. La cobertura calculada por SonarQube ascendió de 0,0 % a **78,0 %**, mientras que todos los defectos (85), la deuda técnica (450 min) y la complejidad cognitiva (585) se mantuvieron estrictamente idénticos, demostrando que la cifra inicial de 0,0 % obedecía a un problema de importación documental y no a ausencia de validación automatizada.
3. **Medición Post-Remediación:** Tras corregir los 12 bugs críticos mediante la sustitución de aserciones por validaciones explícitas con excepciones, eliminar secretos predeterminados (hallazgo H12) y adoptar usuarios no-root (ppuser y 
ginx), los bugs y vulnerabilidades descendieron a **0**, alcanzando calificaciones máximas **A** en fiabilidad y seguridad. Se detectaron 2 nuevos code smells derivados del endurecimiento (docker:S7031 por directivas RUN consecutivas y python:S8997 por modificación de sys.path).
4. **Cierre de Calidad Focalizado (Estado Final):** Se resolvieron las 2 incidencias nuevas, cerrándose un total acumulado de 16 defectos (CLOSED / FIXED). El código final cerró con:
   - **0 Bugs** (calificación tradicional **A** / MQR **C** por reducción de 40 a 28 incidencias de fiabilidad).
   - **0 Vulnerabilidades** (calificación tradicional **A** / MQR **A**, con 0 incidencias de seguridad).
   - **72 Code Smells** (71 preexistentes no remediados intencionalmente + 1 violación menor en pruebas).
   - **491 minutos de deuda técnica** (8,27 horas, ratio de deuda del 0,3 %).
   - **Complejidad cognitiva de 624** y **ciclomática de 712**.
   - **Cobertura global de 77,9 %** (78,4 % en líneas y 69,3 % en ramas).

### 3.2. Causalidad del Incremento de Complejidad Cognitiva
Uno de los hallazgos más notables del experimento radica en la variación de la complejidad cognitiva, que se incrementó en +39 puntos (de 585 a 624, +6,7 %) y la deuda técnica en +41 minutos (+9,1 %) respecto a la línea base con cobertura. El análisis de causa raíz demostró que este incremento fue el resultado directo de la corrección de los 12 bugs de aserción: al reemplazar sentencias lineales ssert cond por estructuras condicionales formales if not cond: raise MigrationVerificationError(...) dentro de tres bucles de verificación, el analizador de SonarSource detectó nuevas ramas lógicas anidadas en el AST. Este fenómeno ilustra empíricamente el **trade-off entre robustez en tiempo de ejecución y métricas de complejidad estática**: la erradicación del riesgo de omisión de aserciones en entornos optimizados de producción (python -O) se pagó con un aumento medible en la complejidad estática y el esfuerzo nominal de mantenimiento.

### 3.3. Transparencia del Quality Gate (Estado ERROR)
El Quality Gate final del proyecto reportó **ERROR**. Lejos de constituir un defecto no controlado, este resultado evidencia la aplicación rigurosa de las reglas *Clean as You Code* (CAYC) sobre el código modificado en el período diferencial:
- **Cobertura en código nuevo (
ew_coverage):** Se midió en **70,6 %** frente al umbral exigido del **80,0 %** (déficit de 9,4 pp). A pesar de que la incorporación de 7 nuevas pruebas de inicio y migración elevó la cobertura sobre código nuevo desde un 52,9 % inicial, las ramas extremas de fallo defensivo (por ejemplo, validación de corrupción en cronogramas recurrentes o fallo de variables criptográficas en cascada) no se transitan en escenarios nominales.
- **Nuevas violaciones (
ew_violations):** Se registró **1 violación** (python:S9073 por tipado en una función auxiliar de prueba) frente al umbral de 0.
- **Integridad ética:** En estricta observancia del protocolo de investigación, **no se debilitaron las reglas bancarias, no se excluyeron archivos artificialmente del reporte de cobertura ni se relajaron los umbrales de SonarQube** para forzar un estado verde artificial. Se documenta que el estado OK de la línea base original era incondicionado y que el estado ERROR actual refleja con fidelidad la exigencia de los umbrales industriales sobre incrementos de código.

### 3.4. Batería de Pruebas Automatizadas y Rendimiento
El sistema alcanzó un récord de validación con **125 pruebas automatizadas al 100 % de éxito**:
- **Backend (Pytest):** 86 pruebas (3 de cuentas, 9 de ACH, 17 de auditoría, 9 de despliegue, 15 de cifrado, 1 de SLA de carga, 4 de MFA, 10 de pagos recurrentes, 4 de transacciones, 3 de límites y 11 de transferencias).
- **Frontend (Vitest):** 39 pruebas en 7 suites cubriendo componentes visuales y la biblioteca criptográfica WebCrypto RSA/AES.
- **Pruebas de Carga:** El benchmark Locust ejecutó 1.280 transacciones con 100 usuarios concurrentes en 30 segundos, registrando una latencia promedio de 4,12 ms, percentil 95 de **12,8 ms** (ampliamente inferior al SLA de 200 ms) y **0,0 % de fallos** (SLA < 1,0 %).
- **Pruebas de Humo en Vivo:** Se verificaron satisfactoriamente 9 escenarios sobre la infraestructura contenerizada real por HTTPS, incluyendo persistencia entre reinicios y validación de la cadena de bloques del log de auditoría.

---

## 4. Cumplimiento de Requerimientos Funcionales y de Seguridad (Dimensión 4)

El análisis de trazabilidad formalizado en E3_TESSL_TRACEABILITY.csv mapeó 24 requerimientos específicos derivados de las cuatro capacidades de la semilla SEED-3.md:

1. **Cifrado Híbrido Extremo a Extremo:** Los formularios sensibles del frontend interceptan los números de ruta y cuenta bancaria antes de la transmisión de red, los encriptan mediante AES-256-GCM con una clave de sesión efímera, y encapsulan dicha clave mediante RSA-OAEP utilizando la clave pública RSA-2048 del servidor obtenida vía GET /api/crypto/public-key. En el backend, las coordenadas se descifran en memoria y se re-encriptan para almacenamiento persistente con AES-256-GCM bajo el formato enc:v1:<iv>:<ct>:<tag>. La migración de datos legados demostró ser idempotente y transaccionalmente segura.
2. **Libro Mayor de Auditoría Inmutable:** Cada operación bancaria genera un bloque que vincula el hash de la operación precedente con la carga útil actual mediante una firma HMAC-SHA256. Disparadores SQL impiden modificaciones o borrados directos en la base de datos, y el esquema transaccional garantiza que si el registro de auditoría falla, la transacción financiera se revierte íntegramente. El endpoint GET /api/audit/verify permite auditar la cadena completa mediante autenticación administrativa X-Admin-Key.
3. **Pruebas de Carga:** Se demostró la resiliencia del motor FastAPI/SQLite en modo WAL ante una concurrencia masiva simulada, protegiendo los datos productivos mediante bases de datos efímeras descartables.
4. **Despliegue Contenerizado Endurecido:** Los contenedores se ejecutan sin privilegios de root (ppuser UID 1000 en backend y 
ginx UID 101 en frontend), sirviendo tráfico HTTPS mediante certificados locales reproducibles y redirigiendo automáticamente el puerto HTTP 8080/80 al puerto seguro 8443/443. La eliminación de secretos por defecto garantiza que la infraestructura no pueda arrancar sin configuración explícita.

---

## 5. Esfuerzo, Intervención Humana y Límites Metodológicos (Dimensiones 1 y 5)

### 5.1. Esfuerzo y Telemetría
El ciclo experimental abarcó **23 interacciones formales** documentadas exhaustivamente en E3_TESSL_REGISTRO_01_INTERACCIONES.md. La interacción humana se concentró en la aprobación inicial de especificaciones, el desbloqueo de credenciales de infraestructura, y la autorización de planes de remediación de prioridad y cierre de calidad. Las métricas cuantitativas de tokens de entrada/salida y tiempos de pared no fueron exportadas de manera aislada por el CLI en esta sesión específica, por lo que se declaran formalmente como **N/D** (no disponible), garantizando que no se introduzcan estimaciones no comprobadas empíricamente.

### 5.2. Comparación Longitudinal con Etapas Previas
| Métrica Clave | Etapa 1 Final | Etapa 2 Final | Etapa 3 Cierre | Variación E3 vs E2 |
|---|---:|---:|---:|---:|
| **LOC no comentadas (
cloc)** | 2.182 | 4.267 | **5.536** | +1.269 (+29,7 %) |
| **Líneas de Especificación** | 241 | 575 | **1.093** | +518 (+90,1 %) |
| **Archivos de Especificación** | 4 | 7 | **11** | +4 (+57,1 %) |
| **Pruebas Automatizadas Totales** | 45 | 78 | **125** | +47 (+60,3 %) |
| **Bugs Tradicionales SonarQube** | 0 | 0 | **0** | 0 |
| **Vulnerabilidades SonarQube** | 0 | 0 | **0** | 0 |
| **Code Smells SonarQube** | 21 | 51 | **72** | +21 (+41,2 %) |
| **Deuda Técnica (minutos)** | 82 | 276 | **491** | +215 (+77,9 %) |
| **Complejidad Cognitiva** | 98 | 337 | **624** | +287 (+85,2 %) |
| **Cobertura Importada** | N/D | 0,0 % (no imp.) | **77,9 %** | +77,9 pp |

El código de producción se expandió un 29,7 % respecto a la Etapa 2 (+153,7 % respecto a E1), mientras que la batería de pruebas se incrementó en un 60,3 % (de 78 a 125 pruebas), manteniendo una tasa de éxito del 100 %.

### 5.3. Limitaciones Metodológicas y Advertencia sobre Base de Datos
1. **Marca de Tiempo en Base de Datos:** Se identificó que el archivo auxiliar SQLite shift_bank.db-shm actualizó su marca de tiempo durante la ejecución de las pruebas locales de humo. Aunque se verificó que la base de datos principal shift_bank.db preservó exactamente su tamaño íntegro de 155.648 bytes y ninguna tabla productiva sufrió alteraciones, se registra la advertencia formal de que la no-modificación histórica no puede ser certificada de forma estrictamente independiente mediante marcas de tiempo del sistema de archivos.
2. **Aislamiento de Docker:** Para garantizar la protección de datos preexistentes, las pruebas de despliegue se efectuaron con un volumen descartable temporal (shiftbank_disposable_test_data), manteniendo el volumen original shiftbank_data inalterado.
3. **Calidad Estática Residual:** Las 72 incidencias de code smells abiertas no fueron remediadas para no iniciar un ciclo de refactorización abierto que invalidara la comparabilidad experimental con las demás herramientas del estudio.

---

## 6. Conclusiones y Aportes a la Tesis

La evaluación de Tessl SDD en la Etapa 3 de Shift Bank demuestra que el desarrollo guiado por especificaciones proporciona un marco altamente efectivo para gestionar transformaciones de software críticas en sistemas existentes:
- **Eficacia Contractual:** La especificación previa de contratos criptográficos y de despliegue evitó desviaciones funcionales y permitió implementar flujos complejos (cifrado asimétrico en cliente, verificación transaccional de auditoría) con cero defectos de fiabilidad y seguridad al cierre.
- **Rigor en la Medición:** El desacoplamiento entre la importación de cobertura (78,0 %) y las correcciones de código demostró la importancia de distinguir artefactos de medición de mejoras de calidad genuinas.
- **Transparencia en Clean Code:** El estado final de Quality Gate en ERROR bajo CAYC, reportado sin atajos metodológicos, valida el comportamiento de los estándares industriales modernos y establece una base cuantitativa objetiva para contrastar el desempeño de Tessl frente a las metodologías alternativas evaluadas en esta tesis.
