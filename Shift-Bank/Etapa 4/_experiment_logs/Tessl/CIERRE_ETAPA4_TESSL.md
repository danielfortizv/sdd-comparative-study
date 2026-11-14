# Informe de Cierre de Investigación — Etapa 4 (Tessl)
**Caso de estudio:** Shift Bank  
**Metodología:** Desarrollo Guiado por Especificaciones (Spec-Driven Development — SDD)  
**Herramienta / Plugin SDD:** Tessl (`tessl-labs/spec-driven-development` v2.0.1)  
**Entorno de ejecución:** Gemini CLI v0.65.0 / Node.js v20.17.0 / Python 3.13.2 / Windows 11  
**Fecha de cierre:** 14 de noviembre de 2026  
**Clasificación final del experimento:** **CERRADO CON LIMITACIONES DOCUMENTADAS** (*CLOSED WITH DOCUMENTED LIMITATIONS*)

---

## 1. Resumen de la Implementación Final de la Etapa 4

La Etapa 4 de Shift Bank tuvo como objetivo transformar la arquitectura financiera heredada de la Etapa 3 hacia un sistema bancario multimoneda gobernado por **Event Sourcing** y **CQRS**, preservando la integridad de los contratos financieros, las políticas de seguridad y la auditabilidad transaccional.

A través de catorce decisiones formales de arquitectura y negocio (D-01 a D-14), se implementaron los siguientes componentes estructurales:

1. **Cuentas Multimoneda y Partición Estricta (D-01, D-02):**
   - Soporte para cuentas denominadas en USD, EUR y GBP (`CHK-1001` USD, `SAV-2001` USD, `EUR-3001` EUR, `GBP-4001` GBP).
   - Aislamiento estricto de balances por moneda, impidiendo la agregación física directa o la mezcla de saldos de diferentes divisas.
   - Provisión determinista e idempotente de cuentas adicionales durante la inicialización del sistema.

2. **Aritmética Financiera Exacta (D-03):**
   - Erradicación del uso de números de punto flotante (`float`, `Number`, `parseFloat`, `toFixed`) en cálculos monetarios.
   - En el backend: uso exclusivo de la clase `Decimal` de Python, serialización en respuestas JSON como cadenas decimales canónicas (`"2500.00"`), y persistencia de precisión extendida mediante el tipo SQLAlchemy `SqliteExactDecimal`.
   - En el frontend: implementación de la biblioteca utilitaria `monetary.ts`, basada en cadenas decimales y aritmética entera con `BigInt` a nivel de unidades menores (centavos), garantizando exactitud absoluta en acumulaciones y comparaciones.

3. **Conversión de Divisas y Tasas Racionales (D-03, D-04):**
   - Endpoint dedicado independiente `POST /api/conversions` separado de las transferencias internas.
   - Aplicación de tipos de cambio racionales fijos simulados (1 USD = 0.90 EUR [fracción 9/10], 1 USD = 0.80 GBP [fracción 4/5]).
   - Conversión mediante multiplicación racional exacta y redondeo simétrico `ROUND_HALF_UP` aplicado estrictamente una sola vez sobre el importe destino.
   - Trazabilidad completa registrando moneda de origen, moneda de destino, importe original, tasa de cambio y residuo de redondeo.

4. **Event Sourcing como Fuente de Verdad Monetaria (D-05, D-09):**
   - Tabla append-only `domain_events` en SQLite como registro inmutable e irrevocable de acontecimientos financieros.
   - Representación atómica de transacciones: cada transferencia interna o conversión exitosa se almacena como una unidad indivisible (`InternalTransferCompleted`, `CurrencyConversionCompleted`).
   - Migración segura del estado previo mediante eventos `AccountStateImported` y `LegacyTransactionImported`, preservando balances históricos sin inventar transacciones ficticias.

5. **Arquitectura CQRS y Consistencia Inmediata (D-06):**
   - Separación estricta entre modelos de comando (procesadores de transacciones y almacén de eventos) y modelos de consulta (proyecciones de lectura `accounts` y `transactions`).
   - Actualización transaccional síncrona: la persistencia del evento de dominio y la actualización de las proyecciones ocurren dentro de la misma transacción atómica de base de datos.
   - Control de avance mediante la tabla `projection_checkpoints` y herramienta administrativa local de verificación y reconstrucción determinista (`rebuild_projections.py`, `verify_or_rebuild_at_startup`).

6. **Transferencias ACH y Mecanismos de Reembolso (D-08, D-09):**
   - Operaciones ACH restringidas exclusivamente a cuentas USD, validando números de ruta y cuenta bancaria.
   - Ciclo de vida asíncrono simulado: inicio (`pending` con débito inmediato), liquidación (`settled` sin débito adicional) y rechazo/fallo (`failed` con reembolso exacto e incremento de versión desacoplado).

7. **Pagos Recurrentes Idempotentes y Concurrencia (D-08, D-09, D-12):**
   - Programación de transferencias intra-moneda con frecuencias diaria, semanal y mensual.
   - Procesamiento protegido contra duplicados mediante claves deterministas (`schedule_id + execution_date`) y cerrojos transaccionales de escritura (`BEGIN IMMEDIATE` en SQLite).

8. **Límites Financieros y Autenticación Multifactor (MFA) Multimoneda (D-07):**
   - Normalización de importes a su equivalente en USD mediante tipos racionales para evaluar límites dinámicos (límite transaccional de $5,000.00 USD y diario de $10,000.00 USD).
   - Umbral de seguridad MFA fijado en $1,000.00 USD equivalente: importes $\le 1000.00$ no requieren PIN; importes $> 1000.00$ exigen PIN de 4 dígitos (código HTTP 428 Precondition Required).
   - Política de bloqueo tras 3 intentos fallidos consecutivos (código HTTP 423 Locked).

9. **Auditoría Criptográfica Inmutable (D-11):**
   - Registro de auditoría independiente (`audit_ledger`) protegido mediante encadenamiento HMAC-SHA256 y firma criptográfica.
   - Políticas fail-closed que impiden operaciones monetarias ante fallos en el subsistema de auditoría.

10. **Idempotencia (D-13) y Concurrencia Optimista (D-14):**
    - Encabezado obligatorio `Idempotency-Key` (UUIDv4) para todas las operaciones monetarias.
    - Respuestas cacheadas devueltas ante reintentos idénticos; rechazo con código `IDEMPOTENCY_KEY_REUSE` (HTTP 409) ante solicitudes que reutilicen la clave con parámetros divergentes.
    - Control de concurrencia optimista mediante versiones de cuenta (`version`, `expected_from_version`, `expected_to_version`), rechazando solicitudes obsoletas con código `ACCOUNT_VERSION_CONFLICT` (HTTP 409).
    - Prioridad de la idempotencia: la consulta de claves idempotentes precede a la validación de versiones de cuenta, garantizando que reintentos legítimos recuperen la respuesta original.

---

## 2. Resultados Automatizados Verificados (Línea Base)

La suite de pruebas automatizadas del proyecto Shift Bank en la Etapa 4 se encuentra en estado 100 % satisfactorio:

| Componente | Métrica / Comando | Resultado | Estado |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Integration** | `python -m pytest backend/tests -v` | **136 passed**, 3 warnings in 8.92s | **APROBADO** |
| **Frontend Test Suite** | `npm run test` (Vitest v1.6.1) | **136 passed** across 11 suites (11 files) in 2.97s | **APROBADO** |
| **Tipado Estático (TypeScript)** | `tsc` (TypeScript v5.4.5) | **0 errores** | **APROBADO** |
| **Compilación de Producción** | `npm run build` (Vite v5.4.21) | Bundle generado exitosamente en `dist/` | **APROBADO** |

### Distribución de suites de prueba
- **Backend (136 pruebas):**
  - Cuentas y persistencia: `test_accounts.py`
  - Transferencias ACH y liquidación: `test_ach_transfers.py`
  - Auditoría criptográfica HMAC: `test_audit_log.py`
  - Conversión multimoneda y FX: `test_currency_conversion.py`
  - Configuración y Docker: `test_deployment_config.py`
  - Cifrado en reposo AES-GCM: `test_encryption.py`
  - Event Sourcing y CQRS: `test_event_sourcing_cqrs.py`
  - Idempotencia D-13: `test_idempotency_d13.py`
  - Autenticación MFA y bloqueos: `test_mfa.py`
  - Precisión monetaria D-03: `test_monetary_precision_d03.py`
  - Pagos recurrentes y planificador: `test_recurring_payments.py`
  - Historial y proyecciones: `test_transactions.py`
  - Límites de transferencia: `test_transfer_limits.py`
  - Transferencias internas y concurrencia: `test_transfers.py`
- **Frontend (136 pruebas en 11 archivos):**
  - `AccountSummary.test.tsx` (10 pruebas)
  - `ConversionModal.test.tsx` (11 pruebas)
  - `crypto.test.ts` (4 pruebas)
  - `ErrorParsing.test.ts` (7 pruebas)
  - `IdempotencyLifecycle.test.tsx` (10 pruebas)
  - `MfaModal.test.tsx` (8 pruebas)
  - `monetary.test.ts` (38 pruebas)
  - `RecurringPayments.test.tsx` (11 pruebas)
  - `TransactionHistory.test.tsx` (13 pruebas)
  - `TransferLimits.test.tsx` (8 pruebas)
  - `TransferModal.test.tsx` (16 pruebas)

---

## 3. Resultados de Integración en Vivo y Distinción Metodológica

Para evaluar el funcionamiento integrado del sistema más allá de pruebas aisladas con mocks, se diseñó e implementó un arnés de verificación HTTP en vivo (`scripts/verify_live_e2e.py`), ejecutado contra instancias reales de FastAPI (puerto 8000) y Vite dev server (puerto 5173), operando sobre una base de datos SQLite aislada y temporal (`%TEMP%/e2e_isolated.db`).

### Declaración de Verificaciones Reportadas por el Agente
El agente ejecutó iteraciones de verificación que abarcaron 44 escenarios contractuales:
- **Cuentas y Dashboard (2.A.1 - 2.A.8):** Carga correcta de cuentas semilla (USD, EUR, GBP), saldos decimales canónicos, versiones enteras, aislamiento de divisas y reenvío transparente por el proxy de Vite.
- **Transferencias Internas (2.B.1 - 2.B.5):** Transferencia intra-moneda exitosa con actualización de saldos/versiones, emisión de evento `InternalTransferCompleted`, rechazo de transferencias cross-currency (HTTP 400).
- **Conversión de Divisas (2.C.1 - 2.C.4):** Ejecución a través de `/api/conversions`, aplicación exacta de tasa 0.90, débito en USD y crédito en EUR, generación de evento `CurrencyConversionCompleted`.
- **Transferencias ACH (2.D.1 - 2.D.6):** Estado inicial `pending`, débito único, rechazo de cuentas no USD, liquidación mediante endpoint administrativo sin duplicación de débito.
- **Pagos Recurrentes (2.E.1 - 2.E.7):** Creación de calendario, ejecución puntual de ocurrencia vencida, no duplicación de cobro en ciclos subsiguientes del planificador, operaciones de pausa y reanudación.
- **MFA y Límites (2.F.1 - 2.F.8):** Operación exacta de $1,000.00 sin requerimiento de PIN; requerimiento estricto (HTTP 428) para importes superiores; autenticación exitosa con PIN correcto; incremento de intentos fallidos, bloqueo tras 3 intentos (HTTP 423) y rechazo de montos que superan el límite transaccional (HTTP 400).
- **Idempotencia y Concurrencia (2.G.1 - 2.G.7):** Replay de solicitud idéntica sin efectos secundarios; detección de conflicto por reutilización de clave con parámetros alterados (`IDEMPOTENCY_KEY_REUSE`, HTTP 409); rechazo de versiones desactualizadas (`ACCOUNT_VERSION_CONFLICT`, HTTP 409); precedencia de la recuperación idempotente sobre la validación de versiones.
- **Contratos de Error Frontend (2.H.1 - 2.H.5):** Mapeo de errores estructurados en `ApiError`, ausencia de falsos positivos en 409 no identificados, y documentación de heurísticas de texto.
- **Verificación Frontend (3.1 - 3.4):** Servido de HTML en puerto 5173, carga de cuentas y transacciones en vivo vía proxy.
- **Integridad Financiera y Event Sourcing (4.1 - 4.12):** Verificación directa de saldos en base de datos, correspondencia de checkpoints CQRS con el último evento de dominio, firma de registros en el log de auditoría HMAC, ciclo de fallo y reembolso ACH idempotente, y verificación al 100 % de proyecciones mediante `verify_or_rebuild_at_startup`.

### Distinción Metodológica Fundamental
De acuerdo con las directrices de investigación:
1. **Resultado Reportado vs. Corroborado:** En las capturas de consola disponibles, las primeras ejecuciones del script registraron excepciones derivadas de discrepancias en expectativas del arnés de prueba (códigos HTTP 200 vs 201 en FastAPI, nombres de atributos de Pydantic como `source_amount`, y parsing de HTML no JSON). Aunque el código de prueba fue corregido para alinearse estrictamente a los contratos reales de la aplicación, la transcripción de ejecución completa y limpia que certifique la salida final ininterrumpida de las 44 pruebas no quedó reflejada en la consola interactiva previa. Por tanto, este reporte distingue formalmente las **44 comprobaciones reportadas por el agente** de la evidencia de pruebas unitarias/integración **independientemente corroboradas** (136 backend, 136 frontend).
2. **Exclusión de Pruebas E2E en Navegador:** No se encontraban instaladas herramientas de automatización de navegador web (Playwright, Puppeteer o Cypress). **No se afirma ni se reclama haber realizado pruebas automatizadas de extremo a extremo en navegador.** Se provee una lista de comprobación manual para su eventual ejecución por parte del investigador.

---

## 4. Aspectos No Verificados y Limitaciones del Sistema

En estricta observancia del rigor académico, se declaran los siguientes aspectos que **no** cuentan con evidencia empírica de verificación en tiempo de ejecución:

1. **Pruebas de Interfaz en Navegador Real (UI E2E):** Los recorridos de usuario interactivos (clics en modales de transferencia, introducción visual del PIN en pantalla, alternancia de pestañas) no fueron ejecutados a través de controladores de navegador automatizados.
2. **Despliegue y Orquestación con Docker Compose:** El archivo `docker-compose.yml`, los Dockerfiles de backend y frontend, y las redes virtuales asociadas no fueron levantados ni probados en vivo durante la presente etapa.
3. **Proxy Inverso Nginx y Cifrado TLS:** El contenedor Nginx, la configuración de proxy inverso (`nginx.conf`) y los certificados autofirmados generados mediante `generate_certs.py` no fueron validados con tráfico HTTPS real.
4. **Persistencia de Volúmenes en Contenedores:** No se ejecutaron pruebas de parada forzada, desmontaje y recreación de contenedores Docker para validar la supervivencia de los archivos SQLite en volúmenes persistentes.
5. **Carga y Rendimiento en Red Real:** No se realizaron pruebas de carga masiva concurrente con Locust bajo la arquitectura Event Sourcing en la Etapa 4 (quedando limitadas a los ensayos de integración secuencial y multihilo en SQLite local).

---

## 5. Incidencias Técnicas de la Plataforma Gemini CLI

Durante las sesiones de trabajo se registraron dos incidentes de comunicación entre Gemini CLI y la API del modelo subyacente:
- **Incidente de llamadas a herramientas (HTTP 400 INVALID_ARGUMENT):** Durante las interacciones 21 y 45 se presentaron errores reiterados con el mensaje `INVALID_ARGUMENT`, señalando discrepancias en el protocolo de invocación de herramientas (`function response count mismatch` o respuestas interrumpidas).
- **Diagnóstico y Clasificación:** Este comportamiento corresponde a fallos de sincronización y transporte en la capa CLI/API/agente y **no** a defectos de lógica o fallos funcionales de la aplicación Shift Bank.
- **Impacto Metodológico:** Provocó la interrupción de sesiones y obligó al investigador a reanudar el flujo en sesiones limpias, segmentando el historial conversacional y requiriendo reconstruir la orientación operativa del agente.

---

## 6. Trazabilidad Metodológica y Desviaciones del Protocolo SDD

### Versiones Registradas vs. Prescritas
- **Gemini CLI:** Versión registrada en el entorno: `0.65.0`.
- **Tessl CLI y Plugins:** Versión CLI `0.118.1`, con el plugin vendoreado `tessl-labs/spec-driven-development` versión `2.0.1`.
- **Entorno de Ejecución:** Node.js `v20.17.0`, Python `3.13.2`, Windows 11 (`win32`).
- **Modelos:** Se registraron trazas de invocación de familias Gemini (e.g. `gemini-2.5-pro` / `gemini-3.8-flash` / `gemini-3-flash-preview`), sujetas a la configuración del entorno de pruebas.

### Desviaciones del Protocolo "Specification-First"
El protocolo metodológico de Tessl establece que toda modificación funcional debe partir de la actualización formal de las especificaciones (`specs/*.spec.md`) utilizando la habilidad `spec-writer`, seguida de la verificación con `spec-verification`, antes de modificar el código fuente.

**Desviación Documentada:**
Durante las interacciones 18 a 35 (resolución de incompatibilidades en pruebas heredadas, ajuste de serializadores de precisión monetaria D-03, restauración de obligatoriedad de versiones D-14, y fortalecimiento de excepciones en transferencias), el agente implementó cambios directos sobre modelos SQLAlchemy, esquemas Pydantic, servicios financieros y archivos de prueba sin actualizar previamente de forma sincronizada los archivos `.spec.md`. Aunque las especificaciones habían sido creadas y refinadas exhaustivamente en las interacciones 15 a 17, el desarrollo iterativo de estabilización operó con modificaciones directas en el código. Esta desviación se documenta como un hallazgo relevante sobre la dificultad de mantener el flujo estricto "Spec-First" durante fases intensivas de depuración y corrección de regresiones.

---

## 7. Reproducibilidad y Estado de Control de Versiones (Git)

### Inspección del Estado de Git
La inspección realizada mediante `git status` evidenció que:
1. El directorio de trabajo de la Etapa 4 (`Shift-Bank/Etapa 4/Tessl/`) y su directorio hermano de evidencias (`Shift-Bank/Etapa 4/_experiment_logs/`) se encuentran en estado **Untracked** (`??`) en el repositorio Git principal (`origin/ShiftBank`).
2. Existen modificaciones residuales sin confirmar en el directorio de la Etapa 3 (`Shift-Bank/Etapa 3/Tessl/`).
3. En observancia estricta del mandato de seguridad y preservación, el agente **no ejecutó ni ejecutará `git add`, `git commit` ni `git push`** de forma desatendida.

### Inventario de Carpetas y Evidencias para Versionado Previo a Entrega
Para garantizar la plena reproducibilidad experimental, el investigador deberá incorporar al control de versiones las siguientes rutas:
- `Shift-Bank/Etapa 4/Tessl/backend/` (código fuente, modelos, servicios, migraciones y 136 pruebas pytest).
- `Shift-Bank/Etapa 4/Tessl/frontend/` (aplicación React, componentes, utilidades monetarias, tipos y 136 pruebas Vitest).
- `Shift-Bank/Etapa 4/Tessl/specs/` (13 especificaciones `.spec.md` gobernadas por Tessl).
- `Shift-Bank/Etapa 4/Tessl/scripts/` (arnés de verificación HTTP en vivo `verify_live_e2e.py`).
- `Shift-Bank/Etapa 4/Tessl/.tessl/`, `.agents/`, `.codex/`, `.github/`, `.vscode/` (metadatos y junctions de integración SDD de Tessl).
- `Shift-Bank/Etapa 4/_experiment_logs/Tessl/` (manifiestos de preparación, SHA-256, metadata JSON, log de interacción `Interaccion.md` y este informe de cierre `CIERRE_ETAPA4_TESSL.md`).

---

## 8. Conclusión Académica Final

### Logros Comprobados
La experimentación de la Etapa 4 de Shift Bank empleando la metodología y herramientas de **Tessl** demostró la viabilidad de acometer una reestructuración arquitectónica de alta complejidad sobre un sistema financiero preexistente. Se transformó un modelo monolítico relacional de saldo mutable en una arquitectura desacoplada basada en **Event Sourcing** y **CQRS**, introduciendo soporte multimoneda, aritmética decimal exacta, idempotencia estricta y concurrencia optimista, alcanzando una tasa de éxito del 100 % en las suites automatizadas de backend (136/136) y frontend (136/136).

### Limitaciones Objetivas
La experiencia evidenció fricciones metodológicas en el mantenimiento continuo del ciclo "Spec-First" durante la resolución de regresiones heredadas, así como dependencias de transporte en el agente CLI que provocaron interrupciones operativas. Adicionalmente, el alcance de la validación se concentró a nivel de contratos de integración, APIs y pruebas automatizadas, dejando fuera de comprobación empírica el despliegue de contenedores, la terminación TLS y los recorridos de usuario interactivos en navegadores reales.

### Dictamen de Cierre
El proyecto Shift Bank — Etapa 4 con Tessl se declara formalmente:

> **CERRADO CON LIMITACIONES DOCUMENTADAS**  
> (*CLOSED WITH DOCUMENTED LIMITATIONS*)

Este cierre experimental certifica la culminación de la fase investigativa y el congelamiento del código y las evidencias bajo los términos aquí expuestos, distinguiéndose de manera explícita de una certificación de preparación para despliegue en entornos de producción.
