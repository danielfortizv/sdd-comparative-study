# 00 — Contexto, fuentes, límites y sistema heredado

**Experimento:** Tesis comparativa de herramientas de *Spec-Driven Development* (SDD).  
**Caso:** Shift Bank — aplicación bancaria simulada, evolución brownfield.  
**Herramienta evaluada:** GitHub Spec Kit (flujo nativo) con Gemini CLI.  
**Agente de preparación externa:** Codex; **su trabajo de Hito 0 no representa el rendimiento medido de Spec Kit/Gemini**.  
**Etapa:** E3, Opción A, cuatro capacidades de la semilla.

## 1. Rutas de Windows obligatorias

```text
REPO_ROOT      = C:\Users\danie\Documents2\sdd-comparative-study
SOURCE_E2      = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit
SOURCE_E2_LOGS = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\_experiment_logs\Spec Kit
DEST_E3        = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Spec Kit
DEST_E3_LOGS   = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Spec Kit
SEED_E3        = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\SEED-3.md
CODEX_INPUT    = C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_codex_prep
```

Estas rutas son **expectativas del traspaso**, no hechos comprobados en la máquina. Codex debe resolver rutas canónicas, verificar existencia, detectar colisiones y anotar cualquier desviación. Si la ruta real cambió, debe documentarla en lugar de crear una copia paralela accidental.

## 2. Jerarquía de fuentes y alcance de E3

1. **Semilla común inalterable** `SEED-3.md`. Su SHA-256 en el paquete es `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`.
2. **Código y especificaciones de E2 de Spec Kit**, tal como quedaron al cierre de esa herramienta. Esta es la única base heredada que se puede copiar.
3. **Contrato E2 heredado**, situado en `Shift-Bank\Etapa 2\E2_COMMON_FUNCTIONAL_CONTRACT.md`, y el comportamiento E2 efectivamente implementado. Si difieren, registrar la divergencia, no reescribir la historia.
4. **Evidencia primaria de E2** en `SOURCE_E2_LOGS`, incluida `01_INFORME_CIERRE_E2_SPECKIT.md`, manifiesto SHA-256, diff, suites de pruebas y SonarQube.
5. **Protocolo investigador de E3** `SHIFT_BANK_E3_PROTOCOLO_REPLICABLE_OTRAS_HERRAMIENTAS.docx`, usado para organizar hitos, medición y controles. **No entregar a Gemini la solución ni los incidentes específicos de Tessl como plantilla**.

La fuente académica identifica para Fintech E3 / Opción A: cifrado de datos bancarios sensibles, auditoría inmutable, pruebas de carga y despliegue. La semilla precisa que el servidor es Python/FastAPI y el cliente React/TypeScript y que se preserva un usuario mock ya autenticado. **No se pide registro/login real ni conexión a bancos reales.**

## 3. Sistema que debe heredar E3 (no reinterpretar)

Según el cierre E2 de esta variante:

- Backend Python 3.13 / FastAPI y SQLite; frontend React / TypeScript / Vite.
- Dos cuentas simuladas con semilla: `acc_checking_123` (Checking, COP 5.000.000) y `acc_savings_456` (Savings, COP 15.000.000); historial inicial de dos transferencias.
- Transferencias entre cuentas propias, saldo/historial, MFA simulado para operaciones de **COP 1.000.000 o más**, PIN de prueba `123456`, expiración de 300 segundos.
- Beneficiarios ACH, transferencias ACH `PENDING` / `SETTLED` / `FAILED`, control transaccional y liquidación autónoma.
- Pagos recurrentes internos o ACH: diario (+24 h), semanal (+7 d), mensual (+30 d), pausa, reanudación, cancelación y MFA de creación cuando corresponde.
- Límites iniciales por transferencia COP 5.000.000, límite diario COP 10.000.000, con consumo en UTC.
- Un proceso de scheduler ligado al ciclo de vida de la aplicación; preferencia operativa documentada por **un solo worker** bajo SQLite.

La fuente E2 reportó **52/52 tareas**, **47/47 pruebas backend**, **12/12 pruebas frontend** y build satisfactorio. También reportó **74 archivos durables** (59 en E1; 49 sin cambios, 10 modificados, 15 nuevos) y SonarQube E2 con **3 bugs, 72 code smells, 4.099 NCLOC**. Estas cifras son **referencias a verificar, no resultados nuevos de E3 ni mínimos forzados**. No corregir esos bugs en el Hito 0: son parte de la línea base experimental.

La validación manual E2 fue comunicada globalmente como satisfactoria por el investigador; no deben inventarse capturas ni evidencias individualizadas de todos los casos.

## 4. Qué exige E3, pero NO se diseña todavía

- Protección criptográfica de datos bancarios sensibles durante transporte y almacenamiento, integridad autenticada y protección de claves; aclarar qué se entiende por «end-to-end» cuando el servidor necesita descifrar.
- Bitácora de auditoría append-only verificable y resistente a alteraciones ordinarias, vinculada atómicamente a operaciones bancarias; aclarar modelo de amenazas.
- Prueba de carga reproducible: **30 usuarios concurrentes; subida 5 usuarios/s; 60 s estables después del ramp-up; 60 % lecturas de saldo, 30 % historial y 10 % transferencias internas reales**. Criterios de referencia: p95 lectura <200 ms, p95 transferencia <500 ms, errores inesperados <1 %. No correr Locust en Hito 0.
- Despliegue local mediante contenedores y HTTPS, secretos externos, almacenamiento aislado y scheduler único; aclarar objetivos del despliegue antes de especificar.

**Estos puntos son contexto de futura aclaración/aprobación; NO autorizan a Codex a crear la solución, dependencias, contenedores, criptografía o tablas de auditoría.**

## 5. Invariantes y fronteras

- **Solo escritura autorizada** dentro de `DEST_E3`, `DEST_E3_LOGS` y, si falta, `SEED_E3`. No editar `SOURCE_E2`, `SOURCE_E2_LOGS`, E1, Tessl, OpenSpec, BMAD, Kiro, Tetris, E-commerce, proyectos externos ni la raíz Git global.
- Nunca editar un historial o sobrescribir una medición existente. No ejecutar `git reset`, `git clean`, `git checkout`, `git add`, `git commit`, `robocopy /MIR`, borrado masivo, podas de Docker ni migraciones sobre bases históricas.
- No montar/abrir las bases SQLite históricas para pruebas ni copiar `.db`, `.sqlite*`, `-wal`, `-shm`. No eliminar/checkpointear esos sidecars; **excluirlos al copiar**.
- No copiar `.env`, claves privadas, tokens, certificados privados, credenciales, cachés, `.venv`, `node_modules`, `dist`, logs brutos, archivos de sesiones ni builds.
- No permitir que dependencias o herramientas generen cambios no documentados en el código heredado. Si una herramienta exige mutar fuentes para correr pruebas, registrar impedimento y solicitar aprobación; no «arreglar» silenciosamente.
- Los documentos del presente paquete son instrucciones auxiliares **de Codex**, y se conservan fuera de `DEST_E3`; **no son specs E3**.
