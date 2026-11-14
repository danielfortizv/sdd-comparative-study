# 9.4.4 Caso de Estudio 3.4: Sistema Bancario — Tessl

## Dimensión A: Esfuerzo Computacional y Costos

En la tercera etapa del caso de estudio Shift Bank se utilizó Tessl como herramienta de Spec-Driven Development y Gemini CLI como agente para evolucionar un sistema bancario simulado desarrollado previamente. El alcance comprendió cuatro capacidades: cifrado de información sensible, auditoría criptográfica, pruebas de carga y despliegue de la aplicación.

El desarrollo siguió un proceso de especificación, aprobación humana, implementación incremental, verificación y corrección. Durante la ejecución se documentaron decisiones técnicas y hallazgos que requirieron nuevas instrucciones al agente, especialmente en seguridad criptográfica, consistencia transaccional, concurrencia y aislamiento de pruebas.

Las métricas de consumo de tokens, llamadas a herramientas y tiempo deben consolidarse a partir de las sesiones originales de Gemini CLI correspondientes exclusivamente a esta etapa. Las entradas de la bitácora no sustituyen las interacciones registradas por el agente y las estadísticas de sesiones diferentes no deben combinarse sin comprobar su procedencia.

Este caso permite estudiar no solamente el costo de generar código, sino también el esfuerzo invertido en revisar requisitos, detectar defectos y solicitar correcciones posteriores.

## Dimensión B: Calidad de los Pipelines Generados

En esta etapa se implementaron procedimientos reproducibles de pruebas automatizadas, medición de rendimiento mediante Locust, análisis estático con SonarQube y verificación de un despliegue Docker Compose. No obstante, estos procedimientos no constituyen evidencia de un pipeline CI/CD completo, dado que no se demostró una orquestación automatizada de integración y entrega continua.

La implementación final superó 125 pruebas automatizadas: 86 de backend y 39 de frontend. El benchmark Locust se ejecutó con 30 usuarios virtuales, una ventana estable de 60 segundos y 1.792 solicitudes procesadas sin errores inesperados. La latencia p95 registrada fue de 11 ms para lecturas y 12 ms para transferencias, cumpliendo los umbrales definidos para el entorno local experimental.

La evaluación estática identificó inicialmente 12 bugs, 2 vulnerabilidades y 71 code smells. Tras las intervenciones correctivas, el análisis final reportó cero bugs, cero vulnerabilidades y 72 code smells.

Aunque se eliminaron los hallazgos de fiabilidad y seguridad detectados inicialmente, la deuda técnica aumentó de 450 a 491 minutos y la complejidad cognitiva de 585 a 624. Esto evidencia que la remediación de defectos específicos no produce necesariamente una mejora simultánea en todas las dimensiones de calidad.

La cobertura global final de SonarQube fue del 77,9 %, mientras que la cobertura del código nuevo alcanzó 70,6 %. El Quality Gate terminó en estado ERROR por no alcanzar el umbral del 80 % sobre código nuevo y por mantener una nueva incidencia de mantenibilidad. El estado inicial OK no es directamente comparable, ya que inicialmente no se aplicaban las mismas condiciones de calidad.

## Dimensión C: Especificación de Infraestructura

Tessl permitió estructurar el diseño de una arquitectura compuesta por frontend React/TypeScript, backend FastAPI, almacenamiento SQLite y servicios desplegados mediante Docker Compose.

El cifrado incorporó RSA-OAEP y AES-256-GCM, tanto para proteger campos sensibles transmitidos por el frontend como para almacenar identificadores bancarios cifrados. El registro de auditoría utilizó firmas HMAC-SHA256 y encadenamiento criptográfico con persistencia transaccional.

La implementación de auditoría presentó dificultades de integración con SQLite, particularmente por la necesidad de distinguir operaciones de lectura y escritura y conservar la atomicidad de operaciones que requerían MFA. La revisión humana permitió identificar problemas que las primeras pruebas automatizadas no habían detectado.

El despliegue final incorporó Nginx con HTTPS, usuarios de contenedor sin privilegios root, configuración obligatoria de secretos y almacenamiento persistente. La validación operacional comprobó nueve escenarios, incluyendo el reinicio de contenedores y la integridad posterior del registro de auditoría.

Se contabilizaron 11 archivos de especificación `.spec.md`, con 1.093 líneas físicas. La proporción entre líneas de código y líneas de especificación fue aproximadamente 5,06. El total de requisitos atómicos queda pendiente de reconciliar, dado que durante el proceso se utilizaron distintos criterios de conteo documental.

En conjunto, el experimento evidencia la capacidad de Tessl para estructurar la evolución de un sistema existente y orientar a un agente de programación hacia funcionalidades de mayor complejidad arquitectónica. Al mismo tiempo, demuestra la importancia de la evaluación humana para garantizar consistencia funcional, seguridad, reproducibilidad y calidad documental.

Los resultados corresponden al alcance aprobado del prototipo bancario y no pueden extrapolarse directamente a sistemas financieros reales ni utilizarse como certificación de seguridad productiva.