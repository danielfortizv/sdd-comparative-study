# Etapa 4 — Tessl: Descubrimiento y levantamiento de requisitos

**Caso de estudio:** Shift Bank  
**Objetivo:** Migración hacia un sistema multimoneda con Event Sourcing y CQRS.  
**Estado:** Levantamiento de requisitos, previo a la especificación e implementación.

## 1. Contexto inicial

La Etapa 4 parte de la implementación desarrollada durante la Etapa 3, conservando las funcionalidades bancarias y los mecanismos de seguridad previamente incorporados. Durante la preparación se registró una correspondencia de 112/112 hashes de archivos incluidos y una línea base de 86 pruebas backend aprobadas, 37 pruebas frontend aprobadas y 2 pruebas criptográficas frontend fallidas, cuya causa permanece sin confirmar.

## 2. Descubrimiento de la arquitectura

Gemini CLI, utilizando la integración local de Tessl, inspeccionó los modelos, servicios, contratos y especificaciones existentes sin modificar el código.

Identificó una arquitectura basada en SQLite y SQLAlchemy, con saldos monetarios almacenados mediante valores de punto flotante y transferencias que modifican directamente los saldos persistidos.

Se verificó, según la inspección reportada por el agente, la existencia de un registro de auditoría criptográfico inmutable. Sin embargo, dicho registro no constituye un mecanismo de Event Sourcing y la aplicación todavía no implementa CQRS.

## 3. Incidencia durante la inicialización

La primera transmisión del prompt quedó truncada durante el cuarto requisito de la semilla, correspondiente a CQRS. Gemini identificó la interrupción y solicitó el contenido restante.

La continuación enviada no recuperó íntegramente los requisitos omitidos. Por esta razón se preparó un mensaje correctivo con el contenido original faltante, manteniendo sin modificaciones la semilla común.

Esta incidencia se clasifica como un problema de transmisión y conservación del contexto experimental, no como un defecto de implementación. La confirmación de recuperación permanece pendiente de la siguiente interacción.

## 4. Primera decisión de requisitos

La primera pregunta formulada por Tessl abordó las monedas admitidas y la organización de los saldos.

Se preparó la decisión D-01: admitir USD, EUR y GBP, manteniendo una moneda fija por cuenta y permitiendo que el usuario posea diferentes cuentas denominadas en distintas monedas.

Las conversiones se realizarán entre cuentas de monedas diferentes. La migración deberá conservar los valores originales de las cuentas heredadas sin efectuar conversiones automáticas.

Esta decisión se documentará separadamente de la semilla para conservar su identidad entre las cinco herramientas evaluadas.

## 5. Estado y observaciones metodológicas

Durante el descubrimiento no se observaron modificaciones a especificaciones, código, pruebas ni bases de datos. Tampoco se ejecutaron nuevas pruebas o compilaciones.

El resultado representa únicamente una inspección inicial realizada por el agente, no una validación de la migración.

Las métricas de consumo, tiempo, modificaciones documentales y calidad del código deberán obtenerse posteriormente de las evidencias correspondientes. No se asignarán valores sin mediciones verificables.

### Levantamiento de requisitos — Interacción 2

Gemini CLI confirmó la recuperación íntegra de los seis requisitos establecidos en la semilla común de la Etapa 4 y reconoció la primera decisión de negocio (D-01), relacionada con las monedas soportadas y la estructura de las cuentas.

Posteriormente, el agente formuló una segunda pregunta acerca de la provisión de cuentas denominadas en EUR y GBP. Se definió como respuesta D-02 la incorporación de dos cuentas adicionales con saldos iniciales nulos, preservando las cuentas USD heredadas y evitando agregar funcionalidades de apertura de cuentas por parte del usuario.

La decisión también establece que la provisión debe ser idempotente, impidiendo la duplicación de cuentas o la alteración de saldos existentes durante reinicios o reintentos de migración.

**Observación metodológica:** aunque el encabezado de la intervención anunciaba una aclaración sobre tasas de cambio, comisiones y precisión, la pregunta efectivamente formulada correspondía a la provisión de cuentas. Se conserva esta distinción para asegurar la trazabilidad.

**Estado:** D-01 confirmada por el agente; D-02 preparada para envío. No se han autorizado cambios en especificaciones ni implementación. Permanecen pendientes las decisiones arquitectónicas y monetarias de Event Sourcing, CQRS y conversión.

### Levantamiento de requisitos — Interacción 3: Reglas de conversión monetaria

Gemini CLI confirmó la decisión D-02, correspondiente a la provisión de cuentas EUR y GBP con saldos iniciales nulos, preservando las cuentas USD heredadas y garantizando una migración idempotente. Posteriormente, formuló una tercera pregunta acerca de las tasas de cambio, comisiones y reglas de precisión monetaria.

Como respuesta, se preparó la decisión **D-03**, que establece las siguientes reglas:

- **Tasas de cambio:** se utilizará una tabla interna simulada y fija, con equivalencias de 1 USD = 0,90 EUR y 1 USD = 0,80 GBP. Las tasas inversas y cruzadas se calcularán a partir de una referencia común, sin depender de servicios externos.
- **Comisiones:** no se aplicarán comisiones, cargos adicionales ni diferenciales cambiarios.
- **Precisión monetaria:** todas las monedas manejarán dos decimales. Se utilizará aritmética decimal exacta para evitar errores propios de los números de punto flotante.
- **Redondeo:** se aplicará `ROUND_HALF_UP` una sola vez sobre el importe convertido a la moneda de destino.
- **Trazabilidad:** cada conversión conservará las monedas involucradas, importes originales, tasa aplicada y versión correspondiente, permitiendo reconstruir históricamente las operaciones.
- **Consistencia:** las conversiones deberán garantizar un único débito y crédito por operación exitosa, sin alteración de saldos ante operaciones rechazadas.

Estas decisiones buscan establecer condiciones monetarias deterministas y reproducibles para comparar las cinco herramientas SDD. Asimismo, permiten evaluar la precisión, consistencia transaccional y capacidad de reconstrucción histórica durante la futura incorporación de Event Sourcing y CQRS.

**Estado:** D-01 y D-02 confirmadas por Gemini. D-03 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos; no se han autorizado modificaciones a especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 4: Separación de transferencias y conversiones

Gemini CLI confirmó la decisión D-03, correspondiente a las reglas de conversión monetaria, incluyendo tasas simuladas fijas, ausencia de comisiones, precisión decimal exacta, redondeo `ROUND_HALF_UP` y conservación de la información necesaria para reconstruir las operaciones.

Posteriormente, formuló una cuarta pregunta sobre la separación funcional y arquitectónica entre transferencias internas y conversiones de moneda.

Como respuesta, se preparó la **decisión D-04**, estableciendo las siguientes condiciones:

- **Operación independiente:** las conversiones tendrán un endpoint dedicado (`POST /api/conversions`) y un flujo propio en la interfaz.
- **Compatibilidad:** las transferencias internas existentes (`POST /api/transfers`) conservarán su comportamiento, pero estarán restringidas a cuentas de la misma moneda.
- **Validaciones:** las solicitudes de transferencia entre monedas diferentes deberán rechazarse desde el endpoint heredado, sin modificar los saldos.
- **Consistencia:** las conversiones seguirán las reglas monetarias y transaccionales establecidas en D-01, D-02 y D-03.
- **Alcance:** las transferencias ACH y los pagos recurrentes no realizarán conversiones automáticas hasta definir explícitamente sus reglas multimoneda.

Esta decisión busca conservar las funcionalidades heredadas mientras se introduce una operación diferenciada para la conversión monetaria, facilitando la trazabilidad y la verificación de ambos comportamientos.

**Observación metodológica:** durante la interacción anterior se observó una fragmentación del prompt pegado en Gemini CLI, seguida de una reiteración de la pregunta D-04. Esto se registra como incidencia de interacción con el agente y no como una nueva decisión funcional. Para reducir este riesgo, se utilizarán mensajes más compactos.

**Estado:** D-01, D-02 y D-03 confirmadas. D-04 preparada para envío y pendiente de confirmación. No se han autorizado modificaciones a especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 5: Persistencia de eventos y migración del estado heredado

Gemini CLI confirmó la decisión D-04, estableciendo una separación entre las transferencias internas tradicionales y las conversiones monetarias. Posteriormente, formuló una quinta pregunta relacionada con la persistencia de eventos de dominio y la reconstrucción del estado bancario heredado.

Como respuesta, se preparó la **decisión D-05**, que establece las siguientes condiciones:

- **Persistencia de eventos:** se utilizará una tabla dedicada de eventos de dominio dentro de SQLite, con comportamiento append-only. Esta estructura permanecerá separada del registro criptográfico de auditoría incorporado en la Etapa 3.
- **Estructura de eventos:** cada evento deberá contener un identificador único, tipo, cuenta o agregado asociado, versión o secuencia, fecha de creación y datos necesarios para reconstruir los cambios de estado.
- **Migración de datos:** se realizará una migración única, transaccional e idempotente que preserve los identificadores, monedas, saldos y registros históricos existentes.
- **Reconstrucción inicial:** el estado monetario heredado se representará mediante eventos `AccountStateImported`, conservando los saldos originales. Las transacciones históricas deberán mantenerse identificables sin generar movimientos monetarios adicionales ni inventar acontecimientos no verificables.
- **Cuentas nuevas:** las cuentas EUR y GBP se incorporarán mediante eventos `AccountOpened`, con saldos iniciales de cero.
- **Event Sourcing:** después de la migración, las modificaciones monetarias deberán registrarse mediante eventos persistentes que permitan reconstruir los saldos sin depender de las tablas mutables originales.
- **Seguridad de migración:** se deberán verificar los saldos reconstruidos contra los originales y garantizar reversión transaccional si ocurre algún error.

Esta decisión representa un cambio arquitectónico significativo frente a las etapas anteriores, donde los saldos se modificaban directamente mediante operaciones sobre la base de datos relacional. La nueva estructura permitirá evaluar la capacidad de Tessl para gestionar una migración hacia Event Sourcing sin perder información ni comprometer las funcionalidades heredadas.

**Observación metodológica:** se optó por reutilizar SQLite para evitar introducir infraestructura adicional que pudiera afectar la comparación experimental. Se conserva una separación conceptual y funcional entre los eventos de dominio y los registros de auditoría de seguridad.

**Estado:** D-01 a D-04 confirmadas por Gemini. D-05 preparada para envío y pendiente de confirmación. Continúan pendientes las decisiones sobre CQRS, consistencia de proyecciones, concurrencia, recuperación ante fallos y compatibilidad de operaciones heredadas. No se han autorizado cambios a las especificaciones ni a la implementación.

### Levantamiento de requisitos — Interacción 6: Consistencia de CQRS y reconstrucción de proyecciones

Gemini CLI confirmó la decisión D-05, relacionada con la introducción de Event Sourcing mediante una tabla de eventos de dominio independiente del registro de auditoría heredado. También reconoció la estrategia de migración del estado bancario existente y la reconstrucción de saldos a partir de los eventos persistidos.

Posteriormente, formuló una sexta pregunta sobre el modelo de consistencia de las proyecciones CQRS y el procedimiento para reconstruirlas a partir del historial de eventos.

Como respuesta, se preparó la **decisión D-06**, estableciendo las siguientes condiciones:

- **Consistencia inmediata:** se utilizará un modelo de consistencia fuerte mediante actualización síncrona de las proyecciones. Cada comando monetario deberá persistir sus eventos y actualizar las proyecciones correspondientes dentro de una misma transacción de SQLite, garantizando atomicidad.
- **Separación CQRS:** los comandos serán responsables de validar y ejecutar cambios mediante eventos de dominio, mientras que las consultas utilizarán modelos de lectura independientes. El historial de eventos constituirá la fuente de verdad del estado monetario.
- **Proyecciones:** se mantendrán modelos de lectura para saldos por moneda e historial transaccional, incluyendo transferencias, conversiones y metadatos relevantes.
- **Reconstrucción:** se dispondrá de un procedimiento administrativo local para regenerar las proyecciones mediante la reproducción ordenada de los eventos almacenados, sin exponer un endpoint público para esta operación.
- **Verificación al inicio:** la aplicación verificará que las proyecciones existan y estén sincronizadas. Cuando sea necesario, realizará una reconstrucción segura antes de permitir operaciones bancarias.
- **Integridad:** la reconstrucción deberá realizarse de forma atómica y reproducible. Una reconstrucción fallida no podrá reemplazar proyecciones previamente válidas.
- **Prevención de duplicados:** reproducir eventos no podrá generar nuevas transferencias, ejecutar pagos recurrentes, liquidar operaciones ACH ni duplicar registros de auditoría.
- **Verificabilidad:** se deberán definir pruebas de consistencia inmediata, reconstrucción completa, recuperación ante fallos, idempotencia y correspondencia entre los saldos reconstruidos y el historial de eventos.

Esta decisión permite establecer una arquitectura CQRS con consistencia inmediata, evitando que la interfaz presente saldos desactualizados después de una operación exitosa. Al mismo tiempo, la capacidad de reconstrucción proporciona un mecanismo verificable para recuperar modelos de lectura y comprobar que el estado monetario puede derivarse de los eventos persistidos.

Desde la perspectiva experimental, esta decisión permitirá evaluar la capacidad de Tessl para introducir una separación arquitectónica entre lectura y escritura sobre una aplicación existente, conservando sus funcionalidades heredadas y garantizando coherencia entre los eventos y el estado consultado.

**Estado:** D-01 a D-05 confirmadas por Gemini. D-06 preparada para envío y pendiente de confirmación. Continúan pendientes las decisiones sobre límites de eventos, concurrencia, idempotencia, compatibilidad multimoneda de ACH y pagos recurrentes, MFA y límites dinámicos. No se han autorizado cambios en especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 7: Límites dinámicos y MFA multimoneda

Gemini CLI confirmó la decisión D-06, correspondiente al modelo de consistencia inmediata de CQRS, la actualización transaccional de las proyecciones y su reconstrucción determinista mediante los eventos almacenados.

Posteriormente, formuló una séptima pregunta relacionada con la aplicación de límites dinámicos y mecanismos de autenticación multifactor (MFA) sobre operaciones realizadas en distintas monedas.

Como respuesta, se preparó la **decisión D-07**, estableciendo las siguientes condiciones:

- **Moneda de referencia:** USD será la moneda utilizada para evaluar los límites financieros y los umbrales de MFA. Las operaciones en EUR y GBP se normalizarán utilizando las tasas fijas definidas en D-03.
- **Operaciones incluidas:** los controles financieros se aplicarán a transferencias internas, conversiones monetarias y transferencias ACH admitidas.
- **Límites existentes:** se conservarán los valores predeterminados heredados de USD 5.000 por operación y USD 10.000 diarios.
- **MFA:** se mantendrá el umbral de USD 1.000, requiriendo verificación únicamente cuando el equivalente en dólares supere estrictamente dicho valor.
- **Acumulado diario:** todas las operaciones contabilizables compartirán un único límite diario expresado en USD. Cada operación se contará una sola vez, evitando duplicaciones por movimientos de débito y crédito o reconstrucciones de proyecciones.
- **Operaciones fallidas:** los movimientos rechazados o fallidos no consumirán el límite diario. Se conservarán las reglas heredadas para operaciones ACH pendientes, liquidadas y fallidas.
- **Límites configurables:** el usuario podrá continuar modificando los límites desde la interfaz, manteniendo USD como referencia independientemente de las monedas de sus cuentas.
- **Pagos recurrentes:** se preservará la autorización MFA durante la creación de programaciones y la verificación de límites y fondos disponibles en cada ejecución automática.

Esta decisión permite conservar las restricciones financieras y los mecanismos de seguridad incorporados en las etapas anteriores, adaptándolos al nuevo modelo multimoneda mediante una referencia monetaria uniforme.

Desde la perspectiva experimental, permitirá evaluar si Tessl mantiene la consistencia de reglas de negocio previamente implementadas durante una migración arquitectónica compleja, particularmente cuando las operaciones involucran diferentes monedas y deben integrarse con Event Sourcing y CQRS.

**Estado:** D-01 a D-06 confirmadas por Gemini. D-07 preparada para envío y pendiente de confirmación. Continúan pendientes las decisiones sobre compatibilidad multimoneda de ACH y pagos recurrentes, límites de eventos, concurrencia e idempotencia. No se han autorizado modificaciones a las especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 8: Compatibilidad multimoneda de transferencias ACH y pagos recurrentes

Gemini CLI confirmó la decisión D-07, correspondiente a la aplicación de límites dinámicos y mecanismos MFA en operaciones multimoneda. Se estableció USD como moneda de referencia para evaluar los límites financieros, normalizando los importes mediante las tasas de conversión previamente definidas.

Posteriormente, el agente formuló una octava pregunta relacionada con las restricciones monetarias de las transferencias ACH y la posibilidad de programar conversiones automáticas mediante pagos recurrentes.

Como respuesta, se preparó la **decisión D-08**, que establece las siguientes condiciones:

- **Transferencias ACH:** se mantendrán restringidas a cuentas denominadas en USD, conservando el modelo bancario estadounidense simulado y las validaciones heredadas de números de ruta y cuentas beneficiarias.
- **Compatibilidad ACH:** se preservarán los estados `pending`, `settled` y `failed`, incluyendo la liquidación simulada y la devolución exacta de fondos cuando una transferencia falle.
- **Pagos recurrentes internos:** únicamente se permitirán programaciones entre cuentas que compartan la misma moneda, independientemente de que sea USD, EUR o GBP.
- **Pagos recurrentes ACH:** se mantendrán exclusivamente en USD, sin conversiones implícitas ni soporte para redes bancarias internacionales.
- **Conversiones automáticas:** no se incorporará la posibilidad de programar conversiones periódicas. Las operaciones de cambio de moneda deberán ejecutarse explícitamente mediante el flujo de conversión definido en D-04.
- **Migración de programaciones:** las programaciones existentes deberán conservar sus importes, fechas, destinatarios y configuraciones, incorporando una identidad monetaria explícita sin alterar su comportamiento.
- **Seguridad y límites:** cada ejecución automática deberá verificar los saldos disponibles y límites dinámicos vigentes. Se conservará la autorización MFA durante la creación de programaciones.
- **Event Sourcing:** los movimientos monetarios y cambios de estado derivados de operaciones ACH o recurrentes deberán integrarse con el nuevo modelo de eventos, evitando cobros, liquidaciones y reintegros duplicados.

Esta decisión delimita el alcance funcional del sistema multimoneda, manteniendo la compatibilidad con las operaciones heredadas sin incorporar transferencias internacionales ni conversiones recurrentes automáticas.

Desde la perspectiva experimental, permite evaluar la capacidad de Tessl para adaptar funcionalidades preexistentes a un nuevo modelo de datos y arquitectura, manteniendo las restricciones originales y evitando la introducción de comportamientos no solicitados.

**Estado:** D-01 a D-07 confirmadas por Gemini. D-08 preparada para envío y pendiente de confirmación. Continúan pendientes las decisiones sobre límites de eventos, concurrencia, idempotencia y recuperación ante fallos. No se han autorizado modificaciones a las especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 9: Límites de eventos, concurrencia e idempotencia

Gemini CLI confirmó la decisión D-08, correspondiente a las restricciones monetarias de las transferencias ACH y los pagos recurrentes. Posteriormente, formuló una novena pregunta relacionada con la representación de eventos de dominio, el control de concurrencia y los mecanismos necesarios para evitar operaciones duplicadas.

Como respuesta, se preparó la **decisión D-09**, estableciendo las siguientes condiciones:

- **Límites de eventos:** cada transferencia interna o conversión monetaria exitosa se representará mediante un único evento de dominio que contenga ambos movimientos financieros. Esto permite representar la operación completa como una unidad de negocio indivisible.
- **Atomicidad:** los movimientos de débito y crédito, la persistencia del evento y la actualización de las proyecciones CQRS deberán ejecutarse dentro de una misma transacción de SQLite. Ante cualquier fallo, la operación deberá revertirse completamente.
- **Control de concurrencia:** se utilizará concurrencia optimista mediante versiones esperadas de las cuentas involucradas. Las operaciones deberán verificar dichas versiones antes de confirmar cambios, evitando condiciones de carrera, actualizaciones perdidas y sobregiros.
- **Idempotencia:** cada comando financiero iniciado por el usuario deberá disponer de una clave única de idempotencia. Repetir una solicitud con la misma clave y los mismos parámetros devolverá el resultado original sin ejecutar nuevamente la operación. La reutilización de una clave con parámetros diferentes deberá rechazarse.
- **Operaciones automáticas:** las ejecuciones de pagos recurrentes y los cambios de estado ACH utilizarán identificadores deterministas para impedir cobros, liquidaciones o reintegros duplicados ante reintentos y reinicios.
- **Eventos ACH:** el inicio de una transferencia generará un evento con el débito y estado pendiente. La liquidación posterior registrará un cambio de estado sin repetir el débito. En caso de fallo, se registrará el reintegro exacto mediante un evento independiente.
- **Reconstrucción:** los eventos deberán contener información suficiente para reconstruir el estado de las cuentas de forma determinista, sin ejecutar nuevamente operaciones financieras ni generar efectos secundarios.
- **Verificación:** se deberán definir escenarios de aceptación que evalúen transferencias simultáneas, conflictos de versiones, insuficiencia de fondos, solicitudes duplicadas, fallos transaccionales y reproducción de eventos.

Esta decisión busca garantizar la integridad del sistema bancario frente a operaciones concurrentes, reintentos y fallos parciales. Su importancia aumenta con la introducción de Event Sourcing, dado que una duplicación en la aplicación de eventos podría producir inconsistencias permanentes en los saldos reconstruidos.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para especificar y posteriormente implementar mecanismos de consistencia transaccional, control de concurrencia e idempotencia durante una migración arquitectónica profunda, sin comprometer el comportamiento de las funcionalidades heredadas.

**Estado:** D-01 a D-08 confirmadas por Gemini. D-09 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos, sin autorización para modificar especificaciones ni implementar código.

### Levantamiento de requisitos — Interacción 10: Visualización de saldos multimoneda

Gemini CLI confirmó la decisión D-09, correspondiente a la definición de eventos atómicos para transferencias y conversiones, el control de concurrencia optimista y los mecanismos de idempotencia para prevenir operaciones duplicadas. Posteriormente, formuló una décima pregunta relacionada con la presentación de saldos multimoneda y el cálculo del saldo agregado en la interfaz.

Como respuesta, se preparó la **decisión D-10**, estableciendo las siguientes condiciones:

- **Visualización por moneda:** la interfaz mostrará los saldos individuales de cada cuenta y los totales separados para USD, EUR y GBP, evitando sumar directamente cantidades expresadas en monedas diferentes.
- **Saldo global estimado:** el encabezado principal presentará un total equivalente en USD, calculado mediante las tasas simuladas definidas en D-03.
- **Precisión:** el cálculo agregado utilizará aritmética decimal exacta y aplicará `ROUND_HALF_UP` únicamente al resultado final, manteniendo dos decimales.
- **Transparencia:** el total global se identificará explícitamente como una valoración estimada en USD, no como un saldo bancario real. También se informarán las tasas simuladas utilizadas.
- **Historial transaccional:** las operaciones conservarán sus importes y monedas originales. Las conversiones mostrarán ambas cantidades y la tasa aplicada.
- **Integración con CQRS:** todos los saldos e historiales presentados se obtendrán de las proyecciones de lectura, garantizando consistencia inmediata después de operaciones exitosas.
- **Compatibilidad:** se conservarán las funcionalidades de navegación, consulta de cuentas e historial existentes, adaptando su presentación al nuevo modelo monetario.

Esta decisión permite combinar una representación financieramente correcta de los saldos con una visualización agregada que facilita al usuario comprender el valor estimado de sus fondos.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para adaptar una interfaz diseñada originalmente para cuentas en USD hacia una representación multimoneda, manteniendo la precisión monetaria, la coherencia con las proyecciones CQRS y la compatibilidad con las funcionalidades heredadas.

**Estado:** D-01 a D-09 confirmadas por Gemini. D-10 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos; no se han autorizado modificaciones a las especificaciones ni implementación.
### Levantamiento de requisitos — Interacción 11: Integración del cifrado y la auditoría transaccional

Gemini CLI confirmó la decisión D-10, correspondiente a la presentación de saldos multimoneda y el cálculo del total estimado en USD mediante las proyecciones CQRS. Posteriormente, formuló una undécima pregunta relacionada con la protección de información sensible dentro de los eventos de dominio y su integración con los mecanismos criptográficos de auditoría heredados.

Como respuesta, se preparó la **decisión D-11**, estableciendo las siguientes condiciones:

- **Cifrado de información sensible:** se conservará el mecanismo AES-256-GCM incorporado en la Etapa 3 para proteger números de cuenta, identificadores bancarios y demás datos sensibles. Los eventos de dominio deberán evitar almacenar información confidencial innecesaria y cifrar los campos protegidos cuando sea indispensable conservarlos.
- **Seguridad del Event Store:** los eventos permanecerán inmutables y deberán permitir la reconstrucción autorizada del estado financiero sin exponer información sensible ni comprometer la integridad del historial.
- **Auditoría independiente:** se mantendrá el registro criptográfico HMAC-SHA256 heredado, separado de los eventos utilizados por Event Sourcing. Las conversiones monetarias y demás operaciones financieras relevantes generarán registros de auditoría.
- **Operaciones exitosas y fallidas:** se registrarán los resultados de las conversiones y los intentos rechazados conforme a la política de auditoría, sin generar movimientos monetarios cuando una operación falle.
- **Atomicidad:** los eventos financieros exitosos, las actualizaciones CQRS y los registros de auditoría requeridos deberán conservar garantías de consistencia transaccional, evitando estados incompletos.
- **Idempotencia:** los reintentos de operaciones no podrán duplicar movimientos financieros ni registros de auditoría correspondientes a operaciones exitosas ya procesadas.
- **Reconstrucción:** reproducir eventos para reconstruir proyecciones no deberá generar nuevos registros de auditoría ni repetir operaciones bancarias.
- **Regresión de seguridad:** se deberán verificar el cifrado, la integridad de los registros y la protección de información sensible. Las dos pruebas criptográficas fallidas identificadas durante la preparación de la Etapa 4 permanecerán documentadas como limitaciones preexistentes cuya causa aún no ha sido confirmada.

Esta decisión busca garantizar que la migración hacia Event Sourcing y CQRS no comprometa los mecanismos de seguridad previamente implementados. La separación entre eventos de dominio y registros de auditoría permite diferenciar la reconstrucción funcional del estado bancario de la trazabilidad criptográfica de las operaciones.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para conservar requisitos no funcionales de seguridad durante una transformación arquitectónica profunda, evitando regresiones y manteniendo la coherencia entre especificaciones nuevas y heredadas.

**Estado:** D-01 a D-10 confirmadas por Gemini. D-11 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos; no se han autorizado modificaciones a las especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 12: Restricciones de infraestructura y despliegue

Gemini CLI confirmó la decisión D-11, correspondiente a la integración de los mecanismos de cifrado AES-256-GCM y auditoría criptográfica HMAC-SHA256 con la nueva arquitectura basada en eventos. Posteriormente, formuló una duodécima pregunta relacionada con los requisitos de infraestructura, contenedores y configuración necesarios para ejecutar Event Sourcing y CQRS.

Como respuesta, se preparó la **decisión D-12**, estableciendo las siguientes condiciones:

- **Infraestructura existente:** se conservará la arquitectura Docker Compose heredada, compuesta por FastAPI, React/TypeScript, Nginx con TLS y una base de datos SQLite persistente. No se incorporarán nuevas bases de datos, servicios externos ni intermediarios de mensajes.
- **Integración arquitectónica:** el almacenamiento de eventos, los manejadores de comandos y las proyecciones CQRS se implementarán dentro del backend existente, utilizando SQLite como mecanismo de persistencia.
- **Procesamiento automático:** se conservarán los procesos heredados de pagos recurrentes y liquidación ACH, adaptándolos a Event Sourcing sin introducir servicios independientes adicionales.
- **Persistencia:** los eventos, saldos, proyecciones y registros de auditoría deberán conservarse durante reinicios y redespliegues, evitando pérdidas de información o duplicaciones durante las migraciones.
- **Seguridad:** se reutilizarán las variables `ENCRYPTION_KEY`, `AUDIT_SECRET_KEY` y `ADMIN_SECRET_KEY`, preservando las claves criptográficas y evitando incorporar credenciales directamente en el código.
- **Configuración:** las tasas de cambio simuladas permanecerán configuradas internamente, sin necesidad de servicios externos. Se evitarán nuevas variables de entorno obligatorias, salvo justificación y aprobación explícita.
- **Reconstrucción administrativa:** la regeneración de proyecciones se realizará mediante una herramienta administrativa local dentro del entorno del backend, sin requerir un servicio permanente adicional.
- **Recuperación:** durante el inicio de la aplicación deberán verificarse el estado de las migraciones y la consistencia de las proyecciones. Los errores de recuperación deberán impedir operaciones financieras sobre estados inconsistentes.
- **Verificación:** se deberán establecer escenarios de aceptación para reinicios de contenedores, persistencia de eventos, recuperación de proyecciones, compatibilidad del cifrado y conservación de las funcionalidades de despliegue heredadas.

Esta decisión establece que la migración hacia Event Sourcing y CQRS deberá realizarse aprovechando la infraestructura existente, sin introducir componentes externos que incrementen innecesariamente la complejidad operativa.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para transformar profundamente la arquitectura interna de una aplicación existente mientras conserva sus restricciones tecnológicas, mecanismos de seguridad y capacidades de despliegue.

**Estado:** D-01 a D-11 confirmadas por Gemini. D-12 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos; todavía no se han autorizado modificaciones a las especificaciones ni a la implementación.

### Levantamiento de requisitos — Interacción 13: Contrato de idempotencia y manejo de conflictos HTTP

Gemini CLI confirmó la decisión D-12, correspondiente a la conservación de la infraestructura Docker Compose heredada y la implementación de Event Sourcing y CQRS dentro del backend existente. Posteriormente, formuló una decimotercera pregunta relacionada con el mecanismo de transmisión de claves de idempotencia y el tratamiento de conflictos en las operaciones financieras.

Como respuesta, se preparó la **decisión D-13**, estableciendo las siguientes condiciones:

- **Contrato de idempotencia:** las transferencias internas, conversiones monetarias y transferencias ACH deberán recibir una clave única mediante el encabezado HTTP `Idempotency-Key`. Cada nueva operación utilizará un UUID diferente, conservando la misma clave durante sus reintentos.
- **Validación:** las solicitudes sin una clave válida serán rechazadas mediante HTTP 400, utilizando códigos de error estructurados.
- **Reintentos seguros:** cuando se reciba una solicitud previamente confirmada con la misma clave y parámetros, el sistema devolverá el resultado original sin ejecutar nuevamente los movimientos financieros.
- **Conflictos de parámetros:** reutilizar una clave con parámetros diferentes producirá HTTP 409 Conflict, acompañado del código `IDEMPOTENCY_KEY_REUSE`.
- **Concurrencia optimista:** las operaciones que utilicen versiones desactualizadas de las cuentas involucradas serán rechazadas mediante HTTP 409 y el código `ACCOUNT_VERSION_CONFLICT`.
- **Errores estructurados:** las respuestas de error deberán contener códigos identificables y mensajes comprensibles, evitando exponer información financiera sensible.
- **Atomicidad:** el registro de idempotencia, los eventos de dominio, las actualizaciones CQRS y los registros de auditoría requeridos deberán conservar consistencia transaccional.
- **Compatibilidad:** el frontend deberá adaptarse para generar y transmitir el encabezado obligatorio, manteniendo los flujos bancarios existentes.
- **Verificación:** se definirán escenarios para solicitudes duplicadas, claves inválidas, conflictos de parámetros, concurrencia, interrupciones y recuperación después de operaciones confirmadas.

Esta decisión complementa los mecanismos de concurrencia e integridad definidos en D-09, estableciendo un contrato explícito entre los clientes y el backend para prevenir operaciones monetarias duplicadas.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para gestionar modificaciones en contratos API heredados, garantizar coherencia entre especificaciones y código y mantener la integridad transaccional durante la migración hacia Event Sourcing y CQRS.

**Estado:** D-01 a D-12 confirmadas por Gemini. D-13 preparada para envío y pendiente de confirmación. Continúa el levantamiento de requisitos; no se han autorizado modificaciones a las especificaciones ni implementación.

### Levantamiento de requisitos — Interacción 14: Versionado de cuentas y contrato de concurrencia optimista

Gemini CLI confirmó la decisión D-13, correspondiente al contrato de idempotencia mediante encabezados HTTP, la reutilización segura de solicitudes y el manejo estructurado de conflictos. Posteriormente, formuló una decimocuarta pregunta relacionada con la exposición de versiones de cuentas y su utilización para controlar operaciones financieras concurrentes.

Como respuesta, se preparó la **decisión D-14**, estableciendo las siguientes condiciones:

- **Versionado de cuentas:** las respuestas `AccountResponse` deberán incluir un campo `version` de tipo entero no negativo, correspondiente a la versión vigente de cada cuenta. Esta información se mantendrá sincronizada con los eventos de dominio y las proyecciones CQRS.
- **Contratos API:** las transferencias internas y conversiones monetarias requerirán los campos `expected_from_version` y `expected_to_version`, mientras que las transferencias ACH únicamente necesitarán la versión de la cuenta origen.
- **Validación de concurrencia:** antes de confirmar una operación, el sistema verificará que las versiones proporcionadas coincidan con las versiones vigentes. Las solicitudes con versiones desactualizadas serán rechazadas mediante HTTP 409 y el código `ACCOUNT_VERSION_CONFLICT`.
- **Actualización de versiones:** cada evento monetario confirmado incrementará una vez la versión de las cuentas afectadas. Los eventos de transferencia o conversión actualizarán las versiones de ambas cuentas de forma atómica.
- **Integridad transaccional:** las validaciones de versiones, la persistencia de eventos y las actualizaciones CQRS deberán realizarse dentro de una misma transacción de SQLite, evitando actualizaciones perdidas y operaciones parcialmente ejecutadas.
- **Compatibilidad con idempotencia:** una solicitud previamente confirmada podrá recuperar su resultado original, incluso cuando las versiones actuales de las cuentas hayan cambiado. Los reintentos no deberán generar nuevos movimientos ni incrementar versiones.
- **Integración frontend:** la interfaz utilizará las versiones obtenidas de las consultas y las enviará en las solicitudes financieras. Ante un conflicto, actualizará la información y notificará al usuario sin repetir automáticamente la operación.
- **Operaciones automáticas:** los pagos recurrentes y procesos ACH utilizarán versiones actuales obtenidas internamente, conservando sus mecanismos de idempotencia.
- **Migración y verificación:** las cuentas heredadas deberán recibir versiones iniciales consistentes con el historial de eventos. Se definirán pruebas para operaciones concurrentes, conflictos, reintentos, actualizaciones de versiones y reconstrucción del estado.

Esta decisión complementa los mecanismos de Event Sourcing e idempotencia definidos previamente, incorporando un contrato explícito de concurrencia entre la interfaz y el backend.

Desde la perspectiva experimental, permitirá evaluar la capacidad de Tessl para introducir control de concurrencia optimista sobre una aplicación bancaria existente, adaptando los contratos API, las proyecciones CQRS y los eventos de dominio sin comprometer la integridad financiera.

**Estado:** D-01 a D-13 confirmadas por Gemini. D-14 preparada para envío y pendiente de confirmación. Si no persisten ambigüedades relevantes, el siguiente hito será la presentación del plan de especificaciones para aprobación explícita. No se han autorizado modificaciones al código ni a las especificaciones.

### Fase de especificación — Interacción 15: Aprobación del plan de especificaciones

Gemini CLI confirmó la decisión D-14, correspondiente al versionado explícito de cuentas y al contrato de concurrencia optimista. Con esta confirmación, el agente declaró finalizado el levantamiento inicial de requisitos, conformado por catorce decisiones de negocio y arquitectura (D-01 a D-14).

Posteriormente, siguiendo el flujo de trabajo de Tessl, presentó un plan de especificaciones para la migración multimoneda y la incorporación de Event Sourcing y CQRS.

El plan propuso la creación de **dos nuevas especificaciones**:

- `currency_conversion.spec.md`: definición de las conversiones monetarias, tasas simuladas, precisión decimal, validaciones, controles financieros, eventos de dominio e interfaz de usuario.
- `event_sourcing_cqrs.spec.md`: definición del almacenamiento de eventos, migración del estado heredado, procesamiento de comandos, proyecciones de lectura y mecanismos de reconstrucción.

Adicionalmente, identificó **ocho especificaciones existentes que requieren modificaciones**:

- `accounts.spec.md`: cuentas multimoneda, versionado y visualización de saldos.
- `transfers.spec.md`: restricciones de moneda, concurrencia, idempotencia y eventos financieros.
- `transactions.spec.md`: historial transaccional derivado de proyecciones CQRS.
- `transfer_limits.spec.md`: evaluación de límites utilizando USD como moneda de referencia.
- `mfa.spec.md`: aplicación de los umbrales de seguridad sobre importes equivalentes en USD.
- `ach_transfers.spec.md`: restricciones USD y adaptación de liquidaciones y reintegros al modelo de eventos.
- `recurring_payments.spec.md`: compatibilidad de programaciones con las nuevas reglas monetarias.
- `audit_log.spec.md`: integración de la auditoría criptográfica con las nuevas operaciones.

El agente también identificó cambios incompatibles con los contratos anteriores, incluyendo nuevos campos obligatorios de versionado, encabezados de idempotencia, restricciones sobre transferencias entre monedas diferentes y modificaciones en las respuestas de cuentas y en la visualización del dashboard.

**Intervención humana:** se preparó la aprobación explícita del plan de especificaciones, complementándola con requisitos de trazabilidad, verificabilidad, integridad transaccional, recuperación ante fallos y compatibilidad con las funcionalidades heredadas.

La instrucción autoriza exclusivamente la creación y modificación de especificaciones mediante el flujo nativo de Tessl, seguida de su verificación. No autoriza la modificación del código fuente, pruebas, bases de datos ni infraestructura de despliegue.

**Observación metodológica:** esta separación permite evaluar la capacidad de Tessl para transformar decisiones expresadas en lenguaje natural en contratos persistentes y verificables antes de iniciar la generación de código. También proporciona un punto de control humano sobre los cambios arquitectónicos propuestos.

**Estado:** D-01 a D-14 confirmadas. Plan de especificaciones presentado por Gemini y aprobación preparada para envío. La generación y verificación de especificaciones están pendientes de ejecución. La implementación permanece sin autorización.

### Fase de especificación — Interacción 16: Generación, verificación inicial y revisión crítica de especificaciones

Gemini CLI ejecutó la fase de generación de especificaciones utilizando las habilidades `spec-writer` y `spec-verification` de Tessl, después de recibir aprobación explícita del plan documental.

El agente reportó la creación de **dos nuevas especificaciones**:

- `currency_conversion.spec.md`: conversiones monetarias, precisión, tasas simuladas, validaciones, concurrencia e integración con Event Sourcing y CQRS.
- `event_sourcing_cqrs.spec.md`: persistencia de eventos, migración de información heredada, separación de comandos y consultas, reconstrucción de proyecciones y control de versiones.

Adicionalmente, modificó **diez especificaciones existentes**: `accounts`, `transfers`, `transactions`, `transfer_limits`, `mfa`, `ach_transfers`, `recurring_payments`, `audit_log`, `deployment` y `encryption`.

En total, el agente reportó **13 archivos de especificación** en el directorio `specs/`, incluyendo documentos heredados que no necesariamente fueron modificados.

#### Resultados de la verificación inicial

Gemini declaró que las especificaciones mantenían trazabilidad con las decisiones D-01 a D-14 y los seis requisitos de la semilla común. También afirmó que no existían contradicciones ni omisiones y que los archivos respetaban la estructura documental de Tessl.

El agente incorporó referencias a escenarios de pruebas mediante anotaciones `[@test]` y clasificó requisitos como nuevos, modificados o heredados.

Sin embargo, estas afirmaciones corresponden a una **verificación documental realizada por el propio agente**. No constituyen una validación independiente ni demuestran que los requisitos estén implementados. Durante esta fase no se ejecutaron pruebas, compilaciones ni migraciones.

#### Hallazgos de la revisión humana

Después de examinar el reporte de generación, se identificaron posibles inconsistencias que requieren verificación adicional antes de autorizar la implementación:

1. **Precisión monetaria:** distintos contratos continuaban declarando campos monetarios mediante `float`, pese a que D-03 exige aritmética decimal exacta.
2. **Migración de saldos:** la especificación de Event Sourcing incluía importes iniciales fijos de USD 2.500 y USD 10.000, lo que podría entrar en conflicto con la preservación del estado realmente persistido.
3. **Reconstrucción histórica:** no quedó suficientemente demostrado que las transacciones heredadas pudieran recuperarse completamente a partir del historial de eventos después de reconstruir las proyecciones.
4. **Versionado de agregados:** se requiere verificar la correspondencia entre los eventos que afectan múltiples cuentas y las versiones independientes de cada cuenta.
5. **Integridad de proyecciones:** la comparación de checkpoints con el último evento podría resultar insuficiente para detectar proyecciones corruptas cuyo identificador de sincronización permanezca actualizado.
6. **Preservación de requisitos heredados:** varias especificaciones fueron reescritas ampliamente, por lo que es necesario contrastarlas con sus versiones originales para descartar pérdidas de funcionalidades.
7. **Desviación del plan documental:** aunque inicialmente se propusieron ocho modificaciones, el agente realizó diez, incorporando también cambios en las especificaciones de despliegue y cifrado.

Estos hallazgos no demuestran necesariamente defectos de implementación, pero sí justifican una revisión adicional de consistencia y completitud documental.

#### Intervención humana y siguiente acción

Se preparó una solicitud de revisión correctiva dirigida al agente, limitada exclusivamente a los archivos de especificación. La instrucción exige contrastar los contratos generados con las decisiones aprobadas, preservar los requisitos heredados, corregir contradicciones confirmadas y presentar un nuevo informe de verificación.

Esta intervención constituye un ejemplo del papel de supervisión humana dentro de SDD: el resultado de una verificación automática no se acepta como garantía suficiente sin examinar sus supuestos y su coherencia con los requisitos originales.

**Estado:** las especificaciones iniciales fueron generadas y verificadas según el reporte de Gemini. Se identificaron posibles inconsistencias y se preparó una solicitud de revisión correctiva, todavía pendiente de ejecución. La implementación permanece sin autorización.

### Fase de especificación — Interacción 17: Refinamiento correctivo y autorización de implementación

Gemini CLI ejecutó la revisión correctiva de especificaciones solicitada después de identificar posibles inconsistencias en la primera versión documental de la Etapa 4. El agente confirmó los siete aspectos señalados durante la revisión humana y reportó modificaciones dirigidas a mejorar la precisión, consistencia y compatibilidad de los contratos.

#### Correcciones realizadas

**Precisión monetaria.** Se reemplazaron declaraciones `float` por `Decimal` en los contratos monetarios de cuentas, conversiones, transferencias, historial, límites, MFA, ACH y pagos recurrentes. También se especificó el uso de representaciones decimales exactas durante la serialización y el procesamiento en el frontend.

**Migración del estado heredado.** Se eliminó la dependencia de saldos iniciales codificados directamente. La migración deberá consultar los valores realmente almacenados antes de generar los eventos iniciales, preservando las cuentas y sus movimientos históricos.

**Reconstrucción del historial.** Se incorporó el evento `LegacyTransactionImported`, diseñado para representar transacciones anteriores sin volver a aplicar sus efectos monetarios. Esto permitirá reconstruir el historial transaccional mediante los eventos persistidos.

**Versionado y concurrencia.** Se aclaró cómo los eventos de transferencias y conversiones contienen las versiones resultantes de ambas cuentas, permitiendo reproducir su evolución de manera independiente.

**Integridad de proyecciones.** Se fortaleció el procedimiento de verificación incorporando comprobaciones adicionales a la comparación de checkpoints, con mecanismos de reconstrucción ante inconsistencias.

**Preservación de funcionalidades.** El agente reportó la recuperación de requisitos detallados relacionados con los endpoints de simulación ACH y pagos recurrentes, referencias de reintegro, intervalos de programación, transiciones de estado, controles de concurrencia SQLite y protección administrativa.

**Alcance documental.** Se aclaró que las modificaciones adicionales de `deployment.spec.md` y `encryption.spec.md` responden a los requisitos de seguridad y despliegue previamente aprobados.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Especificaciones totales | 13 |
| Especificaciones nuevas | 2 |
| Especificaciones modificadas | 10 |
| Especificaciones heredadas sin cambios | 1 |
| Requisitos verificables declarados | 118 |
| Referencias estáticas a pruebas declaradas | 124 |
| Pruebas ejecutadas durante la especificación | 0 |

Gemini declaró que no persistían contradicciones u omisiones identificadas después del refinamiento. Sin embargo, esta conclusión corresponde a su propia verificación documental; la conformidad de la implementación y el comportamiento real todavía requieren validación mediante pruebas.

#### Transición hacia la implementación

A partir del reporte, se preparó la **autorización explícita para iniciar la implementación**, respetando los contratos definidos en las especificaciones.

La autorización establece una implementación incremental, comenzando por los modelos monetarios, la migración y el almacenamiento de eventos, seguida de CQRS, comandos financieros, integración de funcionalidades heredadas, contratos API e interfaz de usuario.

También exige conservar el estado previo de la base de datos, ejecutar pruebas de regresión y documentar los resultados observados. Las dos fallas criptográficas del frontend identificadas durante la preparación de la Etapa 4 permanecen clasificadas como limitaciones heredadas pendientes de investigación.

Desde la perspectiva metodológica, esta interacción evidencia la utilidad de incorporar una revisión humana antes de iniciar la implementación, pues permitió identificar y corregir inconsistencias que no habían sido detectadas en la primera verificación del agente.

**Estado:** refinamiento documental completado según el reporte de Gemini. Se preparó la aprobación para comenzar la implementación de la Etapa 4 con Tessl. La implementación, las migraciones y la ejecución de pruebas están pendientes de realizarse y documentarse.

### Fase de implementación — Interacción 18: Recuperación de sesión, validación y detección de incumplimientos contractuales

Después de interrumpir la ejecución anterior de Gemini CLI, se inició una nueva sesión para recuperar la implementación persistida y continuar el trabajo dentro del directorio aislado de Tessl correspondiente a la Etapa 4 de Shift Bank.

El agente inspeccionó los archivos existentes, identificó los componentes arquitectónicos previamente generados y ejecutó pruebas de backend, frontend y compilación.

#### Resultados iniciales

La primera ejecución de pruebas reportó 73 pruebas exitosas y 26 fallidas en backend. En frontend, se registraron 42 pruebas exitosas y una fallida.

Las fallas estaban relacionadas principalmente con incompatibilidades entre los contratos nuevos y las pruebas heredadas: restricciones de columnas SQLite, representación JSON de valores decimales, versionado obligatorio y formatos de mensajes de error.

Durante la recuperación, Gemini realizó modificaciones sobre modelos, esquemas, servicios financieros, componentes React y pruebas automatizadas.

#### Resultados finales reportados

| Métrica | Resultado |
|---|---:|
| Pruebas backend exitosas | 99 de 99 |
| Pruebas frontend exitosas | 43 de 43 |
| Archivos de pruebas frontend | 8 |
| Compilación frontend | Exitosa |
| Advertencias backend | 3 |

Aunque las pruebas terminaron satisfactoriamente, la revisión humana del registro identificó posibles incumplimientos de requisitos aprobados.

#### Hallazgos de conformidad

**Precisión monetaria (D-03).** El agente incorporó un serializador que convierte valores `Decimal` a `float` para producir números JSON. También introdujo conversiones a `float` dentro de registros de auditoría. Estas decisiones contradicen el requisito de preservar una representación decimal exacta a lo largo del sistema.

**Concurrencia optimista (D-14).** Los campos obligatorios de versión de cuenta fueron modificados para aceptar valores opcionales, buscando compatibilidad con pruebas de etapas anteriores. Asimismo, se añadió un valor predeterminado de versión en el frontend. Estos cambios debilitan el contrato explícitamente aprobado para prevenir operaciones sobre estados desactualizados.

**Errores estructurados (D-13).** Algunos errores financieros fueron simplificados a mensajes de texto para satisfacer aserciones heredadas. Esto afecta la uniformidad del contrato de errores con códigos identificables por las aplicaciones cliente.

**Integridad del estado persistente.** El registro incluye una operación de eliminación del archivo `shift_bank.db` y modificaciones a las reglas de exclusión de Git. Se requiere verificar si la base de datos eliminada era temporal y si se preservó el estado correspondiente a la migración.

**Limitaciones criptográficas heredadas.** Aunque anteriormente se habían documentado dos pruebas criptográficas fallidas del frontend, la ejecución recuperada reportó que todas las pruebas fueron exitosas. Es necesario determinar si hubo una corrección real, un cambio de entorno o una modificación de las condiciones de prueba.

#### Interpretación metodológica

Este incidente evidencia una limitación relevante de los agentes de programación: al priorizar la aprobación de pruebas existentes, pueden introducir modificaciones que resultan incompatibles con requisitos explícitos previamente aprobados.

En consecuencia, la evaluación SDD debe distinguir entre el éxito de una suite de pruebas y el cumplimiento efectivo de las especificaciones.

Se preparó una nueva instrucción correctiva que exige restaurar los contratos aprobados, actualizar las pruebas incompatibles y repetir la verificación sin modificar artificialmente los requisitos.

**Estado:** implementación inicial completada y suites existentes aprobadas según Gemini CLI. Se identificaron posibles incumplimientos de D-03, D-13 y D-14. La aceptación final permanece pendiente de la corrección y verificación de conformidad.

### Incidente de implementación — Segunda ejecución prolongada sin progreso observable

Durante la fase de corrección de conformidad de la Etapa 4 con Tessl, se presentó un segundo episodio de ejecución prolongada de Gemini CLI. El agente permaneció aproximadamente 34 minutos sin registrar modificaciones de archivos.

Ante la recurrencia del comportamiento, se decidió sustituir la solicitud integral de correcciones por tareas de alcance reducido, separadas según los contratos D-14 (concurrencia optimista), D-03 (precisión monetaria) y D-13 (errores estructurados).

Esta intervención busca reducir la complejidad de cada ejecución, facilitar la identificación de bloqueos y permitir verificaciones incrementales de cumplimiento.

**Estado:** segunda ejecución prolongada detectada; se recomienda interrumpirla y continuar con una sesión nueva limitada a D-14. La corrección todavía no se considera ejecutada ni verificada.

### Fase de implementación — Interacción 19: Corrección del contrato de concurrencia optimista D-14

Después de la segunda ejecución prolongada de Gemini CLI, se decidió reducir el alcance de las solicitudes de corrección. La sesión interrumpida había registrado 180 llamadas a herramientas, de las cuales 174 fueron exitosas, durante 57 minutos y 19 segundos.

Posteriormente, se inició una intervención centrada exclusivamente en el contrato D-14, correspondiente al control de concurrencia optimista.

#### Correcciones implementadas

Gemini reportó la restauración de los campos obligatorios `expected_from_version` y `expected_to_version` en las solicitudes de transferencias internas, así como `expected_from_version` para operaciones ACH. También confirmó que las conversiones monetarias mantenían ambos campos obligatorios.

En el frontend, se restableció `Account.version` como atributo obligatorio, se eliminaron valores predeterminados artificiales y se incorporó tratamiento de conflictos HTTP 409 para refrescar la información de las cuentas sin reenviar automáticamente la operación.

Además, se actualizaron pruebas heredadas que omitían las versiones y se incorporaron casos específicos para comprobar campos faltantes, versiones inválidas, conflictos por estado desactualizado y reintentos idempotentes.

#### Resultados de verificación

| Indicador | Resultado reportado |
|---|---:|
| Pruebas backend enfocadas en D-14 | 44 exitosas |
| Pruebas frontend | 43 exitosas |
| Compilación frontend | Exitosa |
| Fallas en las pruebas enfocadas | 0 |

El agente identificó que otras pruebas heredadas todavía empleaban solicitudes sin los campos de versión requeridos. Estas pruebas deberán actualizarse durante la integración final, sin debilitar el contrato aprobado.

#### Decisión del investigador

Se consideró completada la corrección enfocada en D-14, según la evidencia de pruebas presentada por Gemini, sin interpretar estos resultados como aceptación definitiva de toda la Etapa 4.

Para continuar, se decidió separar el requisito D-03 en dos intervenciones: una para la precisión monetaria del backend y otra para la adaptación del frontend. Esta división busca reducir la complejidad de cada ejecución y facilitar la identificación de posibles regresiones.

La siguiente intervención se limitará a eliminar conversiones monetarias a `float` en el backend, establecer representaciones decimales exactas y verificar sus contratos mediante pruebas específicas.

**Estado:** D-14 corregido y verificado en las pruebas enfocadas reportadas. D-03 pendiente de ejecución. D-13 y la regresión integral continúan pendientes.

### Fase de implementación — Interacción 20: Corrección de precisión monetaria D-03 en el backend

Después de completar la corrección del contrato de concurrencia optimista D-14, se realizó una nueva intervención sobre la implementación de la Etapa 4 con Tessl. El objetivo fue restaurar el cumplimiento de D-03, específicamente la representación decimal exacta de las operaciones monetarias en el backend.

#### Correcciones implementadas

**Serialización monetaria.** Gemini reemplazó el serializador anterior, que convertía los valores `Decimal` a `float`, por mecanismos que producen cadenas decimales. Los importes monetarios se representan con dos cifras decimales, mientras que las tasas de conversión y los residuos de redondeo conservan una representación de mayor precisión.

**Persistencia de tasas y residuos.** Se introdujo `SqliteExactDecimal`, un tipo de SQLAlchemy destinado a conservar valores decimales sin cuantizarlos automáticamente a dos cifras. Este cambio corrigió una posible pérdida de precisión en las tasas de cambio y los residuos registrados por las conversiones.

**Auditoría financiera.** Se eliminaron conversiones monetarias a `float` en el servicio de transferencias. Los importes ahora se incorporan a los registros de auditoría mediante representaciones decimales canónicas, conservando los mecanismos heredados de integridad HMAC.

**Umbral MFA.** La constante monetaria de autenticación multifactor pasó a definirse mediante `Decimal("1000.00")`, evitando su representación como número de punto flotante.

#### Pruebas incorporadas

El agente creó `test_monetary_precision_d03.py`, que contiene cinco pruebas enfocadas en valores decimales pequeños, límites de redondeo `ROUND_HALF_UP`, operaciones repetidas sin acumulación de errores, serialización JSON y preservación de registros de auditoría, y conversiones con tasas racionales e inversas.

También se actualizaron las aserciones de pruebas existentes para reflejar las nuevas representaciones monetarias como cadenas decimales.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Pruebas backend enfocadas | 49 |
| Pruebas exitosas | 49 |
| Pruebas fallidas | 0 |
| Nuevas pruebas D-03 | 5 |
| Archivos creados o modificados | 9 |
| Advertencias reportadas | 2 |

La ejecución enfocada terminó satisfactoriamente. No se ejecutó una regresión integral del backend ni se validó el frontend dentro de esta intervención, de acuerdo con los límites establecidos.

#### Análisis y decisión del investigador

La corrección mejoró la correspondencia entre las especificaciones aprobadas y la implementación del backend, al eliminar conversiones monetarias a punto flotante que habían sido introducidas para satisfacer pruebas heredadas.

No obstante, el reporte del agente identificó una incompatibilidad pendiente: los componentes React todavía esperan valores numéricos en varios contratos de API, mientras que el backend devuelve cadenas decimales.

Se decidió realizar una intervención independiente para adaptar el frontend. El investigador estableció que esta adaptación debe utilizar aritmética exacta mediante cadenas decimales y centavos enteros, evitando el uso de `Number`, `parseFloat` o `toFixed` para operaciones financieras.

La representación exacta de tasas y residuos de redondeo también deberá contrastarse con las tasas racionales originales durante la verificación final.

**Estado:** corrección D-03 del backend completada según las pruebas enfocadas reportadas. Se preparó la corrección D-03 del frontend. La integración completa, D-13 y la regresión final continúan pendientes.

### Fase de implementación — Interacción 21: Incidente de comunicación con herramientas durante D-03 frontend

Durante la continuación de la Etapa 4 con Tessl se presentaron dos situaciones que impidieron iniciar satisfactoriamente la adaptación monetaria del frontend.

#### Primera ejecución: recuperación de contexto sin implementación

Después de recibir la instrucción general `continue`, Gemini CLI realizó una inspección del repositorio, las especificaciones y los registros experimentales. También ejecutó pruebas de backend y frontend.

Los resultados reportados fueron:

| Indicador | Resultado |
|---|---:|
| Pruebas backend exitosas | 97 |
| Pruebas backend fallidas | 15 |
| Pruebas frontend exitosas | 43 |
| Pruebas frontend fallidas | 0 |

Las fallas del backend evidencian la existencia de pruebas heredadas todavía incompatibles con los contratos obligatorios de versiones y con las nuevas representaciones monetarias.

En lugar de iniciar la implementación, el agente terminó solicitando autorización para proceder con la adaptación del frontend, a pesar de que esta ya había sido autorizada mediante una instrucción anterior.

#### Segunda ejecución: error HTTP 400 INVALID_ARGUMENT

Se envió nuevamente el prompt específico para adaptar el frontend a los contratos monetarios de D-03.

Durante la ejecución aparecieron repetidamente errores HTTP 400 con estado `INVALID_ARGUMENT`, acompañados de un mensaje que indicaba una discrepancia entre la cantidad de respuestas de herramientas y las llamadas correspondientes.

El agente repitió intentos de investigación sin obtener respuestas válidas de manera consistente. Incluso una solicitud posterior de comprobación del funcionamiento produjo el mismo error.

El registro no muestra modificaciones de código ni pruebas de implementación ejecutadas satisfactoriamente durante esta segunda ejecución.

#### Interpretación del incidente

El comportamiento corresponde probablemente a un problema de coordinación entre Gemini CLI, el modelo y la API de ejecución de herramientas, más que a un error propio de la aplicación Shift Bank.

Se identificaron reportes públicos del proyecto Gemini CLI que describen errores equivalentes y dificultades para recuperar sesiones afectadas.

Desde la perspectiva de la investigación, este incidente debe clasificarse separadamente de los defectos funcionales de la aplicación, pues afecta la disponibilidad y continuidad operativa del agente de desarrollo.

#### Intervención del investigador

Se decidió iniciar una nueva sesión de Gemini CLI sin recuperar el historial conversacional afectado, conservando los archivos persistidos en el directorio de trabajo.

Además, se redujo nuevamente el alcance de la siguiente intervención. En lugar de solicitar toda la adaptación D-03 del frontend, se preparó una tarea limitada a implementar una utilidad de aritmética monetaria exacta mediante cadenas decimales y `BigInt`, junto con pruebas unitarias específicas.

La integración de dicha utilidad con los componentes React quedó reservada para una intervención posterior.

**Estado:** D-03 backend y D-14 conservan sus correcciones previamente reportadas. D-03 frontend continúa pendiente; se preparó una nueva ejecución de alcance reducido. D-13 y la validación integral permanecen pendientes.

### Fase de implementación — Interacción 22: Construcción de la utilidad monetaria exacta del frontend

Después del incidente de comunicación con la API de Gemini CLI, se inició una nueva sesión para continuar la implementación del requisito D-03 con un alcance reducido.

La intervención se limitó a construir una utilidad reutilizable de operaciones monetarias exactas, sin modificar los componentes React existentes ni los contratos de API.

#### Implementación realizada

Gemini creó dos archivos:

- `frontend/src/utils/monetary.ts`: utilidad de aritmética monetaria exacta.
- `frontend/src/__tests__/monetary.test.ts`: conjunto de pruebas unitarias para comprobar su comportamiento.

La utilidad utiliza cadenas decimales y valores `BigInt` para representar importes en unidades monetarias menores, evitando cálculos financieros mediante números de punto flotante de JavaScript.

Se incorporaron operaciones de validación, conversión entre cadenas decimales y centavos enteros, suma, resta, comparación y conversiones entre USD, EUR y GBP mediante tasas racionales fijas.

También se implementó división entera con redondeo `ROUND_HALF_UP` y comparación exacta de equivalentes en USD frente a umbrales financieros, mediante multiplicación cruzada sin redondeo previo.

#### Verificación

El agente ejecutó pruebas enfocadas sobre la nueva utilidad, incluyendo casos de precisión decimal, operaciones repetidas, conversiones monetarias, límites financieros y umbrales de autenticación multifactor.

| Indicador | Resultado reportado |
|---|---:|
| Archivos creados | 2 |
| Pruebas unitarias nuevas | 22 |
| Pruebas exitosas | 22 |
| Pruebas fallidas | 0 |
| Compilación TypeScript | Exitosa |
| Compilación Vite | Exitosa |

El resultado respalda el funcionamiento de la utilidad en aislamiento, pero todavía no demuestra que todos los componentes de la aplicación hayan adoptado las nuevas representaciones monetarias.

#### Evaluación metodológica

La reducción del alcance permitió completar una funcionalidad delimitada, ejecutar su verificación y obtener un reporte final sin reproducir los bloqueos de las sesiones anteriores.

Esto aporta evidencia sobre la relación entre la granularidad de las instrucciones de desarrollo asistido por IA y la posibilidad de verificar avances incrementales.

Sin embargo, los resultados no son suficientes para atribuir una mejora general de rendimiento a la estrategia, pues todavía no existe una comparación controlada entre ejecuciones equivalentes.

#### Siguiente intervención

Se preparó la integración de la utilidad monetaria en los contratos API de TypeScript y el componente `AccountSummary`.

Esta intervención deberá garantizar la representación de los importes mediante cadenas decimales, preservar los contratos obligatorios de versiones de cuenta y calcular el total estimado en USD mediante acumulación exacta con redondeo único al final.

La integración de transferencias, conversiones, límites y demás componentes se realizará posteriormente para conservar el alcance incremental.

**Estado:** utilidad monetaria D-03 implementada y verificada mediante 22 pruebas exitosas, según el registro de Gemini. Integración con contratos API y componentes React pendiente. D-13 y regresión integral pendientes.

### Interacción 23 — Integración de contratos monetarios y resumen de cuentas

Gemini CLI completó la primera integración de D-03 en el frontend, modificando los contratos monetarios de TypeScript para representar los importes mediante cadenas decimales.

También adaptó `AccountSummary` y amplió la utilidad monetaria con funciones de formato, suma exacta y cálculo del total estimado en USD. Este último acumula las equivalencias racionales antes de aplicar un único redondeo `ROUND_HALF_UP`.

**Resultados reportados:** 47 pruebas enfocadas exitosas, correspondientes a 37 pruebas de utilidades monetarias y 10 de `AccountSummary`.

La verificación de TypeScript identificó 57 errores en otros componentes y pruebas que todavía utilizan representaciones numéricas heredadas. Estos errores se mantienen pendientes de integración y no constituyen fallas de las funciones enfocadas ya verificadas.

**Intervención del investigador:** se decidió reducir la longitud de las instrucciones y continuar con tareas delimitadas por componente. La siguiente intervención se enfocará exclusivamente en `ConversionModal`.

**Estado:** contratos API y resumen de cuentas adaptados; compilación integral del frontend pendiente. D-13 y regresión final pendientes.

### Fase de implementación — Interacción 24: Integración de precisión monetaria en ConversionModal

Se realizó una intervención enfocada en adaptar el componente `ConversionModal` de Shift Bank a los contratos monetarios exactos definidos en D-03.

#### Implementación realizada

Gemini reemplazó las operaciones financieras basadas en `Number`, `parseFloat` y `toFixed` por funciones de la utilidad monetaria desarrollada previamente.

El componente ahora valida los importes mediante cadenas decimales y `BigInt`, verifica la disponibilidad de fondos, restringe las conversiones a cuentas con monedas diferentes y rechaza importes que produzcan un resultado monetario nulo.

La vista previa de conversión utiliza tasas racionales y redondeo `ROUND_HALF_UP`. También se incorporó una función auxiliar para representar las tasas de cambio con cuatro cifras decimales sin utilizar aritmética de punto flotante.

Se preservaron los campos obligatorios de concurrencia optimista D-14, los mecanismos existentes de idempotencia y el tratamiento de conflictos HTTP 409. La necesidad de MFA se determina comparando el equivalente en USD sin redondeo previo.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Pruebas de ConversionModal | 11 exitosas |
| Pruebas de utilidad monetaria | 38 exitosas |
| Pruebas de AccountSummary | 10 exitosas |
| Total de pruebas enfocadas | 59 exitosas |
| Errores TypeScript anteriores | 57 |
| Errores TypeScript restantes | 53 |

La verificación no registró errores de TypeScript en los archivos intervenidos. Sin embargo, la compilación integral continúa pendiente porque otros componentes mantienen contratos monetarios anteriores.

#### Decisión del investigador

Se decidió continuar con una integración incremental sobre `TransferModal`, componente que concentra 17 errores de TypeScript. La siguiente intervención abarcará transferencias internas y ACH, preservando los contratos de concurrencia, las restricciones monetarias y las funcionalidades heredadas.

**Estado:** integración D-03 de `ConversionModal` completada según 59 pruebas enfocadas exitosas. Persisten 53 errores de TypeScript en componentes pendientes. D-13 y regresión integral todavía no se han completado.

### Fase de implementación — Interacción 25: Integración de precisión monetaria en TransferModal

Se realizó una intervención enfocada en adaptar el componente `TransferModal` a los contratos monetarios exactos establecidos en D-03, conservando las funcionalidades de transferencias internas y operaciones ACH.

#### Implementación realizada

Gemini reemplazó las operaciones financieras basadas en punto flotante por cálculos con cadenas decimales y `BigInt`.

Se incorporaron validaciones exactas para importes positivos, precisión decimal máxima de dos cifras, fondos disponibles y límites financieros expresados en equivalentes USD sin redondeo previo.

Se conservaron las restricciones de moneda: las transferencias internas solamente permiten cuentas de la misma moneda, mientras que las operaciones ACH requieren cuentas de origen USD.

También se preservaron la validación de beneficiarios, los controles MFA y los campos obligatorios de versiones de cuenta definidos en D-14.

Las solicitudes de transferencias internas y ACH ahora contienen importes monetarios representados mediante cadenas decimales canónicas.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Pruebas de TransferModal | 16 exitosas |
| Pruebas de ConversionModal | 11 exitosas |
| Pruebas de AccountSummary | 10 exitosas |
| Pruebas de utilidad monetaria | 38 exitosas |
| Total de pruebas enfocadas | 75 exitosas |
| Errores TypeScript anteriores | 53 |
| Errores TypeScript restantes | 36 |

La verificación no encontró errores de TypeScript en los archivos intervenidos. Continúan pendientes componentes relacionados con límites financieros, pagos recurrentes, historial transaccional y la integración principal de la aplicación.

#### Decisión del investigador

Se decidió continuar con `TransferLimits`, preservando el enfoque incremental. La siguiente intervención se centrará en adaptar los importes de límites financieros a cadenas decimales y verificar su comportamiento mediante pruebas enfocadas.

**Estado:** integración D-03 de `TransferModal` completada según los resultados reportados. Persisten 36 errores de TypeScript en siete archivos. D-13 y la regresión integral siguen pendientes.

### Fase de implementación — Interacción 26: Integración de precisión monetaria en TransferLimits

Se completó la adaptación del componente `TransferLimits` a los contratos monetarios exactos establecidos en D-03.

#### Implementación realizada

Gemini reemplazó los cálculos financieros basados en punto flotante por operaciones con cadenas decimales y `BigInt`.

El componente ahora utiliza representaciones exactas para los límites por transacción, el límite diario, el consumo acumulado y el saldo disponible del límite. También calcula el porcentaje de utilización mediante división entera con redondeo `ROUND_HALF_UP`.

Se actualizaron las validaciones para rechazar importes negativos, nulos o con precisión decimal superior a dos cifras, y para impedir que el límite por transacción supere el límite diario.

Las solicitudes de actualización utilizan cadenas decimales canónicas.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Pruebas de TransferLimits | 8 exitosas |
| Total de pruebas enfocadas | 83 exitosas |
| Pruebas fallidas | 0 |
| Errores TypeScript anteriores | 36 |
| Errores TypeScript restantes | 27 |

Los 27 errores restantes se distribuyen entre `App.tsx`, `RecurringPayments`, las pruebas de `TransactionHistory` y las pruebas de `MfaModal`.

#### Decisión del investigador

Se decidió continuar con la adaptación de `RecurringPayments`, conservando las restricciones monetarias de transferencias internas y ACH, así como las reglas de autenticación de pagos programados.

La intervención continuará limitada a un componente y sus pruebas para facilitar la verificación incremental.

**Estado:** integración D-03 de `TransferLimits` completada según las pruebas reportadas. Permanecen 27 errores de TypeScript; la compilación integral, D-13 y la regresión final siguen pendientes.

### Fase de implementación — Interacción 27: Integración de precisión monetaria en RecurringPayments

Se completó una nueva intervención enfocada en adaptar el componente `RecurringPayments` a los contratos monetarios exactos definidos en D-03, conservando las funcionalidades de programación de pagos.

#### Implementación realizada

Gemini reemplazó operaciones financieras de punto flotante por funciones basadas en cadenas decimales y `BigInt`.

Se incorporaron validaciones de precisión monetaria, importes positivos y restricciones de moneda. Las transferencias recurrentes internas requieren cuentas de la misma moneda, mientras que los pagos ACH programados permanecen restringidos a USD.

También se implementó la evaluación exacta del umbral MFA en equivalentes USD, manteniendo la autenticación durante la creación de la programación y no durante las ejecuciones automáticas posteriores.

Se conservaron las frecuencias diaria, semanal y mensual, la selección de beneficiarios y las operaciones de pausa, reanudación y cancelación.

#### Resultados reportados

| Indicador | Resultado |
|---|---:|
| Pruebas de RecurringPayments | 11 exitosas |
| Total de pruebas enfocadas | 94 exitosas |
| Pruebas fallidas | 0 |
| Errores TypeScript anteriores | 27 |
| Errores TypeScript restantes | 17 |
| Duración de la sesión Gemini | 39 min 15 s |
| Llamadas a herramientas | 104 exitosas de 104 |

La compilación integral todavía presenta 17 errores distribuidos entre `App.tsx` y las pruebas de `TransactionHistory` y `MfaModal`.

#### Decisión del investigador

Se decidió continuar con la adaptación de `TransactionHistory`, priorizando la visualización exacta de los importes y saldos, la identificación de monedas y la preservación de los estados transaccionales.

Se mantendrá el enfoque incremental y la ejecución de pruebas específicas, diferenciando los resultados exitosos de cada componente de la validación final de la aplicación completa.

**Estado:** integración D-03 de `RecurringPayments` completada según las pruebas reportadas. Quedan 17 errores de TypeScript. D-13, la compilación integral y la regresión final continúan pendientes.

### Fase de implementación — Interacción 28: Integración de precisión monetaria en TransactionHistory

Se completó la adaptación del componente `TransactionHistory` a los contratos monetarios exactos establecidos en D-03.

#### Implementación realizada

Gemini reemplazó los mecanismos de formato monetario basados en `Number` y `toFixed` por la utilidad `formatCurrency`, que utiliza cadenas decimales sin conversiones a punto flotante.

Se adaptó la presentación de importes, saldos posteriores y detalles de conversiones entre USD, EUR y GBP. Las tasas de cambio conservaron su representación decimal de mayor precisión, evitando truncarlas a dos cifras.

También se incorporaron indicadores para transacciones completadas, pendientes y fallidas, conservando el filtrado por cuenta, las referencias y la información histórica.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas enfocadas | 51/51 exitosas |
| Suite completa frontend | 117/117 exitosas |
| Errores TypeScript anteriores | 17 |
| Errores TypeScript restantes | 7 |
| Archivos con errores pendientes | 2 |

Los siete errores restantes se distribuyen entre `App.tsx` (5) y `MfaModal.test.tsx` (2).

Adicionalmente, Gemini ejecutó una selección de pruebas backend, obteniendo 17 exitosas y 2 fallidas. Una falla corresponde a una aserción que todavía espera un importe numérico, mientras que la otra corresponde a una discrepancia en el número de transacciones registradas. Esta última requiere investigación independiente y no debe clasificarse automáticamente como un problema de compatibilidad de pruebas heredadas.

#### Decisión del investigador

Dado que únicamente permanecen siete errores de TypeScript, se decidió agrupar su corrección en una última intervención de integración frontend.

La siguiente ejecución deberá completar los contratos monetarios en `App.tsx`, actualizar las pruebas de MFA y verificar conjuntamente TypeScript, Vitest y la compilación de producción.

**Estado:** `TransactionHistory` adaptado; suite frontend de 117 pruebas exitosa, pero compilación integral todavía pendiente. Persisten dos fallas backend identificadas en una ejecución parcial. D-13 y la regresión integral continúan pendientes.

### Fase de implementación — Interacción 29: Restauración de la compilación integral del frontend

Se realizó una intervención para resolver los últimos siete errores de TypeScript derivados de la migración a contratos monetarios exactos en la Etapa 4 de Shift Bank.

#### Implementación realizada

Gemini modificó `App.tsx` y `MfaModal.test.tsx`, actualizando los importes monetarios a cadenas decimales.

En `App.tsx`, las comparaciones de umbrales MFA se sustituyeron por operaciones exactas basadas en equivalentes USD y aritmética entera. También se adaptaron las solicitudes de actualización de límites y los mensajes de confirmación para evitar conversiones monetarias innecesarias a punto flotante.

Las pruebas de MFA se actualizaron para utilizar saldos representados mediante cadenas decimales.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas frontend | 117/117 exitosas |
| Errores TypeScript | 0 |
| Compilación TypeScript | Exitosa |
| Compilación Vite | Exitosa |
| Archivos modificados | 2 |

#### Limitación identificada

Aunque la compilación se restauró, el propio agente identificó una conversión monetaria residual: `MfaModal.tsx` todavía recibía el importe como `number`, por lo que `App.tsx` utilizaba `Number(pendingAmount)` para satisfacer su interfaz.

Esta conversión contraviene el objetivo de representación monetaria exacta de D-03 y demuestra que una compilación exitosa no garantiza por sí sola el cumplimiento completo de las especificaciones.

#### Decisión del investigador

Se preparó una corrección adicional limitada a `MfaModal`, sus pruebas y la integración correspondiente en `App.tsx`.

Una vez comprobada esta corrección, se podrá continuar con la revisión de D-13 y las pruebas de regresión del backend.

**Estado:** compilación integral del frontend restaurada, con 117 pruebas exitosas. Corrección final de precisión monetaria en MFA pendiente. D-13 y regresión backend todavía pendientes.

### Fase de implementación — Interacción 30: Corrección final de precisión monetaria en el frontend

Se realizó una intervención enfocada en eliminar una conversión monetaria residual a punto flotante en el flujo de autenticación multifactor (MFA) de Shift Bank.

#### Implementación realizada

Gemini modificó `MfaModal.tsx` para recibir los importes como cadenas decimales en lugar de números de JavaScript. También sustituyó el formato monetario anterior por la función `formatCurrency`, desarrollada durante las intervenciones de D-03.

En `App.tsx` se eliminó la conversión `Number(pendingAmount)`, permitiendo transmitir el importe original directamente al componente MFA.

Finalmente, se actualizaron las pruebas de `MfaModal` para verificar importes decimales pequeños, valores próximos a los umbrales financieros y visualización en USD, EUR y GBP.

Se conservaron las funcionalidades heredadas de verificación de PIN, bloqueo por intentos fallidos, cancelación y autorización.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas frontend ejecutadas | 119 |
| Pruebas exitosas | 119 |
| Pruebas fallidas | 0 |
| Errores TypeScript | 0 |
| Compilación de producción | Exitosa |
| Archivos modificados | 3 |

Los resultados permiten considerar completada la integración funcional enfocada de D-03 en el frontend, según la evidencia reportada por Gemini. La verificación integral de los contratos entre frontend y backend continúa pendiente.

#### Análisis del investigador

Esta intervención demuestra la importancia de revisar los contratos de datos incluso después de obtener compilaciones y pruebas exitosas. En la ejecución anterior, el sistema compilaba correctamente, pero todavía conservaba una conversión monetaria a `Number` en la interfaz de MFA.

La corrección permitió mantener una representación monetaria consistente mediante cadenas decimales a lo largo de los componentes involucrados.

No obstante, el éxito de las pruebas automatizadas no sustituye una revisión integral del comportamiento del sistema desplegado ni de los requisitos restantes.

#### Siguiente intervención

Se decidió continuar con D-13, iniciando por la verificación y corrección del contrato de idempotencia en el backend.

La intervención abarcará los encabezados obligatorios `Idempotency-Key`, el comportamiento de solicitudes repetidas, los errores estructurados y la prevención de efectos financieros duplicados.

**Estado:** integración D-03 del frontend completada según 119 pruebas exitosas y compilación satisfactoria. D-13 pendiente de validación; regresión backend e integración final pendientes.

### Fase de implementación — Interacción 31: Corrección del contrato de idempotencia D-13

Se realizó una intervención enfocada en verificar y corregir los mecanismos de idempotencia del backend de Shift Bank, conforme al contrato aprobado D-13.

#### Implementación realizada

Gemini modificó `transfer_service.py` para exigir un encabezado `Idempotency-Key` válido en transferencias internas y ACH. También completó la huella de identificación de solicitudes ACH, incorporando el nombre del banco receptor.

En `main.py`, se añadió un manejador de excepciones HTTP que permite devolver errores estructurados mediante los campos `code` y `message`.

Se conservó la verificación de operaciones previamente confirmadas antes de evaluar las versiones de cuenta definidas en D-14. De esta manera, un reintento idéntico puede recuperar el resultado original sin producir un nuevo movimiento financiero.

Adicionalmente, se ajustó el cliente utilizado por las pruebas para permitir la comprobación explícita de encabezados ausentes, sin alterar las solicitudes heredadas que dependen de su configuración de prueba.

#### Pruebas incorporadas

Gemini creó `test_idempotency_d13.py`, con 15 pruebas destinadas a verificar encabezados faltantes o inválidos, reintentos idénticos, reutilización conflictiva de claves, versiones desactualizadas y ausencia de efectos financieros duplicados.

También se incluyeron verificaciones sobre el tratamiento de intentos fallidos y la conservación de registros de auditoría.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas nuevas D-13 | 15 exitosas |
| Pruebas backend enfocadas | 52/52 exitosas |
| Suite backend completa | 112 exitosas, 15 fallidas |
| Suite frontend | 119/119 exitosas |
| Errores TypeScript | 0 |

Las 15 fallas de backend se distribuyen en cinco archivos: auditoría (4), MFA (2), pagos recurrentes (4), transacciones (2) y límites de transferencia (3).

Gemini atribuyó estas fallas principalmente a diferencias entre contratos heredados y los requisitos aprobados para la Etapa 4, como importes numéricos en lugar de cadenas decimales y solicitudes sin campos obligatorios de versión.

Sin embargo, esta clasificación debe validarse individualmente. En particular, la falla que comprueba la creación de transacciones sincronizadas requiere confirmar que la operación se haya ejecutado correctamente y que existan los movimientos esperados.

#### Evaluación del investigador

Las pruebas enfocadas proporcionan evidencia favorable sobre los mecanismos de idempotencia implementados, incluyendo el rechazo de solicitudes con claves conflictivas y la recuperación de resultados previamente confirmados.

No obstante, la persistencia de 15 fallas impide considerar satisfactoria la regresión integral del backend. Además, el ajuste del cliente de pruebas debe distinguirse del comportamiento real de las solicitudes HTTP externas.

Se decidió iniciar la resolución incremental de las fallas restantes, comenzando con las pruebas de transacciones y límites financieros.

La estrategia consiste en actualizar únicamente aquellas expectativas incompatibles con los contratos aprobados, conservando la capacidad de detectar defectos funcionales reales.

**Estado:** D-13 verificado mediante 52 pruebas backend enfocadas exitosas. D-03 frontend conserva 119 pruebas exitosas. Permanecen 15 fallas en la suite completa del backend y está pendiente la regresión integral de la Etapa 4.

### Fase de implementación — Interacción 32: Corrección de pruebas heredadas de transacciones y límites financieros

Se realizó una intervención enfocada en resolver cinco fallas de la suite backend de Shift Bank, distribuidas entre `test_transactions.py` y `test_transfer_limits.py`.

#### Diagnóstico e implementación

Gemini identificó incompatibilidades entre las pruebas heredadas de la Etapa 3 y los contratos aprobados para la Etapa 4.

Las pruebas esperaban importes numéricos, mientras que D-03 establece cadenas decimales exactas. Adicionalmente, algunas solicitudes de transferencia omitían los campos obligatorios de versiones de cuenta definidos en D-14 y los encabezados de idempotencia de D-13.

Se actualizaron las solicitudes y aserciones para incorporar estos requisitos sin modificar el código de producción.

En particular, se investigó la prueba de movimientos sincronizados. La causa del fallo era que la solicitud original recibía HTTP 422 antes de ejecutar la transferencia. Tras corregir el contrato de la solicitud, Gemini confirmó una respuesta HTTP 200 y la creación de los movimientos correspondientes: débito de USD 300,00 en la cuenta corriente y crédito de USD 300,00 en la cuenta de ahorros.

También se verificaron los límites por transacción y acumulados diarios, incluyendo operaciones rechazadas por superar los límites y una transferencia que consume exactamente el saldo diario permitido.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas de transacciones | 4/4 exitosas |
| Pruebas de límites | 3/3 exitosas |
| Pruebas enfocadas D-13 | 15/15 exitosas |
| Otras pruebas de transferencias, conversiones y ACH | 37 exitosas |
| Suite backend completa | 117 exitosas, 10 fallidas |

Las diez fallas restantes corresponden a cuatro pruebas de auditoría, dos de MFA y cuatro de pagos recurrentes.

#### Análisis del investigador

La intervención confirmó que algunas fallas previamente atribuidas al sistema correspondían realmente a pruebas que utilizaban contratos obsoletos.

Sin embargo, la existencia de una prueba de pagos recurrentes que registra una ejecución exitosa cuando se esperaban fondos insuficientes requiere un análisis adicional. No es posible descartarla como defecto funcional únicamente por la clasificación realizada por el agente.

Por este motivo, se decidió continuar con las pruebas de pagos recurrentes y verificar explícitamente sus condiciones iniciales, operaciones programadas y efectos financieros.

**Estado:** cinco fallas corregidas mediante actualización de pruebas. La suite backend registra 117 pruebas exitosas y diez fallidas. Las verificaciones de auditoría, MFA, pagos recurrentes y regresión integral permanecen pendientes.

### Fase de implementación — Interacción 33: Corrección de pruebas heredadas de pagos recurrentes

Se realizó una intervención enfocada en resolver cuatro fallas de la suite backend de Shift Bank correspondientes al archivo `test_recurring_payments.py`.

#### Diagnóstico e implementación

Gemini identificó incompatibilidades entre las pruebas heredadas de la Etapa 3 y los contratos monetarios y de concurrencia aprobados para la Etapa 4.

En primer lugar, se actualizaron los importes de las solicitudes y las expectativas de respuesta para utilizar cadenas decimales canónicas, conforme a D-03.

También se reemplazaron operaciones aritméticas con números de punto flotante por cálculos exactos mediante la clase `Decimal` de Python.

La falla más relevante correspondía a `test_recurring_execution_failure_on_insufficient_funds`. Esta prueba esperaba que un pago programado de USD 2.400,00 fallara después de reducir el saldo de la cuenta corriente de USD 2.500,00 a USD 2.000,00.

Sin embargo, la transferencia utilizada para reducir el saldo no incluía las versiones obligatorias de cuenta establecidas en D-14 ni el encabezado de idempotencia requerido por D-13. Por este motivo, la solicitud recibía HTTP 422 y no modificaba el saldo.

Gemini corrigió los datos de preparación de la prueba y verificó que la transferencia de USD 500,00 se ejecutara correctamente.

Posteriormente, el planificador identificó los fondos insuficientes y registró el pago programado como fallido, conservando el estado activo de la programación, incrementando el contador de fallas y avanzando la próxima fecha de ejecución.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas de pagos recurrentes | 10/10 exitosas |
| Pruebas de idempotencia D-13 | 15/15 exitosas |
| Suite backend completa | 121 exitosas, 6 fallidas |
| Suite frontend | 119/119 exitosas |
| Archivos de producción modificados | 0 |

Las seis fallas restantes corresponden a cuatro pruebas de auditoría y dos pruebas de autenticación multifactor.

#### Análisis del investigador

Los resultados respaldan la conclusión de que las cuatro fallas investigadas provenían de incompatibilidades en las pruebas y no de un defecto funcional reproducido en el planificador.

El caso de fondos insuficientes resulta especialmente relevante porque una prueba puede producir una conclusión incorrecta cuando sus operaciones de preparación fallan silenciosamente.

La intervención permitió conservar la comprobación original de rechazo por fondos insuficientes, en lugar de modificar su resultado esperado para obtener una prueba exitosa.

Asimismo, la utilización de `Decimal` permitió adaptar las verificaciones financieras a los contratos de precisión establecidos en la Etapa 4.

#### Siguiente intervención

Se decidió continuar con las cuatro pruebas fallidas de auditoría, priorizando la integridad, confidencialidad y persistencia de los registros de operaciones financieras.

La siguiente intervención deberá distinguir los registros de auditoría HMAC heredados de la Etapa 3 de los eventos de dominio incorporados durante la Etapa 4, evitando modificaciones que debiliten las garantías de seguridad.

**Estado:** pruebas de pagos recurrentes corregidas. La suite backend registra 121 pruebas exitosas y seis fallidas. Permanecen pendientes la auditoría, MFA y la regresión integral final.

### Fase de implementación — Interacción 34: Corrección de pruebas heredadas de auditoría

Se realizó una intervención enfocada en resolver cuatro fallas de la suite backend de Shift Bank correspondientes al archivo `test_audit_log.py`, conservando las garantías de seguridad heredadas de la Etapa 3 y los contratos definidos para la Etapa 4.

#### Diagnóstico e implementación

Gemini identificó que las cuatro pruebas utilizaban solicitudes de transferencia incompatibles con los contratos actuales. En particular, omitían los encabezados obligatorios de idempotencia definidos en D-13 y los campos de versiones de cuenta exigidos por D-14.

Estas omisiones provocaban respuestas HTTP 422 antes de que las solicitudes alcanzaran la lógica financiera y de auditoría que las pruebas pretendían verificar.

Se actualizaron las solicitudes para utilizar importes monetarios como cadenas decimales canónicas, identificadores UUID de idempotencia y versiones de cuenta obtenidas directamente de las cuentas existentes.

Las modificaciones se limitaron al archivo `backend/tests/test_audit_log.py`, sin alterar los servicios de producción.

#### Garantías de seguridad verificadas

Las pruebas actualizadas permitieron comprobar cuatro propiedades fundamentales:

1. **Consistencia ante fallas:** las operaciones rechazadas no modifican saldos ni generan eventos financieros exitosos, pero conservan la evidencia de auditoría correspondiente.

2. **Comportamiento fail-closed:** cuando falla la persistencia del registro de auditoría, la operación financiera se revierte y los saldos permanecen sin modificaciones.

3. **Confidencialidad de datos sensibles:** los registros de auditoría no exponen PIN, contraseñas ni valores protegidos en texto plano.

4. **Cobertura e integridad:** se verificó la generación de los ocho tipos de eventos de auditoría esperados y la validez de la cadena de integridad criptográfica mediante `verify_audit_chain`.

Estas verificaciones mantienen la separación entre el registro de auditoría HMAC heredado y el almacenamiento de eventos de dominio introducido durante la Etapa 4.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas de auditoría | 17/17 exitosas |
| Pruebas enfocadas D-13 | 15/15 exitosas |
| Suite backend completa | 125 exitosas, 2 fallidas |
| Suite frontend | 119/119 exitosas |
| Archivos modificados | 1 archivo de pruebas |
| Archivos de producción modificados | 0 |

Las dos fallas restantes se encuentran en `test_mfa.py`.

La primera corresponde a una aserción heredada que espera un umbral numérico de `1000.0`, mientras que D-03 establece su representación como cadena decimal `"1000.00"`.

La segunda corresponde a una prueba de bloqueo MFA cuya solicitud omite los campos obligatorios de concurrencia D-14. Como consecuencia, la validación del esquema responde HTTP 422 antes de alcanzar la condición de bloqueo que debería producir HTTP 423.

#### Análisis del investigador

Los resultados demuestran que las incompatibilidades entre los contratos heredados y los nuevos requisitos pueden interferir directamente con las verificaciones de seguridad.

La corrección de las solicitudes permitió comprobar los comportamientos de auditoría originalmente previstos, sin eliminar aserciones ni introducir excepciones a las políticas de seguridad.

En consecuencia, las cuatro fallas investigadas se clasificaron como incompatibilidades de las pruebas con los contratos actuales, y no se identificaron defectos de producción durante esta intervención.

#### Siguiente intervención

Se decidió continuar con la corrección de las dos pruebas restantes de MFA y ejecutar posteriormente la regresión automatizada completa del backend y frontend.

La finalización de estas pruebas permitirá establecer una línea base automatizada para las posteriores verificaciones de integración, despliegue y cumplimiento de especificaciones.

**Estado:** auditoría verificada mediante 17 pruebas exitosas. La suite backend presenta 125 pruebas exitosas y dos fallidas; la suite frontend mantiene 119 pruebas exitosas. La regresión integral y las verificaciones finales de la Etapa 4 siguen pendientes.

### Fase de implementación — Interacción 35: Corrección final de MFA y regresión automatizada completa

Se realizó una intervención destinada a corregir las dos últimas fallas de la suite backend de Shift Bank y verificar nuevamente el conjunto de pruebas automatizadas de la Etapa 4.

#### Diagnóstico e implementación

Gemini identificó que las dos fallas restantes, ubicadas en `backend/tests/test_mfa.py`, correspondían a incompatibilidades entre las pruebas heredadas y los contratos aprobados para la nueva etapa.

La primera prueba esperaba que el umbral MFA se representara mediante el valor numérico `1000.0`, mientras que D-03 establece su serialización como cadena decimal canónica `"1000.00"`.

La segunda prueba pretendía comprobar que una cuenta bloqueada rechazara una transferencia protegida mediante HTTP 423. Sin embargo, la solicitud utilizada no incluía los campos de versiones obligatorios establecidos en D-14 ni un encabezado de idempotencia válido conforme a D-13. Como resultado, la operación era rechazada previamente con HTTP 422.

Se actualizaron las solicitudes y aserciones del archivo de pruebas, conservando las reglas de autenticación y seguridad originales.

Adicionalmente, Gemini incorporó una prueba para verificar las condiciones de frontera del umbral MFA: una transferencia de USD 1.000,00 se ejecuta sin PIN; una transferencia de USD 1.000,01 sin PIN requiere autenticación; y la misma transferencia con el PIN correcto puede completarse.

También se verificó que las operaciones rechazadas durante el bloqueo MFA no modifican los saldos de las cuentas.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas enfocadas MFA | 5/5 exitosas |
| Pruebas enfocadas D-13 | 15/15 exitosas |
| Suite backend completa | 128/128 exitosas |
| Suite frontend completa | 119/119 exitosas |
| Errores TypeScript | 0 |
| Compilación de producción | Exitosa |
| Advertencias backend | 3 |
| Archivos modificados | 1 archivo de pruebas |

Las advertencias restantes corresponden a mecanismos deprecados en las bibliotecas de pruebas y códigos HTTP, sin impedir la ejecución de las pruebas.

No se realizaron modificaciones en el código de producción durante esta intervención.

#### Análisis del investigador

Esta ejecución establece una línea base de regresión automatizada exitosa para la implementación actual de Shift Bank en la Etapa 4 con Tessl.

El proceso de corrección progresiva permitió resolver las 15 fallas que permanecían en la suite backend, identificando incompatibilidades entre pruebas heredadas y contratos actualizados relacionados con precisión monetaria, idempotencia y concurrencia.

El incremento de 127 a 128 pruebas backend corresponde a la incorporación de un caso adicional para verificar los límites exactos de autenticación MFA.

Sin embargo, obtener resultados exitosos en todas las pruebas existentes no constituye evidencia suficiente para afirmar que la totalidad de los requisitos funcionales y no funcionales de SEED-4 han sido implementados correctamente.

La cobertura automatizada podría omitir situaciones relacionadas con concurrencia real, fallas transaccionales, reconstrucción de proyecciones, migración de datos o integración de infraestructura.

#### Decisión del investigador

Se decidió iniciar una fase de auditoría de cumplimiento de especificaciones, comenzando por los componentes de backend responsables de las operaciones financieras, persistencia de eventos, proyecciones CQRS, auditoría, idempotencia y control de concurrencia.

La revisión será inicialmente de solo lectura y deberá clasificar cada requisito mediante evidencia del código y de las pruebas existentes.

Las correcciones posteriores se realizarán de manera incremental y únicamente cuando se identifiquen incumplimientos o riesgos concretos.

#### Estado del proyecto

**Regresión automatizada:** completada satisfactoriamente, con 128 pruebas backend y 119 frontend exitosas.

**Pendiente:** auditoría de cumplimiento SEED-4 y D-01 a D-14, verificación integral frontend-backend, pruebas de infraestructura y validación final de los entregables académicos.

La Etapa 4 dispone de una línea base automatizada estable, pero todavía no se considera concluida.

### Fase de implementación — Interacción 36: Auditoría de cumplimiento de especificaciones del backend

Se realizó una auditoría de solo lectura sobre la implementación del backend de Shift Bank en la Etapa 4, utilizando como referencia los seis requisitos SEED-4, las especificaciones aprobadas de Tessl y las decisiones del investigador D-01 a D-14.

El propósito de esta intervención fue identificar incumplimientos, riesgos arquitectónicos y limitaciones de cobertura que no hubieran sido detectados por las pruebas automatizadas existentes.

#### Metodología de revisión

Gemini inspeccionó el código de producción, incluyendo esquemas, modelos de datos, servicios financieros, almacenamiento de eventos, proyecciones CQRS, mecanismos de auditoría, migraciones, operaciones programadas y configuración de infraestructura.

También revisó las pruebas disponibles y sus mecanismos de preparación, con el objetivo de distinguir la conformidad de la implementación de los comportamientos que únicamente están verificados mediante pruebas.

La auditoría fue ejecutada sin modificar archivos.

#### Resultados de cumplimiento

Según el análisis estático reportado por Gemini, trece de las catorce decisiones evaluadas fueron clasificadas como conformes. La decisión D-09 recibió una clasificación de cumplimiento parcial debido a un defecto identificado en el manejo de versiones durante el reembolso de transferencias ACH.

Las áreas clasificadas como conformes incluyen precisión monetaria, conversión de divisas, migración de cuentas, almacenamiento de eventos, proyecciones CQRS, límites financieros, MFA, restricciones de moneda, cifrado, auditoría, idempotencia y concurrencia optimista.

Sin embargo, estas clasificaciones constituyen resultados del análisis de código efectuado por el agente y no sustituyen las pruebas de integración ni las verificaciones de infraestructura.

#### Hallazgo crítico: incremento duplicado de versión en ACH

La auditoría identificó una posible inconsistencia en `backend/app/services/transfer_service.py`, dentro de la función `fail_ach_transfer`.

Según el análisis, esta función incrementa manualmente la versión de la cuenta origen durante un reembolso. Posteriormente, el mecanismo `append_domain_event` vuelve a incrementar la versión al registrar el evento `AchTransferFailed`.

Como consecuencia, la versión persistida de la cuenta podría avanzar dos unidades mientras el evento de dominio representa un incremento de una sola unidad.

Este comportamiento incumpliría las invariantes definidas en D-09, D-06 y D-14, pudiendo provocar discrepancias entre el estado persistido y las proyecciones reconstruidas a partir de eventos.

El hallazgo fue identificado mediante inspección estática y requiere una prueba de reproducción antes de aplicar la corrección.

#### Hallazgos adicionales

La auditoría también identificó riesgos y limitaciones que deben revisarse en intervenciones posteriores:

- **Idempotencia D-13:** existe una posible continuación indebida de la ejecución si se encuentra un registro de idempotencia confirmado, pero no se recupera el objeto de transferencia asociado.
- **Planificador de pagos D-09:** se genera una clave determinista para las ejecuciones recurrentes, pero no se verificó una protección transaccional suficiente frente a ejecuciones concurrentes.
- **Concurrencia D-14:** las pruebas existentes cubren conflictos secuenciales, pero carecen de una verificación específica de solicitudes simultáneas.
- **Pruebas ACH:** falta una aserción explícita de integridad de las proyecciones después de un reembolso.
- **Configuración de pruebas:** el cliente de pruebas inyecta automáticamente encabezados de idempotencia en determinadas condiciones, lo que puede ocultar incumplimientos si no se diseñan pruebas negativas explícitas.

También permanecen pendientes las verificaciones de persistencia de volúmenes Docker, terminación TLS, funcionamiento del proxy inverso y aislamiento del planificador bajo infraestructura real.

#### Análisis del investigador

Esta auditoría permitió identificar un riesgo que no había sido detectado por la suite automatizada previamente ejecutada.

El resultado evidencia que una tasa del 100 % de pruebas exitosas no garantiza la ausencia de defectos en el sistema, especialmente cuando las pruebas omiten determinadas invariantes de consistencia.

La revisión también mostró la importancia de comprobar directamente la relación entre los eventos de dominio y las proyecciones CQRS, en lugar de verificar exclusivamente saldos o respuestas HTTP.

Por otra parte, las recomendaciones del agente deben evaluarse cuidadosamente. Una consulta previa de idempotencia, por ejemplo, no garantiza por sí sola la exclusión de ejecuciones simultáneas si no cuenta con mecanismos adecuados de atomicidad.

#### Decisión del investigador

Se decidió priorizar la investigación del incremento duplicado de versiones durante el reembolso ACH.

La siguiente intervención deberá incorporar una prueba de regresión que reproduzca la inconsistencia antes de modificar el código. Posteriormente, se realizará una corrección mínima y se ejecutará nuevamente la regresión completa del backend.

Los demás hallazgos permanecerán registrados para su tratamiento posterior, evitando realizar múltiples cambios arquitectónicos simultáneos.

#### Estado del proyecto

**Línea base previa:** 128 pruebas backend y 119 frontend exitosas.

**Auditoría:** completada en modalidad de solo lectura.

**Hallazgo prioritario:** posible defecto crítico de consistencia entre versiones de cuenta y proyecciones CQRS durante reembolsos ACH.

**Pendiente:** reproducción y corrección del defecto, fortalecimiento de idempotencia y concurrencia, auditoría del frontend y validación integral en infraestructura real.

La Etapa 4 no se considera finalizada hasta verificar estos aspectos.

### Fase de implementación — Interacción 37: Corrección de inconsistencia de versiones durante reembolsos ACH

Se realizó una intervención enfocada en reproducir y corregir el defecto crítico identificado durante la auditoría de cumplimiento de la Etapa 4 de Shift Bank, relacionado con el manejo de versiones de cuenta durante el reembolso de transferencias ACH fallidas.

#### Diagnóstico y reproducción del defecto

La auditoría anterior había identificado que `fail_ach_transfer`, implementada en `backend/app/services/transfer_service.py`, incrementaba manualmente la versión de la cuenta origen y posteriormente invocaba `append_domain_event`, función que también incrementaba la versión para el evento `AchTransferFailed`.

Para confirmar el defecto, Gemini incorporó una nueva prueba de regresión en `backend/tests/test_ach_transfers.py`, denominada `test_ach_failure_refund_single_version_increment_and_projection_consistency`.

La prueba verificaba el reembolso exacto de los fondos, el incremento de versión de cuenta, la creación del evento correspondiente y la consistencia entre el estado persistido y las proyecciones CQRS reconstruidas.

Antes de modificar el código de producción, se ejecutó la prueba contra la implementación original.

**El resultado fue fallido**, reproduciendo la inconsistencia:

```text
FAILED test_ach_failure_refund_single_version_increment_and_projection_consistency

assert 4 == (2 + 1)
```

Este resultado confirmó que la versión de la cuenta avanzaba dos unidades, pasando de 2 a 4, cuando el comportamiento requerido establecía un incremento de una sola unidad.

#### Corrección implementada

Una vez reproducido el defecto, Gemini modificó `fail_ach_transfer` para eliminar el incremento manual redundante de `from_acc.version`.

La función pasó a calcular anticipadamente la versión esperada para incluirla en el evento `AchTransferFailed`, mientras que la actualización efectiva de la versión quedó delegada exclusivamente a `append_domain_event`.

La corrección permitió mantener la correspondencia entre la versión almacenada de la cuenta, la versión registrada en el evento de dominio y el resultado de reconstruir las proyecciones CQRS.

Adicionalmente, la prueba incorporada verificó que una llamada repetida sobre una transferencia ACH ya fallida no produjera otro reembolso ni incrementos adicionales de versión.

#### Resultados de verificación

| Verificación | Resultado |
|---|---:|
| Nueva prueba antes de la corrección | 1 fallida |
| Nueva prueba después de la corrección | 1 exitosa |
| Suite de transferencias ACH | 12/12 exitosas |
| Suite de event sourcing y CQRS | 4/4 exitosas |
| Suite de idempotencia D-13 | 15/15 exitosas |
| Suite backend completa | 129/129 exitosas |
| Advertencias backend | 3 |

La nueva prueba también verificó satisfactoriamente la integridad de las proyecciones mediante `verify_projections_integrity` y su consistencia después de una reconstrucción.

#### Análisis del investigador

Esta intervención constituye evidencia empírica de un defecto funcional que había permanecido sin detectar a pesar de que la suite automatizada anterior registraba 128 pruebas exitosas.

La diferencia entre los resultados obtenidos antes y después de la corrección permite establecer una relación directa entre la modificación implementada y la eliminación del comportamiento defectuoso.

El caso demuestra que las pruebas existentes no cubrían suficientemente la relación entre las versiones persistidas, los eventos de dominio y las proyecciones reconstruidas después de un reembolso ACH.

La incorporación de una prueba específica permitió ampliar la cobertura y evitar que el mismo defecto reaparezca inadvertidamente durante modificaciones posteriores.

#### Decisión del investigador

Con el defecto crítico corregido, se decidió continuar con los hallazgos relacionados con idempotencia.

La siguiente intervención investigará el comportamiento del sistema cuando existe un registro de idempotencia confirmado, pero no es posible recuperar la operación financiera asociada.

Se priorizará un comportamiento de fallo seguro que impida ejecutar nuevamente una operación ya confirmada y producir efectos financieros duplicados.

#### Estado del proyecto

**Defecto D-09/D-06/D-14:** reproducido y corregido.

**Regresión backend:** 129/129 pruebas exitosas.

**Integridad de proyecciones ACH:** verificada mediante una nueva prueba de regresión.

**Pendiente:** endurecimiento de recuperación idempotente D-13, revisión de concurrencia en el planificador, pruebas simultáneas D-14, auditoría del frontend y validación en infraestructura real.

La Etapa 4 continúa en fase de verificación y fortalecimiento de sus garantías técnicas.

### Fase de implementación — Interacción 38: Fortalecimiento de la recuperación de operaciones idempotentes

Se realizó una intervención enfocada en investigar y corregir un riesgo de control de flujo asociado con la recuperación de operaciones previamente confirmadas mediante claves de idempotencia.

#### Diagnóstico del problema

La auditoría anterior había identificado que las funciones `execute_transfer` y `execute_ach_transfer` consultaban el registro de idempotencia antes de ejecutar operaciones financieras. Sin embargo, cuando existía un registro confirmado y no podía recuperarse la transferencia correspondiente, ambas funciones podían continuar hacia las validaciones y la lógica de ejecución normal.

Para investigar este comportamiento, Gemini incorporó dos pruebas de regresión que simulaban la ausencia del registro de transferencia manteniendo su registro de idempotencia confirmado.

Antes de modificar el código, ambas pruebas fallaron: el sistema respondió HTTP 409 en lugar del error de integridad esperado. Esto confirmó que la ejecución continuaba hasta las validaciones de concurrencia D-14, aunque no demostró que se produjera efectivamente un débito duplicado.

#### Corrección implementada

Gemini modificó `backend/app/services/transfer_service.py`, incorporando un comportamiento de fallo seguro en las operaciones internas y ACH.

Cuando se encuentra una clave de idempotencia confirmada, pero no es posible recuperar la transferencia asociada, el sistema interrumpe el procesamiento y devuelve HTTP 500 con el código estructurado `IDEMPOTENT_RECORD_CORRUPTED`.

Esta corrección evita que una operación inconsistente continúe hacia la lógica financiera y permite distinguir errores de integridad de conflictos normales de versiones de cuenta.

También se inspeccionó el servicio de conversiones, cuya recuperación idempotente utiliza directamente la respuesta persistida y no presenta el mismo mecanismo de continuación.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Nuevas pruebas antes de corregir | 2 fallidas |
| Nuevas pruebas después de corregir | 2 exitosas |
| Pruebas D-13 | 17/17 exitosas |
| Pruebas backend relacionadas | 45/45 exitosas |
| Suite backend completa | 131/131 exitosas |
| Advertencias | 3 |

#### Análisis del investigador

La intervención permitió identificar y eliminar una ruta de ejecución que no respetaba completamente el principio de fallo seguro ante inconsistencias en registros de idempotencia.

La reproducción previa confirmó que el sistema alcanzaba las verificaciones de concurrencia cuando debía interrumpirse inmediatamente. La corrección impide esta continuación y proporciona una respuesta estructurada que permite identificar el problema.

La incorporación de dos pruebas de regresión amplía la cobertura de D-13 frente a estados inconsistentes de persistencia.

#### Decisión del investigador

Se decidió continuar con la revisión de concurrencia del planificador de pagos recurrentes, identificada durante la auditoría estática.

La siguiente intervención deberá determinar si varias ejecuciones simultáneas pueden procesar una misma ocurrencia programada y, en caso afirmativo, incorporar un mecanismo transaccional que garantice la ejecución única.

**Estado:** recuperación idempotente endurecida y suite backend de 131 pruebas exitosa. Permanecen pendientes la concurrencia del planificador, las pruebas simultáneas D-14, la auditoría del frontend y la integración final.

### Fase de implementación — Interacción 39: Corrección de concurrencia e idempotencia en el planificador de pagos recurrentes

Se realizó una intervención enfocada en investigar y corregir una posible condición de carrera en el planificador de pagos recurrentes de Shift Bank, relacionada con las garantías de ejecución única establecidas en D-09, D-12 y D-13.

#### Diagnóstico y reproducción

Gemini inspeccionó la implementación del planificador, el almacenamiento de eventos, los modelos de persistencia y las pruebas existentes.

El análisis identificó que dos procesos podían consultar simultáneamente una programación vencida antes de que cualquiera confirmara sus cambios. Como resultado, ambos podían procesar la misma ocurrencia sin una protección transaccional suficiente.

Inicialmente se incorporó una prueba con dos sesiones independientes contra una base de datos SQLite temporal. Su primera ejecución secuencial fue exitosa y no permitió confirmar el defecto.

Posteriormente, Gemini modificó la prueba para utilizar dos hilos concurrentes sincronizados mediante `threading.Barrier`.

En esta segunda ejecución, antes de modificar el código de producción, la prueba falló:

```text
FAILED test_concurrent_scheduler_execution_does_not_duplicate_transfer

AssertionError: Expected 1 transfer, but found 2
```

El resultado confirmó la posibilidad de registrar dos transferencias correspondientes a una misma ocurrencia programada bajo ejecución concurrente.

#### Corrección implementada

Gemini modificó `backend/app/services/recurring_service.py`, incorporando varios mecanismos complementarios.

Primero, se añadió la adquisición de un bloqueo de escritura SQLite mediante `BEGIN IMMEDIATE`, con el propósito de serializar las operaciones de los trabajadores concurrentes.

Segundo, se implementó una nueva consulta de la programación dentro de la transacción para comprobar que continuara activa y vencida.

Tercero, se incorporó una verificación de idempotencia a partir de una clave determinista, construida con el identificador de la programación y la fecha de ejecución.

Finalmente, se añadió el registro de la ocurrencia en la tabla de idempotencia dentro de la misma transacción que confirma los efectos financieros. La restricción de unicidad de la clave proporciona una protección adicional frente a confirmaciones duplicadas.

También se incorporó el tratamiento de conflictos de integridad mediante reversión transaccional.

#### Ajustes durante la implementación

La primera ejecución de la suite de pagos recurrentes después de modificar el servicio presentó siete pruebas fallidas.

La revisión posterior identificó, entre otros problemas, la omisión del retorno de la lista de resultados desde el servicio y errores de preparación de la nueva prueba de recuperación.

Gemini corrigió estos problemas, incluyendo el PIN requerido para crear una programación superior al umbral MFA, el acceso al contador de fallas mediante el modelo persistido y la normalización de fechas para las comparaciones.

La resolución de estos errores permitió restaurar las pruebas existentes y completar la verificación del nuevo comportamiento.

#### Pruebas adicionales

Se incorporaron dos pruebas de regresión:

1. `test_concurrent_scheduler_execution_does_not_duplicate_transfer`, que verifica la ejecución única mediante dos trabajadores concurrentes y sesiones independientes.

2. `test_scheduler_repeated_ticks_and_recovery_after_failure`, que comprueba que las ejecuciones repetidas no generen duplicados y que una programación pueda recuperarse después de un intento fallido por fondos insuficientes.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Prueba de concurrencia antes de corregir | Fallida: 2 transferencias |
| Prueba de concurrencia después de corregir | Exitosa: 1 transferencia |
| Pruebas de pagos recurrentes | 12/12 exitosas |
| Pruebas event sourcing/CQRS | 4/4 exitosas |
| Pruebas de idempotencia D-13 | 17/17 exitosas |
| Suite backend completa | 133/133 exitosas |
| Advertencias | 3 |

#### Análisis del investigador

Esta intervención permitió reproducir empíricamente un defecto de concurrencia que no había sido detectado mediante pruebas secuenciales.

El contraste entre la prueba secuencial exitosa y la prueba verdaderamente concurrente fallida demuestra la importancia de diseñar escenarios que reproduzcan las condiciones de ejecución responsables de los defectos.

La corrección combinó mecanismos de serialización de transacciones, verificación del estado persistido y unicidad de registros de idempotencia.

También se evidenció que las modificaciones introducidas por un agente pueden generar regresiones temporales, por lo que resulta necesario mantener una verificación incremental y ejecutar la suite completa después de cada intervención.

#### Decisión del investigador

Una vez corregido el defecto del planificador, se decidió continuar con la verificación de concurrencia optimista D-14 bajo solicitudes financieras simultáneas.

La siguiente intervención deberá comprobar que dos operaciones con la misma versión esperada de cuenta no puedan confirmarse simultáneamente, preservando la atomicidad y la consistencia del sistema.

#### Estado del proyecto

**Concurrencia del planificador:** defecto reproducido y corregido.

**Regresión backend:** 133/133 pruebas exitosas.

**Pendiente:** pruebas simultáneas D-14, auditoría de cumplimiento del frontend, integración real, despliegue y preparación de evidencias finales.

La Etapa 4 permanece en fase de validación técnica y cierre.

### Fase de implementación — Interacción 40: Corrección de concurrencia optimista D-14 bajo operaciones simultáneas

Se realizó una intervención enfocada en comprobar el comportamiento del mecanismo de concurrencia optimista D-14 cuando dos operaciones financieras intentan modificar simultáneamente una cuenta utilizando la misma versión esperada.

#### Diagnóstico y reproducción

Gemini incorporó una prueba de concurrencia utilizando una base de datos SQLite temporal persistida en archivo, sesiones independientes y dos hilos de ejecución.

Ambas operaciones intentaban realizar transferencias desde la misma cuenta utilizando versiones esperadas iguales a 1 y claves de idempotencia diferentes.

Antes de modificar el código de producción, la prueba reprodujo un defecto:

```text
FAILED test_concurrent_transfers_same_version_conflict_d14

AssertionError: Expected exactly 1 success, but got 2 successes
```

El resultado evidenció que dos operaciones simultáneas podían superar la validación de versiones y completarse, incumpliendo el comportamiento de concurrencia optimista previsto en D-14.

#### Corrección implementada

Gemini modificó `backend/app/services/event_store.py`, específicamente la función `append_domain_event`.

Se incorporó un mecanismo de bloqueo de escritura de SQLite mediante `acquire_sqlite_write_lock`, con el objetivo de serializar el acceso a las modificaciones financieras.

Adicionalmente, se introdujo `db.expire_all()` antes de la comprobación de versiones para invalidar los valores almacenados en caché por la sesión de SQLAlchemy y recuperar el estado persistido actualizado.

Según la verificación realizada, después de esta modificación una operación se completó mientras que la solicitud competidora fue rechazada con HTTP 409 y código `ACCOUNT_VERSION_CONFLICT`.

#### Ampliación de cobertura

Además de la prueba sobre transferencias internas, Gemini incorporó escenarios concurrentes para conversiones de divisas y transferencias ACH.

Las tres pruebas comprobaron que únicamente una operación se confirmara y que la operación competidora fuera rechazada debido al conflicto de versiones.

También se verificó la integridad de las proyecciones CQRS después de ejecutar los escenarios.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Prueba D-14 antes de la corrección | Fallida: 2 transferencias exitosas |
| Pruebas concurrentes después de corregir | 3 exitosas |
| Suite de transferencias internas | 17/17 |
| Suite de conversiones | 11/11 |
| Suite de transferencias ACH | 13/13 |
| Suite de event sourcing y CQRS | 4/4 |
| Suite de idempotencia D-13 | 17/17 |
| Suite backend completa | 136/136 |
| Advertencias | 3 |

#### Análisis del investigador

La intervención permitió identificar un defecto que no había sido detectado por las pruebas secuenciales de concurrencia optimista.

La reproducción confirmó que el mecanismo anterior podía aceptar dos operaciones que compartían una misma versión esperada de cuenta.

La corrección centralizó la protección en el almacenamiento de eventos, buscando mantener un comportamiento consistente entre transferencias internas, conversiones y ACH.

No obstante, la incorporación de bloqueo de escritura e invalidación de caché requiere comprobar cuidadosamente el orden de las mutaciones financieras y de las operaciones de persistencia.

En particular, debe verificarse que la invalidación de objetos de SQLAlchemy no descarte modificaciones monetarias que todavía no hayan sido confirmadas o sincronizadas con la base de datos.

También resulta necesario comprobar que las pruebas concurrentes sincronizan efectivamente las funciones utilizadas por los servicios de producción.

Estas comprobaciones adicionales no invalidan los resultados exitosos obtenidos, pero permiten evaluar con mayor rigor la seguridad de la corrección.

#### Decisión del investigador

Se decidió realizar una verificación puntual de seguridad transaccional sobre el cambio introducido en `append_domain_event` antes de iniciar la auditoría del frontend.

La siguiente intervención revisará el orden de bloqueos, actualizaciones de saldos, validaciones de versiones, persistencia de eventos y confirmaciones transaccionales.

#### Estado del proyecto

**Concurrencia D-14:** defecto reproducido y corrección verificada mediante tres escenarios concurrentes.

**Regresión backend:** 136/136 pruebas exitosas.

**Pendiente inmediato:** verificar que el bloqueo y la invalidación de caché no afecten las operaciones monetarias.

**Pendiente posterior:** auditoría del frontend, integración real, despliegue y cierre académico de la Etapa 4.

### Fase de implementación — Interacción 41: Verificación de seguridad transaccional y corrección de pruebas concurrentes

Se realizó una intervención enfocada en verificar la seguridad transaccional de las modificaciones recientes sobre el mecanismo de concurrencia optimista D-14 de Shift Bank.

El objetivo consistió en comprobar que los bloqueos de escritura SQLite y los mecanismos de invalidación de caché de SQLAlchemy no produjeran pérdidas de modificaciones financieras pendientes ni inconsistencias entre los estados persistidos y los eventos de dominio.

#### Análisis de las operaciones financieras

Gemini inspeccionó el orden de ejecución de las transferencias internas, conversiones de divisas, transferencias ACH, reembolsos y pagos recurrentes.

La revisión abarcó la consulta de cuentas, validación de límites, bloqueo de escritura, actualización de versiones, cambios de saldos, almacenamiento de eventos, auditoría y confirmación de transacciones.

Según el análisis realizado, las transferencias internas, conversiones y operaciones ACH aplican las modificaciones de saldos después de la validación de versiones efectuada en `append_domain_event`.

En el caso de los reembolsos ACH, se identificó la necesidad de asegurar la sincronización del saldo reembolsado con la transacción antes de continuar con el almacenamiento del evento correspondiente.

#### Ajustes de seguridad transaccional

Se realizaron dos modificaciones enfocadas en fortalecer la persistencia:

**Invalidación selectiva de caché**

En `backend/app/services/event_store.py` se reemplazó `db.expire_all()` por `db.expire(acc)` para actualizar selectivamente las cuentas involucradas en la verificación de versiones.

Este cambio reduce el alcance de la invalidación y evita descartar innecesariamente el estado pendiente de otros objetos presentes en la sesión.

**Sincronización del reembolso ACH**

En `backend/app/services/transfer_service.py` se incorporó una operación `db.flush()` después de actualizar el saldo durante el reembolso ACH.

Su propósito es asegurar que la actualización monetaria quede sincronizada dentro de la transacción activa antes de continuar con la generación del evento de dominio.

#### Corrección de la instrumentación de pruebas

La revisión también detectó que las pruebas de concurrencia introducidas anteriormente utilizaban `monkeypatch` sobre `event_store.append_domain_event`.

Sin embargo, los servicios financieros importaban directamente dicha función. Como consecuencia, modificar la referencia en el módulo original no necesariamente alteraba la referencia utilizada internamente por los servicios.

Gemini comprobó esta diferencia y corrigió las pruebas para aplicar los mecanismos de sincronización directamente sobre las referencias utilizadas por `transfer_service` y `conversion_service`.

Esta modificación resulta metodológicamente relevante porque permite asegurar que las barreras de los hilos intercepten la ejecución real de las funciones que las pruebas pretenden sincronizar.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas financieras enfocadas | 74/74 exitosas |
| Pruebas backend completas | 136/136 exitosas |
| Fallas backend | 0 |
| Advertencias | 3 |
| Archivos modificados | 5 |

Los archivos modificados corresponden a `event_store.py`, `transfer_service.py` y las pruebas de transferencias internas, conversiones y ACH.

#### Análisis del investigador

La intervención permitió fortalecer tanto la implementación como la validez de los procedimientos de verificación.

La revisión de `db.expire_all()` mostró la importancia de considerar los efectos de las operaciones del ORM sobre el estado transaccional, especialmente cuando los servicios financieros realizan varias modificaciones dentro de una misma sesión.

Adicionalmente, el hallazgo relacionado con `monkeypatch` evidencia que una prueba concurrente puede ejecutarse exitosamente sin sincronizar correctamente el punto crítico que pretende evaluar.

La corrección de las referencias instrumentadas mejora la correspondencia entre el escenario de prueba y el comportamiento de producción.

Aunque la suite backend se mantiene completamente exitosa, estos resultados corresponden a pruebas automatizadas y revisión del código. Las verificaciones de integración y despliegue en infraestructura real permanecen pendientes.

#### Decisión del investigador

Se decidió considerar completada esta revisión puntual de seguridad transaccional y continuar con la auditoría de cumplimiento del frontend.

La siguiente intervención revisará los contratos de comunicación con el backend, los requisitos monetarios, la idempotencia, las versiones de cuenta y los flujos de interacción del usuario.

La auditoría se realizará inicialmente en modalidad de solo lectura, con el propósito de identificar incumplimientos antes de introducir nuevas modificaciones.

#### Estado del proyecto

**Backend:** 136 pruebas automatizadas exitosas.

**Seguridad transaccional D-14:** revisada y fortalecida.

**Pruebas concurrentes:** instrumentación corregida y regresión exitosa.

**Pendientes:** auditoría del frontend, corrección de hallazgos, integración real, validación de infraestructura y cierre académico de la Etapa 4.

### Fase de implementación — Interacción 42: Auditoría de cumplimiento del frontend y sus contratos de integración

Se realizó una auditoría de solo lectura sobre el frontend de Shift Bank en la Etapa 4, utilizando como referencia los requisitos SEED-4, las especificaciones aprobadas de Tessl y las decisiones D-01 a D-14.

#### Objetivo

Evaluar la conformidad de la interfaz React con los contratos de comunicación del backend e identificar defectos funcionales, riesgos de integración y limitaciones de cobertura que no hubieran sido detectados mediante las pruebas existentes.

#### Metodología

Gemini examinó los componentes del frontend, el cliente HTTP, los tipos de TypeScript, las utilidades monetarias y las pruebas automatizadas.

La revisión se concentró en precisión financiera, separación de monedas, transferencias, conversiones, pagos ACH, pagos recurrentes, límites, MFA, idempotencia y concurrencia optimista.

También se contrastaron las estructuras de las solicitudes frontend con los esquemas y endpoints implementados en el backend.

#### Resultados generales

La auditoría clasificó como conformes los componentes principales relacionados con precisión monetaria, separación de monedas, restricciones financieras, autorización MFA, presentación de saldos y control de versiones de cuenta.

Según la inspección realizada, el frontend utiliza cadenas decimales e implementa cálculos financieros mediante enteros `BigInt`, evitando las operaciones monetarias con números de punto flotante.

Se confirmó asimismo la presencia de versiones de cuenta en las solicitudes financieras y el tratamiento de conflictos de concurrencia mediante mensajes al usuario y actualización de la información de cuentas.

No obstante, se identificaron dos hallazgos que requieren intervención.

#### Hallazgo 1: ciclo de vida de claves de idempotencia D-13

La auditoría identificó que determinadas operaciones financieras generan una nueva clave UUID cuando se invoca el cliente HTTP sin proporcionar explícitamente una clave de idempotencia.

En el flujo actual, los componentes pueden realizar solicitudes sin conservar la clave correspondiente al primer intento.

Esto representa un problema cuando el servidor confirma una operación, pero la respuesta no llega al navegador. Si el usuario intenta nuevamente la misma operación, una clave diferente impediría recuperar directamente el resultado confirmado.

Aunque el control de versiones D-14 puede rechazar la nueva solicitud, dicho rechazo no equivale a la recuperación idempotente del resultado original.

Se recomendó incorporar una identidad estable por operación lógica, conservando tanto el UUID como los parámetros originales durante los reintentos.

#### Hallazgo 2: presentación de errores estructurados

Se observó que el cliente HTTP puede transformar objetos de error en cadenas JSON mediante `JSON.stringify`.

Como consecuencia, ciertos mensajes de error del backend pueden presentarse en la interfaz en un formato técnico poco comprensible.

Se recomendó priorizar los campos estructurados `code` y `message`, manteniendo la información necesaria para distinguir conflictos de versiones, errores de idempotencia y fallas de autorización.

#### Limitación de cobertura adicional

Se identificó la ausencia de pruebas enfocadas en la integración completa de `App.tsx` con los componentes financieros.

Aunque los componentes cuentan con pruebas individuales, todavía deben verificarse los flujos que involucran varios elementos, como la apertura de una transferencia, la solicitud de MFA, el resultado de la operación y la actualización de saldos y versiones.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Suite frontend | 119/119 exitosas |
| Compilación de producción | Exitosa |
| Última regresión backend conocida | 136/136 exitosas |
| Hallazgos de frontend | 2 |
| Limitaciones adicionales de cobertura | 1 |
| Archivos modificados | 0 |

La auditoría se realizó en modalidad de solo lectura, sin modificar el proyecto.

#### Análisis del investigador

Los resultados muestran que la conformidad individual de los componentes no garantiza necesariamente el cumplimiento de los contratos durante una interacción completa.

En particular, el mecanismo de idempotencia depende tanto del comportamiento del servidor como de la capacidad del cliente para conservar la identidad de una operación entre intentos.

El hallazgo relacionado con la presentación de errores también evidencia la necesidad de mantener una representación consistente de los contratos de comunicación.

La revisión permite priorizar correcciones específicas sin introducir modificaciones innecesarias en funcionalidades que ya cuentan con evidencia favorable.

#### Decisión del investigador

Se decidió intervenir primero el ciclo de vida de las claves de idempotencia D-13, debido a su relación directa con la recuperación segura de operaciones financieras.

Posteriormente se corregirá la presentación de errores estructurados y se incorporarán pruebas de integración de los principales flujos de usuario.

#### Estado del proyecto

**Auditoría frontend:** completada.

**Hallazgo prioritario:** persistencia de claves de idempotencia durante reintentos.

**Pendientes:** correcciones D-13, manejo de errores, pruebas de integración entre componentes, verificación del despliegue y preparación de evidencias finales.

La Etapa 4 continúa en fase de cierre técnico.

### Fase de implementación — Interacción 43: Implementación del ciclo de vida de idempotencia D-13 en el frontend

Se realizó una intervención enfocada en corregir el manejo de claves de idempotencia de las operaciones financieras iniciadas desde el frontend de Shift Bank.

El objetivo consistió en asegurar que los reintentos de una misma operación conservaran su identificador UUID y sus parámetros financieros originales, evitando generar una nueva identidad por cada solicitud HTTP.

#### Diagnóstico

La auditoría anterior había identificado que el cliente HTTP generaba automáticamente una nueva clave UUID cuando una operación financiera era invocada sin proporcionar explícitamente una clave de idempotencia.

Esta implementación representaba una limitación ante escenarios en los que el servidor confirmaba la operación, pero la respuesta HTTP no llegaba al navegador.

Si el usuario intentaba nuevamente la misma transferencia, una nueva clave impediría recuperar directamente el resultado mediante el mecanismo de idempotencia D-13.

#### Implementación

Gemini modificó `frontend/src/App.tsx` para incorporar un estado denominado `ActiveOperation`, encargado de conservar la clave de idempotencia junto con una representación de los parámetros de la operación.

Este mecanismo permite reutilizar la misma clave cuando se intenta nuevamente una operación con parámetros idénticos y generar una nueva clave cuando los parámetros son modificados deliberadamente.

La implementación se aplicó tanto a transferencias internas como a transferencias ACH.

Asimismo, se modificó `ConversionModal.tsx` para proporcionar un comportamiento equivalente durante conversiones de moneda.

Se actualizó la estructura `PendingAction` para conservar la clave de idempotencia durante el flujo de autenticación multifactor, evitando que el paso por el modal MFA genere automáticamente una nueva identidad.

También se añadieron mecanismos de control de envíos simultáneos mediante verificaciones del estado de envío en los componentes correspondientes.

#### Pruebas incorporadas

Gemini creó el archivo `frontend/src/__tests__/IdempotencyLifecycle.test.tsx`, que contiene ocho pruebas enfocadas en:

- Conservación de claves y parámetros durante reintentos de transferencias internas.
- Generación de claves nuevas ante cambios deliberados del formulario.
- Prevención de envíos duplicados por interacciones rápidas.
- Conservación de la clave durante el proceso MFA.
- Reintentos de transferencias ACH.
- Reintentos de conversiones de moneda.
- Generación de nuevas claves en conversiones con parámetros modificados.
- Actualización de cuentas tras conflictos de versión D-14 sin reintentos automáticos.

Durante la verificación inicial, la suite frontend presentó tres pruebas fallidas debido a incompatibilidades entre los mocks existentes y las nuevas firmas de los métodos del cliente HTTP.

Gemini actualizó las expectativas de `ConversionModal.test.tsx` para contemplar el argumento adicional de idempotencia.

Posteriormente, la revisión de TypeScript detectó tres errores relacionados con un import no utilizado y propiedades faltantes en respuestas simuladas de conversiones. Estos también fueron corregidos.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Nuevas pruebas de idempotencia | 8/8 exitosas |
| Suite frontend completa | 127/127 exitosas |
| Archivos de pruebas frontend | 10 |
| Errores TypeScript | 0 |
| Compilación de producción | Exitosa |
| Última regresión backend conocida | 136/136 exitosas |

Los archivos modificados fueron `App.tsx`, `ConversionModal.tsx`, `TransferModal.tsx`, `IdempotencyLifecycle.test.tsx` y `ConversionModal.test.tsx`.

#### Análisis del investigador

La intervención permitió fortalecer el cumplimiento de D-13 desde la interfaz, extendiendo la idempotencia más allá del almacenamiento y la validación realizados por el backend.

La implementación actual conserva una identidad estable durante los reintentos de operaciones con parámetros equivalentes, mientras el estado correspondiente permanezca disponible en React.

Los resultados obtenidos muestran que las ocho pruebas incorporadas se ejecutan exitosamente, aunque todavía no se ha verificado la recuperación de operaciones después de una recarga del navegador ni en un entorno integrado con servicios reales.

Asimismo, la inspección de los cambios sugiere que ciertos errores HTTP 409 podrían estar siendo interpretados indistintamente como conflictos de versiones, cuando también pueden corresponder a errores de idempotencia.

Por esta razón, resulta necesario revisar el tratamiento estructurado de errores antes de considerar completado el contrato D-13 en la interfaz.

#### Decisión del investigador

Se decidió continuar con el manejo de respuestas de error estructuradas y la diferenciación entre conflictos de idempotencia D-13 y conflictos de versiones D-14.

La siguiente intervención incorporará pruebas enfocadas en el cliente HTTP y en los componentes responsables de presentar errores, preservando el comportamiento de reintento seguro implementado durante esta interacción.

#### Estado del proyecto

**Frontend:** 127 pruebas automatizadas exitosas, sin errores TypeScript y con compilación de producción satisfactoria.

**D-13 frontend:** ciclo de vida de claves implementado y verificado mediante ocho pruebas nuevas.

**Pendiente inmediato:** tratamiento de errores estructurados y distinción de conflictos HTTP 409.

**Pendiente posterior:** pruebas integradas de los principales flujos de usuario, validación Docker/Nginx/TLS, revisión de archivos Git y preparación de evidencias finales.

La Etapa 4 permanece en fase de cierre técnico.

### Fase de implementación — Interacción 44: Corrección del manejo de errores estructurados y diferenciación de conflictos D-13 y D-14

Se realizó una intervención enfocada en mejorar la interpretación de los errores HTTP del frontend de Shift Bank, particularmente aquellos relacionados con idempotencia D-13 y concurrencia optimista D-14.

#### Diagnóstico e implementación

La auditoría del frontend había identificado que algunos errores estructurados del backend podían presentarse como cadenas JSON sin formato. Además, los errores HTTP 409 no siempre se diferenciaban según su causa.

Gemini modificó `frontend/src/api/client.ts` para ampliar la clase `ApiError`, incorporando atributos destinados a conservar el estado HTTP, el código del error, su mensaje y los detalles estructurados.

El cliente HTTP fue actualizado para interpretar respuestas con campos `code` y `message`, estructuras anidadas de FastAPI mediante `detail`, mensajes heredados y fallas de comunicación sin respuesta HTTP.

Posteriormente, se actualizaron los manejadores de errores en `App.tsx` y `ConversionModal.tsx` para distinguir los conflictos de idempotencia de los conflictos de versiones de cuenta.

Cuando el backend informa `ACCOUNT_VERSION_CONFLICT`, el frontend actualiza la información de las cuentas sin repetir automáticamente la operación.

Cuando informa `IDEMPOTENCY_KEY_REUSE`, la aplicación presenta un mensaje diferenciado y evita tratar el problema como una versión desactualizada.

También se incorporó un tratamiento conservador para conflictos HTTP 409 no identificados.

#### Ampliación de las pruebas

Se creó `frontend/src/__tests__/ErrorParsing.test.ts`, con siete pruebas del límite HTTP del cliente.

Estas pruebas verifican la interpretación de respuestas estructuradas, errores anidados, mensajes heredados, bloqueo MFA, errores de integridad, fallas de red y respuestas de infraestructura sin JSON válido.

Adicionalmente, se ampliaron las pruebas de `IdempotencyLifecycle.test.tsx` con escenarios de conflictos D-13 y errores HTTP 409 desconocidos.

Durante la ejecución inicial de la suite completa se identificó una incompatibilidad en los mocks de `ConversionModal.test.tsx`. Gemini actualizó dichos mocks para contemplar las nuevas propiedades de `ApiError`.

La verificación de TypeScript también detectó referencias no reconocidas a `global` dentro de las nuevas pruebas. Estas fueron reemplazadas por `globalThis`, permitiendo completar la compilación.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas de interpretación de errores | 7/7 exitosas |
| Pruebas de ciclo de vida de idempotencia | 10/10 exitosas |
| Suite frontend completa | 136/136 exitosas |
| Suite backend completa | 136/136 exitosas |
| Errores TypeScript | 0 |
| Compilación de producción | Exitosa |
| Advertencias backend | 3 |

#### Análisis del investigador

La intervención fortaleció la interoperabilidad entre el cliente React y los contratos de respuesta del backend.

La separación entre códigos de error permite que las decisiones de la interfaz dependan del tipo de conflicto identificado, evitando actualizar innecesariamente las cuentas ante errores de idempotencia.

Las pruebas incorporadas también amplían la cobertura del cliente HTTP, que anteriormente se verificaba principalmente mediante métodos simulados de la API.

No obstante, la implementación introdujo un mecanismo de inferencia de códigos HTTP 409 basado en palabras presentes en los mensajes. Aunque proporciona compatibilidad con respuestas heredadas, este comportamiento debe contrastarse con las respuestas reales del backend para evitar clasificaciones incorrectas.

Asimismo, las pruebas automatizadas actuales no sustituyen la validación de la aplicación ejecutándose con conexiones HTTP reales.

#### Decisión del investigador

Se decidió finalizar la fase de correcciones derivadas de la auditoría del frontend e iniciar la verificación integral del sistema en ejecución.

La siguiente intervención comprobará los principales flujos financieros de Shift Bank mediante solicitudes reales a la API, utilizando una base de datos temporal aislada.

También se revisará el funcionamiento de la interfaz conectada al backend y se documentarán por separado los escenarios verificados, fallidos y no ejecutados.

#### Estado del proyecto

**Backend:** 136 pruebas exitosas.

**Frontend:** 136 pruebas exitosas.

**Manejo de errores:** actualizado y verificado mediante pruebas automatizadas.

**Pendientes:** integración real frontend-backend, verificación Docker/Nginx/TLS, revisión de Git y preparación de evidencias finales.

La Etapa 4 continúa en fase de validación integral y cierre académico.

### Fase de implementación — Interacción 44: Corrección del manejo de errores estructurados y diferenciación de conflictos D-13 y D-14

Se realizó una intervención enfocada en mejorar la interpretación de los errores HTTP del frontend de Shift Bank, particularmente aquellos relacionados con idempotencia D-13 y concurrencia optimista D-14.

#### Diagnóstico e implementación

La auditoría del frontend había identificado que algunos errores estructurados del backend podían presentarse como cadenas JSON sin formato. Además, los errores HTTP 409 no siempre se diferenciaban según su causa.

Gemini modificó `frontend/src/api/client.ts` para ampliar la clase `ApiError`, incorporando atributos destinados a conservar el estado HTTP, el código del error, su mensaje y los detalles estructurados.

El cliente HTTP fue actualizado para interpretar respuestas con campos `code` y `message`, estructuras anidadas de FastAPI mediante `detail`, mensajes heredados y fallas de comunicación sin respuesta HTTP.

Posteriormente, se actualizaron los manejadores de errores en `App.tsx` y `ConversionModal.tsx` para distinguir los conflictos de idempotencia de los conflictos de versiones de cuenta.

Cuando el backend informa `ACCOUNT_VERSION_CONFLICT`, el frontend actualiza la información de las cuentas sin repetir automáticamente la operación.

Cuando informa `IDEMPOTENCY_KEY_REUSE`, la aplicación presenta un mensaje diferenciado y evita tratar el problema como una versión desactualizada.

También se incorporó un tratamiento conservador para conflictos HTTP 409 no identificados.

#### Ampliación de las pruebas

Se creó `frontend/src/__tests__/ErrorParsing.test.ts`, con siete pruebas del límite HTTP del cliente.

Estas pruebas verifican la interpretación de respuestas estructuradas, errores anidados, mensajes heredados, bloqueo MFA, errores de integridad, fallas de red y respuestas de infraestructura sin JSON válido.

Adicionalmente, se ampliaron las pruebas de `IdempotencyLifecycle.test.tsx` con escenarios de conflictos D-13 y errores HTTP 409 desconocidos.

Durante la ejecución inicial de la suite completa se identificó una incompatibilidad en los mocks de `ConversionModal.test.tsx`. Gemini actualizó dichos mocks para contemplar las nuevas propiedades de `ApiError`.

La verificación de TypeScript también detectó referencias no reconocidas a `global` dentro de las nuevas pruebas. Estas fueron reemplazadas por `globalThis`, permitiendo completar la compilación.

#### Resultados de verificación

| Indicador | Resultado |
|---|---:|
| Pruebas de interpretación de errores | 7/7 exitosas |
| Pruebas de ciclo de vida de idempotencia | 10/10 exitosas |
| Suite frontend completa | 136/136 exitosas |
| Suite backend completa | 136/136 exitosas |
| Errores TypeScript | 0 |
| Compilación de producción | Exitosa |
| Advertencias backend | 3 |

#### Análisis del investigador

La intervención fortaleció la interoperabilidad entre el cliente React y los contratos de respuesta del backend.

La separación entre códigos de error permite que las decisiones de la interfaz dependan del tipo de conflicto identificado, evitando actualizar innecesariamente las cuentas ante errores de idempotencia.

Las pruebas incorporadas también amplían la cobertura del cliente HTTP, que anteriormente se verificaba principalmente mediante métodos simulados de la API.

No obstante, la implementación introdujo un mecanismo de inferencia de códigos HTTP 409 basado en palabras presentes en los mensajes. Aunque proporciona compatibilidad con respuestas heredadas, este comportamiento debe contrastarse con las respuestas reales del backend para evitar clasificaciones incorrectas.

Asimismo, las pruebas automatizadas actuales no sustituyen la validación de la aplicación ejecutándose con conexiones HTTP reales.

#### Decisión del investigador

Se decidió finalizar la fase de correcciones derivadas de la auditoría del frontend e iniciar la verificación integral del sistema en ejecución.

La siguiente intervención comprobará los principales flujos financieros de Shift Bank mediante solicitudes reales a la API, utilizando una base de datos temporal aislada.

También se revisará el funcionamiento de la interfaz conectada al backend y se documentarán por separado los escenarios verificados, fallidos y no ejecutados.

#### Estado del proyecto

**Backend:** 136 pruebas exitosas.

**Frontend:** 136 pruebas exitosas.

**Manejo de errores:** actualizado y verificado mediante pruebas automatizadas.

**Pendientes:** integración real frontend-backend, verificación Docker/Nginx/TLS, revisión de Git y preparación de evidencias finales.

La Etapa 4 continúa en fase de validación integral y cierre académico.

### Interacción 45: Validación integral y decisión de cierre de la Etapa 4

Se realizó una intervención destinada a verificar el funcionamiento integrado de Shift Bank mediante solicitudes HTTP reales y una base de datos SQLite temporal aislada.

Durante la ejecución inicial, Gemini CLI presentó errores HTTP 400 `INVALID_ARGUMENT` relacionados con la correspondencia entre llamadas a herramientas y sus respuestas. Estos errores afectaron la ejecución del agente y no constituyen evidencia de un defecto en la aplicación desarrollada.

Tras reanudar el trabajo, Gemini inspeccionó la configuración de FastAPI, SQLite, Vite y los contratos HTTP. Posteriormente, elaboró el script `scripts/verify_live_e2e.py` para comprobar las principales operaciones financieras.

Durante las ejecuciones visibles del script se identificaron errores en las expectativas de prueba, incluyendo diferencias entre códigos HTTP esperados y reales, nombres de campos de solicitudes, rutas de endpoints y procesamiento de respuestas JSON. El agente realizó ajustes sucesivos sobre el script de verificación.

En su informe final, Gemini reportó 44 verificaciones HTTP exitosas sobre cuentas, transferencias, conversiones, ACH, pagos recurrentes, MFA, idempotencia, concurrencia e integridad financiera.

Sin embargo, el registro disponible no presenta una ejecución final completa del script que permita corroborar independientemente las 44 verificaciones. Por esta razón, el resultado se conserva como una afirmación del agente y no como evidencia automatizada concluyente.

#### Resultados confirmados

| Indicador | Resultado |
|---|---:|
| Pruebas backend | 136 exitosas |
| Pruebas frontend | 136 exitosas |
| Errores TypeScript | 0 |
| Compilación frontend | Exitosa |
| Verificaciones HTTP reportadas | 44 |
| Navegador E2E | No verificado |
| Docker/Nginx/TLS | No verificado |

#### Limitaciones

La validación visual de la interfaz mediante un navegador no fue ejecutada de forma automatizada. Tampoco se completó una verificación de despliegue con Docker Compose, persistencia de volúmenes y terminación TLS.

Adicionalmente, se identificaron aspectos pendientes de reproducibilidad asociados con archivos todavía no rastreados por Git.

La guía metodológica del proyecto también establece versiones específicas para Gemini CLI y el modelo utilizado, además de un procedimiento de modificación guiado por especificaciones. Cualquier diferencia entre ese protocolo y las ejecuciones efectivamente registradas deberá declararse como desviación metodológica, sin modificar retroactivamente las evidencias.

#### Análisis y decisión del investigador

La Etapa 4 permitió implementar y verificar mediante pruebas automatizadas una migración arquitectónica significativa hacia cuentas multimoneda, conversión de divisas y Event Sourcing/CQRS.

Durante el proceso se identificaron y corrigieron defectos funcionales relacionados con versiones de cuentas, reembolsos ACH, recuperación idempotente y concurrencia real. Estos hallazgos proporcionan evidencia relevante para evaluar el comportamiento de la herramienta ante cambios arquitectónicos complejos.

Considerando el alcance experimental y los resultados alcanzados, se decidió finalizar las intervenciones de desarrollo y registrar explícitamente las verificaciones que no pudieron completarse.

**Estado de la Etapa 4: cierre experimental con limitaciones documentadas.**

Esta clasificación no implica que la aplicación haya sido validada como sistema listo para producción.

### Fase de cierre — Interacción 46: Elaboración del informe final de la Etapa 4 con Tessl

Se realizó la última interacción del experimento de la Etapa 4 de Shift Bank utilizando Tessl y Gemini CLI.

El objetivo consistió en consolidar los resultados de implementación, pruebas, incidencias, desviaciones metodológicas y limitaciones identificadas durante el desarrollo, sin continuar modificando la aplicación.

Gemini consultó las especificaciones, los registros históricos de interacciones y las evidencias experimentales. También verificó las versiones instaladas de Gemini CLI (`0.65.0`) y Tessl CLI (`0.118.1`), así como el estado de los archivos en Git.

Posteriormente, generó el informe `CIERRE_ETAPA4_TESSL.md` en el directorio de evidencias de la etapa. La creación fue confirmada mediante una comprobación de existencia del archivo.

#### Resultados consolidados

- Backend: 136 pruebas automatizadas exitosas.
- Frontend: 136 pruebas automatizadas exitosas.
- TypeScript: sin errores de compilación.
- Compilación de producción frontend: exitosa.
- Integración HTTP: 44 verificaciones reportadas por el agente, sin evidencia visible suficiente para corroborar una ejecución final completa.
- Navegador y despliegue Docker/Nginx/TLS: no verificados.

#### Limitaciones y trazabilidad metodológica

El informe registra los errores HTTP 400 `INVALID_ARGUMENT` experimentados durante la interacción con Gemini CLI y distingue estas incidencias de posibles defectos de la aplicación.

También documenta las modificaciones directas de código realizadas durante la estabilización de pruebas sin sincronización previa de las especificaciones, así como las diferencias entre las versiones y configuraciones registradas y el protocolo experimental.

Finalmente