# Shift Bank Stage 2 - Spec Kit: Auditoria Experimental y Registro de Pendientes de Medicion

**Documento:** E2_SPECKIT_PENDIENTES_MEDICION.md
**Destino:** Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_PENDIENTES_MEDICION.md
**Referencia Metodologica:** SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md (Secciones 8 y 9) y Matriz de Dimensiones Experimentales
**Fecha de Auditoria:** 2026-11-14
**Herramienta y Entorno:** GitHub Spec Kit v1.0.6 sobre Gemini CLI v0.65.0
**Modelo Real en Transcripcion:** gemini-3.8-flash (Configurado en entorno: gemini-3.5-flash)
**Estado:** AUDITORIA COMPLETADA - METRICAS VERIFICADAS Y GAPS CATALOGADOS

---

## 1. Resumen Ejecutivo de la Auditoria

Esta auditoria revisa la evidencia empirica generada durante el desarrollo de **Shift Bank Stage 2 (Spec Kit)** frente a las Secciones 8 y 9 del marco comparativo comun y los registros originales de Gemini CLI (session-2026-11-14T17-18-f52d4c11.jsonl y session-2026-11-14T18-24-fe272589.jsonl).

### Hallazgos Principales:
1. **Resolucion de la Anomalia de 5.213 Llamadas a Herramientas:**
   El recuento inicial de 5.213 llamadas a herramientas y ~236M tokens de entrada fue causado por un analisis plano de las lineas JSONL de Gemini CLI sin deduplicacion. Al registrar snapshots incrementales de la conversacion a lo largo del streaming, cada turno previo se re-acumulaba en las lineas subsiguientes (amplificacion de ~10,7x en herramientas y ~1,9x en tokens).
   **Telemetria real deduplicada:** **485 llamadas a herramientas unicas** (520 respuestas registradas), **521 solicitudes al modelo**, **123.950.969 tokens de entrada totales** (con un 87,83% de acierto en cache contextual), **335.430 tokens de salida**, **225.992 tokens de razonamiento** y **4 h 55 min 34 s de tiempo transcurrido (wall clock)**.
2. **Taxonomia de Errores Rigurosa:**
   Se diferenciaron con precision los **errores de ejecucion de herramientas** (10 fallos de sandbox/inspeccion, 97,94% de exito de herramientas), los **comandos con codigo de salida distinto de cero** (21 comandos), los **fallos intermedios de pruebas automatizadas en ciclo TDD** (rapidamente subsanados) y los **errores/timeouts de API** (1 timeout transitorio en S1 turno 13).
3. **Identificacion de 4 Vacios de Medicion Criticos (Gaps):**
   - **Analisis SonarQube:** Ausente tanto en linea base como final (PENDIENTE).
   - **Inventario SHA-256 Final y Diff LOC:** Ausente (PENDIENTE).
   - **Metricas de Archivos y Lineas de Especificacion:** Medidas con exactitud en esta auditoria: **8 archivos**, **1.640 lineas**.
   - **Validacion Manual de Escenarios A01-A21:** La suite automatizada cubre el 100% de los escenarios en sandbox (pytest y itest), pero **no sustituye la validacion manual interactiva en navegador** requerida por A21 (PENDIENTE).

---
## 2. Auditoria de Telemetria: Investigacion de la Anomalia de 5.213 Herramientas

### 2.1. Causa Raiz de la Sobrecarga en el Conteo Inicial
En los registros JSONL de Gemini CLI (.gemini/tmp/spec-kit-1/chats/session-*.jsonl), el motor CLI emite multiples lineas de snapshot por cada turno de conversacion para persistir el historial, el streaming de pensamientos y los bloques de estado.
- Un bucle ingenuo que itera sobre todas las lineas del archivo JSONL suma el contenido de turnos anteriores repetidamente cada vez que se emite un nuevo evento.
- **Factor de repeticion observado:** ~10,74x en llamadas a herramientas y ~1,91x en tokens.

### 2.2. Telemetria Real Deduplicada por Identificador Unico de Evento

| Dimension de Telemetria | Sesion 01 (Descubrimiento, Spec y Plan) | Sesion 02 (Remediacion e Implementacion) | Total Consolidado Real | Conteo Bruto Inicial (Con Duplicados de Snapshot) |
|---|---|---|---|---|
| **Identificador de Sesion** | 52d4c11-3f33-4667-8b68-f76b443d510d | e272589-bd7f-4c7d-8205-4f821865bbc9 | **2 sesiones** | 2 sesiones |
| **Modelo Principal Real** | gemini-3.8-flash | gemini-3.8-flash | **gemini-3.8-flash** | gemini-3.8-flash |
| **Interacciones Humanas (Prompts)** | 15 mensajes | 10 mensajes | **25 mensajes** | 25 mensajes |
| **Solicitudes API al Modelo (Turnos)** | 109 turnos | 412 turnos | **521 solicitudes** | 972 lineas brutas |
| **Tokens Entrada (con Cache)** | 15.033.790 | 108.917.179 | **123.950.969** | 236.439.047 |
| **Tokens Cache Leidos** | 13.980.169 | 94.887.922 | **108.868.091** | 208.019.589 |
| **Tokens Entrada No Cacheados** | 1.053.621 | 14.029.257 | **15.082.878** | 28.419.458 |
| **Tasa de Acierto en Cache** | 92,99 % | 87,12 % | **87,83 %** | 87,98 % |
| **Tokens Salida Generados** | 117.188 | 218.242 | **335.430** | 600.788 |
| **Tokens Pensamiento (Thoughts)** | 60.710 | 165.282 | **225.992** | 417.652 |
| **Llamadas a Herramientas Unicas** | 83 llamadas | 402 llamadas | **485 llamadas** | 5.213 acumuladas |
| **Respuestas de Herramientas Unicas**| 106 respuestas | 414 respuestas | **520 respuestas** | - |
| **Errores de Ejecucion de Herramienta** | 5 fallos | 5 fallos | **10 errores** | Declarado 0 (sin distinguir) |
| **Tasa de Exito de Herramientas** | 93,98 % | 98,76 % | **97,94 %** | - |
| **Inicio Wall Clock (UTC)** | 2026-11-14T17:18:20.286Z | 2026-11-14T18:24:30.998Z | - | - |
| **Fin Wall Clock (UTC)** | 2026-11-14T18:22:56.126Z | 2026-11-14T22:15:29.467Z | - | - |
| **Duracion Transcurrida (Wall Time)** | 1 h 04 min 36 s (3.876 s)| 3 h 50 min 58 s (13.858 s)| **4 h 55 min 34 s (17.734 s)** | 4 h 55 min 34 s |
| **Costo Monetario Estimado** | **N/A** | **N/A** | **N/A** | **N/A** |

### 2.3. Distribucion Real de Llamadas por Herramienta (485 llamadas unicas)
- 
ead_file: **199** invocaciones (S1: 39, S2: 160) - Lectura quirurgica de codigo heredado, especificaciones y contratos.
- 
un_shell_command: **139** invocaciones (S1: 21, S2: 118) - Ejecucion de pruebas unitarias, compilacion, verificacion de base de datos y scripts de prerequisitos.
- 
eplace: **66** invocaciones (S1: 0, S2: 66) - Ediciones dirigidas sobre codigo fuente, componentes React y hojas de estilo.
- write_file: **33** invocaciones (S1: 14, S2: 19) - Creacion de nuevas especificaciones, servicios (services.py, scheduler.py) y modulos de prueba.
- update_topic: **26** invocaciones (S1: 4, S2: 22) - Gestion de capitulos y sincronizacion del plan de trabajo.
- grep_search: **11** invocaciones (S1: 3, S2: 8) - Busqueda de patrones arquitectonicos, decimales e invariantes.
- glob: **5** invocaciones (S1: 0, S2: 5) - Mapeo de rutas y descubrimiento de artefactos.
- list_directory: **6** invocaciones (S1: 2, S2: 4) - Inspeccion de estructura de carpetas.

---
## 3. Taxonomia y Distincion de Errores

Para evitar clasificaciones erroneas, se categorizan estrictamente los eventos anomalos registrados en los logs:

### 3.1. Errores de Ejecucion de Herramienta (Nivel Agente / Sandbox) - Total: 10
Eventos donde la invocacion de la herramienta fue rechazada por la infraestructura de seguridad del agente o fallo por precondicion intrinseca de la herramienta:
1. 
ead_file (S1): Rechazado por limite de sandbox al intentar leer ../SEED-2.md fuera del espacio de trabajo.
2. 
ead_file (S1): Rechazado por limite de sandbox al intentar leer ../E2_COMMON_FUNCTIONAL_CONTRACT.md.
3. 
ead_file (S1): Rechazado al intentar acceder a archivo ignorado .specify/feature.json.
4. update_topic (S1): Caida transitoria Response was lost or interrupted.
5. write_file (S1): Caida transitoria Response was lost or interrupted.
6. glob (S2): Rechazado por limite de sandbox al intentar buscar en carpeta superior ../.
7. 
eplace (S2): Fallo de coincidencia exacta de old_string en specs/002-shift-bank-stage2/plan.md.
8. 
eplace (S2): Reintento con desfase de contexto en plan.md.
9. 
eplace (S2): Tercer intento de reemplazo en plan.md (resuelto releyendo el fragmento antes de editar).
10. 
ead_file (S2): Rechazado por limite de sandbox al intentar leer ../_experiment_logs/.../E2_SPECKIT_REGISTRO_01_PREPARACION.md.

### 3.2. Comandos con Codigo de Salida Distinto de Cero (Exit Code != 0) - Total: 21
La herramienta 
un_shell_command funciono correctamente capturando la salida, pero el proceso ejecutado en PowerShell retorno un codigo de error:
- **Sesion 1 (2 comandos):**
  - Error de sintaxis en comando de una linea en Python al inspeccionar SQLite.
  - Invocacion de pwsh (PowerShell Core) no instalado en el sistema operativo Windows nativo (se corrigio usando powershell.exe).
- **Sesion 2 (19 comandos):**
  - Deteccion de inyeccion/sustitucion de comandos bloqueada por seguridad interna del agente en expresiones $().
  - Fallo de prueba intermedia en 	est_stage2_regression.py por falta de importacion de 	imedelta (resuelto inmediatamente).
  - Verificaciones intermedias de diff y filtros de salida vacios con codigo 1.

### 3.3. Fallos Intermedios de Pruebas Automatizadas (Ciclo TDD)
- **Backend:** En T042, la primera ejecucion de 	est_stage2_regression.py fallo 1 de 5 pruebas por NameError: name 'timedelta' is not defined. Tras anadir la importacion, paso 5/5 (y posteriormente 6/6 con el test de scheduler lifespan).
- **Frontend:** En T036/T040, las pruebas iniciales de la tabla de pagos recurrentes fallaron temporalmente antes de sincronizar el estado del modal compartido de MFA. Tras el cableado, Vitest paso 12/12.

### 3.4. Errores de API / Red
- **1 interrupcion de API en S1 turno 13:** Provoco la reconexion con el prompt 'Continue the Stage 2 documentation remediation interrupted by API errors'.

---
## 4. Estado de los Gaps de Medicion (Secciones 8 y 9)

`
+-----------------------------------------------------------------------------------------------+
| MATRIZ DE GAPS DE MEDICION: REQUISITO VS. EVIDENCIA DISPONIBLE                                |
+------------------------------------+--------------------------+---------------+---------------+
| Elemento Metodologico              | Requisito Guia           | Estado Actual | Clasificacion |
+------------------------------------+--------------------------+---------------+---------------+
| 1. SonarQube Linea Base (E1)       | Quality Gate, NCLOC, MQR | NO EJECUTADO  | PENDIENTE     |
| 2. SonarQube Final (E2)            | Issues, Deuda, Cobertura | NO EJECUTADO  | PENDIENTE     |
| 3. Inventario SHA-256 Final (E2)   | CSV reproducible         | NO GENERADO   | PENDIENTE     |
| 4. Diff LOC (Nu./Mod./Del.)        | Conteo reproducible      | NO GENERADO   | PENDIENTE     |
| 5. Metricas de Especificacion      | Archivos y lineas spec   | MEDIDO AHORA  | COMPLETADO    |
| 6. Validacion Manual A01-A21       | Inspeccion en navegador  | NO EJECUTADA  | PENDIENTE     |
+------------------------------------+--------------------------+---------------+---------------+
`

### 4.1. Gap 1: Analisis SonarQube Inicial y Final (PENDIENTE)
- **Evidencia observada en Tessl:** E2_TESSL_SONARQUBE_INICIAL.md y E2_TESSL_SONARQUBE_FINAL.json.
- **Estado en Spec Kit:** No se configuro ni ejecuto SonarScanner durante las sesiones de Gemini CLI. No existe archivo de propiedades ni reporte JSON/MD en el espacio de trabajo.
- **Impacto:** Las metricas de Calidad Estatica (deuda tecnica, issues por severidad, bugs, vulnerabilidades, code smells) permanecen **N/D** hasta que un investigador ejecute el escaner sobre la linea base E1 y la implementacion E2.

### 4.2. Gap 2: Inventario SHA-256 Final y Diff LOC (PENDIENTE)
- **Evidencia observada en preparacion:**  
  - preparacion/E1_SOURCE_MANIFEST_SHA256.csv: 59 archivos durables.  
  - preparacion/E2_READY_FOR_GEMINI_SHA256.csv: 59 archivos identicos antes de iniciar Gemini CLI.
- **Estado en Spec Kit:** No se ha corrido el script post-implementacion para generar:
  - E2_SPECKIT_FINAL_MANIFEST_SHA256.csv
  - E2_SPECKIT_DIFF_BASELINE_FINAL.csv
  - Conteo estricto de Diff LOC (lineas anadidas, modificadas y eliminadas sobre codigo fuente).
- **Impacto:** El conteo de cambios se conoce a nivel de archivos modificados/creados, pero la metrica formal de lineas modificadas frente a la linea base E1 permanece **N/D**.

### 4.3. Gap 3: Metricas de Archivos y Lineas de Especificacion (COMPLETADO EN ESTA AUDITORIA)
Se ejecuto la medicion estricta sobre todos los artefactos de especificacion bajo specs/002-shift-bank-stage2/:

| Artefacto de Especificacion | Rol en Spec Kit | Lineas Fisicas |
|---|---|---:|
| specs/002-shift-bank-stage2/spec.md | Especificacion de Requisitos y Criterios | 290 |
| specs/002-shift-bank-stage2/plan.md | Plan de Implementacion Tecnica | 250 |
| specs/002-shift-bank-stage2/data-model.md | Modelo de Entidades y Migracion SQLite | 219 |
| specs/002-shift-bank-stage2/contracts/api.md | Contratos de API REST y Errores | 433 |
| specs/002-shift-bank-stage2/research.md | Decisiones Tecnicas y Remediaciones | 121 |
| specs/002-shift-bank-stage2/quickstart.md | Guia de Verificacion y Escenarios A01-A21 | 100 |
| specs/002-shift-bank-stage2/tasks.md | Lista de Tareas y Desglose de Fases | 191 |
| specs/002-shift-bank-stage2/checklists/requirements.md | Checklist de Calidad de Requisitos | 36 |
| **TOTAL ESPECIFICACION STAGE 2** | **8 archivos formales** | **1.640 lineas** |

### 4.4. Gap 4: Validacion Manual de Escenarios A01-A21 (PENDIENTE)
- **Regla Metodologica Mandatoria:** *Las pruebas automatizadas no constituyen validacion manual.*
- **Estado en Spec Kit:**
  - Los escenarios A01 a A20 fueron verificados mediante suites automatizadas (pytest 47/47 y itest 12/12) dentro del arnes de pruebas.
  - El escenario **A21 (Inspeccion Visual en Navegador)** exige explicitamente:
    - Arrancar uvicorn backend.src.main:app y 
pm run dev.
    - Abrir http://localhost:5173 en navegador web.
    - Comprobar visualmente las tarjetas Checking y Savings y el formato COP (es-CO).
    - Validar en tiempo real la respuesta visual del campo de enrutamiento (borde rojo/boton deshabilitado en <9 digitos, verde en 9 digitos).
    - Verificar la separacion visual entre Limite Configurado, Consumo Acumulado y Disponibilidad Restante.
    - Interactuar con el modal de MFA compartido ante transferencias sensibles (>= 1.000.000 COP) y creaciones de pago recurrente.
  - Esta inspeccion interactiva humana **no se ha ejecutado ni documentado con capturas/bitacora**. Clasificarla como 'aprobada' sin ejecucion humana presencial viola el protocolo experimental.

---
## 5. Tabla Comparativa de Telemetria: Tessl vs. Spec Kit (Etapa 2)

A titulo informativo para la tesis comparativa, se contrastan las telemetrias deduplicadas de ambas herramientas sobre el mismo problema funcional:

| Metrica Telemetrica | Tessl E2 (2 sesiones registradas) | Spec Kit E2 (2 sesiones registradas) | Observacion Metodologica |
|---|---:|---:|---|
| **Modelo Principal Observado** | gemini-3.8-flash | gemini-3.8-flash | Ambas usaron 3.8 Flash (desviacion respecto a 3.5 Flash) |
| **Prompts Humanos (Msgs)** | N/D (no reportado en Tessl) | **25 mensajes** | Spec Kit registra con precision cada prompt de usuario |
| **Solicitudes API (Turnos)** | 196 | **521** | Spec Kit requirio +165,8 % turnos (workflow SDD multi-fase) |
| **Tokens Entrada Totales** | 22.273.164 | **123.950.969** | Spec Kit acumulo mayor contexto por analisis y tareas |
| **Tokens Cache Leidos** | 20.447.304 | **108.868.091** | Cache Spec Kit: 87,83 % vs Tessl: 91,80 % |
| **Tokens Salida Generados** | 92.615 | **335.430** | Spec Kit genero especificaciones extensas (1.640 lineas) |
| **Tokens Pensamiento** | 41.809 (parcial S1) | **225.992** | Registrados explicitamente en Spec Kit |
| **Llamadas a Herramientas Unicas** | 237 | **485** | Spec Kit: 199 lecturas, 139 comandos, 66 reemplazos, etc. |
| **Tasa de Exito de Herramientas**| 98,73 % (234/237) | **97,94 % (475/485)** | Consistente (>97 % de exito en ambas) |
| **Wall Clock Time** | 1 h 59 min 19 s (7.159 s)| **4 h 55 min 34 s (17.734 s)** | Spec Kit dedico mayor tiempo al ciclo de especificacion |
| **Pruebas Automatizadas Finales** | 78 (43 back, 35 front) | **59 (47 back, 12 front)** | Ambas alcanzaron 100 % de paso en suites de regresion |
| **Costo Monetario** | N/D | **N/A** | Ninguna cuenta con factura formal desglosada por sesion |

---

## 6. Plan de Accion Priorizado para el Investigador

Para completar el expediente de evidencia de Spec Kit antes de cerrar la Etapa 2:

1. **Prioridad 1 - Ejecucion de SonarQube (Linea Base y Final):**  
   - Ejecutar SonarScanner sobre Shift-Bank/Etapa 2/Spec Kit apuntando al servidor SonarQube local del estudio.
   - Extraer metricas JSON y generar E2_SPECKIT_SONARQUBE_FINAL.json.
2. **Prioridad 2 - Generacion de Manifiesto SHA-256 Final y Diff LOC:**  
   - Ejecutar script de hash sobre los archivos de Shift-Bank/Etapa 2/Spec Kit excluyendo dependencias y caches.
   - Generar E2_SPECKIT_FINAL_MANIFEST_SHA256.csv y compararlo contra preparacion/E2_READY_FOR_GEMINI_SHA256.csv.
   - Calcular Diff LOC neto (anadidas, modificadas, borradas) con git diff --stat.
3. **Prioridad 3 - Validacion Manual Interactiva en Navegador (A21):**  
   - Levantar servidor backend y frontend en modo interactivo.
   - Completar el checklist visual A21 y documentar evidencia en bitacora de pruebas humanas.
4. **Prioridad 4 - Consolidacion de Telemetria Deduplicada:**  
   - Actualizar las tablas de tesis utilizando las **485 llamadas a herramientas** y **123.95M tokens de entrada**, descartando formalmente la cifra inflada de 5.213 herramientas como artefacto de logging plano.

---
**Fin del Registro de Auditoria de Medicion.**
