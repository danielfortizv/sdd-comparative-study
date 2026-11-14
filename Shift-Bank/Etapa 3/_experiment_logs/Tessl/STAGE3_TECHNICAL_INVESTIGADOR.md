# Documentación técnica — Shift Bank E3 (Tessl)

## 1. Descripción general

Shift Bank es una aplicación bancaria simulada con backend FastAPI, frontend React/TypeScript y persistencia SQLite mediante SQLAlchemy.

La tercera etapa evoluciona el sistema de la Etapa 2, conservando consultas de cuentas, historial, transferencias internas, MFA, ACH, pagos recurrentes y límites de transferencia.

Sus cuatro extensiones principales son cifrado, auditoría, pruebas de carga y despliegue contenerizado.

## 2. Arquitectura

**Frontend:** React, TypeScript y Vite. Maneja la presentación, los formularios bancarios, la validación de entrada y el cifrado de los campos sensibles antes de determinadas solicitudes HTTP.

**Backend:** FastAPI y Python. Implementa contratos REST, reglas bancarias, comprobaciones MFA, cifrado y descifrado, migración de registros y escritura de auditoría.

**Persistencia:** SQLite y SQLAlchemy. Almacena cuentas, transacciones, beneficiarios, programaciones recurrentes y registros de auditoría.

**Infraestructura:** Docker Compose, Nginx como servidor del frontend y proxy inverso HTTPS, y un volumen persistente para SQLite.

## 3. Cifrado de información

El sistema utiliza un mecanismo criptográfico híbrido basado en RSA-OAEP-256 y AES-256-GCM.

El frontend solicita la clave pública mediante `GET /api/crypto/public-key` y utiliza Web Crypto API para cifrar campos bancarios sensibles antes de enviarlos al backend.

El backend descifra los campos necesarios para procesar las operaciones bancarias autorizadas. Por tanto, el diseño no corresponde a un esquema de cifrado extremo a extremo donde el servidor sea incapaz de acceder al texto claro; la interpretación válida es el contrato híbrido cliente-servidor aprobado durante la especificación.

Adicionalmente, los identificadores sensibles se cifran en reposo mediante AES-256-GCM y se implementó una migración de registros heredados con comprobación de integridad, rollback e idempotencia.

La clave de cifrado persistente debe conservarse entre reinicios. No se deben reemplazar claves de una base existente sin un procedimiento explícito de rotación y migración.

El formato serializado exacto de los campos cifrados debe verificarse contra `crypto_service.py` antes de utilizar ejemplos de bajo nivel, puesto que aparecieron representaciones distintas en documentos generados durante la ejecución.

## 4. Auditoría criptográfica

El sistema implementa un registro de auditoría sobre SQLite que utiliza encadenamiento SHA-256 y firmas HMAC-SHA256.

La implementación contempla:

- Registro de eventos bancarios y de seguridad.
- Validación de integridad de la cadena.
- Protección de registros frente a UPDATE y DELETE mediante triggers.
- Manejo transaccional para relacionar operaciones exitosas y sus eventos de auditoría.
- Registro de intentos fallidos mediante mecanismos de persistencia independientes.
- Protección administrativa del endpoint `GET /api/audit/verify` mediante la cabecera `X-Admin-Key`.

Las garantías de inmutabilidad deben entenderse dentro del modelo de amenazas definido. El encadenamiento criptográfico y los triggers no impiden todas las formas de manipulación por parte de un atacante con control total sobre la base de datos, las claves o el almacenamiento.

## 5. Pruebas de carga con Locust

El benchmark de E3 se ejecutó sobre FastAPI local con una base de datos SQLite sintética.

### Configuración

| Parámetro | Valor |
|---|---|
| Usuarios virtuales | 30 |
| Tasa de incorporación | 5 usuarios/s |
| Duración de calentamiento | Aproximadamente 6 s |
| Ventana estable | 60 s |
| Distribución configurada | 60 % saldo, 30 % historial, 10 % transferencias |
| Servidor de referencia | `http://127.0.0.1:8009` |

### Resultados

| Métrica | Medición |
|---|---:|
| Solicitudes | 1.792 |
| Lecturas agregadas | 1.597 |
| Transferencias | 195 |
| Throughput | 29,9 req/s |
| Latencia global p50 | 4 ms |
| Latencia global p95 | 9 ms |
| Latencia global p99 | 15 ms |
| Lecturas p95 | 11 ms |
| Transferencias p95 | 12 ms |
| Errores inesperados | 0 % |

Los objetivos de aceptación fueron p95 de lectura inferior a 200 ms, p95 de transferencias inferior a 500 ms y errores inesperados inferiores al 1 %. Los tres se cumplieron en la ejecución reportada.

La evidencia principal se encuentra en `backend/tests/load/load_benchmark_report.json`.

Los resultados corresponden al benchmark ejecutado, no a una medición de rendimiento de la infraestructura Docker ni a una prueba en un servicio bancario real.

## 6. Despliegue con Docker Compose

El entorno contiene dos servicios principales:

**Backend:** contenedor Python/FastAPI ejecutado como `appuser`, con persistencia de datos en un volumen Docker.

**Frontend:** contenedor Nginx ejecutado como usuario `nginx`, encargado de servir la aplicación compilada y actuar como proxy HTTPS para `/api`.

Los puertos internos 8080 y 8443 se publican externamente como 80 y 443, respectivamente.

Se exigen tres variables sensibles:

- `ENCRYPTION_KEY`
- `AUDIT_SECRET_KEY`
- `ADMIN_SECRET_KEY`

Deben configurarse antes de iniciar los contenedores. Los valores no deben almacenarse en el repositorio ni exponerse en informes.

La generación local de certificados de desarrollo se realiza mediante `nginx/generate_certs.py`. Los certificados autofirmados son apropiados únicamente para pruebas controladas; un despliegue público necesitaría certificados válidos y una configuración de seguridad adicional.

Se verificó la persistencia mediante reinicio de contenedores, conservación de beneficiarios y comprobación de integridad de auditoría.

## 7. Verificación automatizada

Desde la raíz del proyecto pueden ejecutarse las pruebas backend mediante:

`python -m pytest backend/tests -q`

Desde `frontend/`:

`npx vitest run`

`npm run build`

Para comprobar la configuración de Compose, una vez definidas las variables de entorno requeridas:

`docker compose config`

Para iniciar el despliegue:

`docker compose up --build -d`

Estos comandos presuponen que las dependencias y herramientas correspondientes están instaladas. Las pruebas deben utilizar una base independiente de cualquier archivo bancario histórico.

## 8. Resultados y limitaciones

La verificación final reportó 86 pruebas backend aprobadas, 39 pruebas frontend aprobadas y compilación exitosa.

La infraestructura también superó nueve pruebas de humo HTTPS con una base de datos aislada.

Los certificados de desarrollo no son aptos para producción. La auditoría posee garantías acotadas por su modelo de amenazas. Los resultados Locust están limitados a una configuración local concreta.

No se implementó ni verificó un pipeline completo de integración y despliegue continuo. No debe presentarse Docker Compose como equivalente a CI/CD.

Este documento describe el estado experimental final de la Etapa 3, sin certificar que el sistema sea apto para operar como una plataforma bancaria real.