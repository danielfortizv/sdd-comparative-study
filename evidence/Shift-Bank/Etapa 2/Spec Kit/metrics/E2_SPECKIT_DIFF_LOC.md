# Shift Bank Stage 2 - Spec Kit: Registro de Evolucion de Archivos, Trazabilidad SHA-256 y Diff LOC

**Documento:** E2_SPECKIT_DIFF_LOC.md
**Destino:** Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_DIFF_LOC.md
**Referencia Metodologica:** SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md (Seccion 9) y Metodologia de Inventario Tessl
**Fecha de Medicion:** 2026-11-14
**Linea Base E1 Preservada:** Shift-Bank/Etapa 1/Spec Kit (59 archivos durables, SHA-256 identicos a preparacion)
**Implementacion Final E2:** Shift-Bank/Etapa 2/Spec Kit (74 archivos durables)
**Archivos CSV Generados:**
- E2_SPECKIT_FINAL_MANIFEST_SHA256.csv (Inventario completo de 74 archivos con hash SHA-256 y tamano en bytes)
- E2_SPECKIT_DIFF_BASELINE_FINAL.csv (Matriz comparativa archivo por archivo con categorias, estados, bytes, hashes y Diff LOC)
- E2_SPECKIT_DIFF_RESUMEN.csv (Resumen cuantitativo por categoria y estado)
- E2_SPECKIT_ESPECIFICACIONES_FINAL.csv (Desglose de los 8 artefactos de especificacion Stage 2 con lineas y bytes)

---

## 1. Metodologia de Inventario y Reglas de Exclusion

Siguiendo exactamente la politica de exclusion establecida en la preparacion (preparacion/COPY_EXCLUSIONS_AND_SKIPPED_LINKS.md) y el estandar del estudio comparativo:
- **Directorios excluidos:** .git, 
ode_modules, __pycache__, .pytest_cache, .ruff_cache, dist, .scannerwork y _experiment_logs.
- **Archivos mutables/temporales excluidos:** Base de datos SQLite mutable (ackend/shift_bank.db), archivos WAL/SHM y archivos de cobertura .coverage.
- **Calculo de Hash:** SHA-256 sobre bytes en crudo del archivo.
- **Rutas:** Separadores POSIX normalizados relativos a la raiz del espacio de trabajo.

---

## 2. Resumen Cuantitativo de Evolucion de Archivos

De los **59 archivos durables** heredados de la linea base E1, la implementacion final de Stage 2 consta de **74 archivos**:
- **Archivos Sin cambios:** **49**
- **Archivos Modificados:** **10**
- **Archivos Nuevos:** **15**
- **Archivos Eliminados:** **0**

### Desglose por Categoria y Estado:

| Categoria | Estado | Cantidad de Archivos | Archivos Comprendidos |
|---|---|---:|---|
| **Codigo backend** | Modificado | 4 | ackend/src/api.py, ackend/src/database.py, ackend/src/main.py, ackend/src/models.py |
| **Codigo backend** | Nuevo | 2 | ackend/src/scheduler.py, ackend/src/services.py |
| **Codigo frontend** | Modificado | 4 | rontend/src/App.css, rontend/src/App.tsx, rontend/src/services.ts, rontend/src/types.ts |
| **Codigo frontend** | Sin cambios | 1 | rontend/src/main.tsx |
| **Pruebas backend** | Nuevo | 5 | ackend/tests/conftest.py, ackend/tests/test_ach.py, ackend/tests/test_limits.py, ackend/tests/test_recurring.py, ackend/tests/test_stage2_regression.py |
| **Pruebas backend** | Sin cambios | 1 | ackend/tests/test_api.py |
| **Pruebas frontend** | Modificado | 1 | rontend/src/App.test.tsx |
| **Pruebas frontend** | Sin cambios | 1 | rontend/src/setupTests.ts |
| **Especificacion** | Nuevo | 8 | Todos los 8 artefactos bajo specs/002-shift-bank-stage2/ |
| **Especificacion** | Sin cambios | 8 | Todos los 8 artefactos heredados bajo specs/001-shift-bank-stage1/ |
| **Configuracion u otros** | Modificado | 1 | .specify/feature.json (metadata de feature activa de Spec Kit) |
| **Configuracion u otros** | Sin cambios | 38 | Templates, scripts powershell, workflows, .gitignore, package.json, etc. |
| **TOTAL** | | **74** | **49 sin cambios, 10 modificados, 15 nuevos, 0 eliminados** |

---
## 3. Metrica de Diff LOC (Lineas Anadidas, Modificadas y Eliminadas)

El computo de Diff LOC se ejecuto mediante algoritmo de diff unificado (difflib.unified_diff) sobre el contenido UTF-8 de cada archivo entre la linea base E1 y la implementacion final E2:

- **Lineas Anadidas (+):** **7.298**
- **Lineas Eliminadas (-):** **273**
- **Cambio Neto (Net LOC):** **+7.025**

### Desglose de Diff LOC por Grupo Funcional:

| Grupo Funcional | Archivos Modificados / Nuevos | Lineas Anadidas (+) | Lineas Eliminadas (-) | Cambio Neto |
|---|---|---:|---:|---:|
| **Especificacion Stage 2** | 8 nuevos | +1.640 | -0 | +1.640 |
| **Codigo de Produccion Backend** | 4 modif., 2 nuevos | +1.935 | -177 | +1.758 |
| **Pruebas Backend** | 5 nuevos | +1.421 | -0 | +1.421 |
| **Codigo de Produccion Frontend** | 4 modif. | +1.875 | -91 | +1.784 |
| **Pruebas Frontend** | 1 modif. | +426 | -4 | +422 |
| **Configuracion / Metadata** | 1 modif. | +1 | -1 | 0 |
| **TOTALES CONSOLIDADOS** | **25 archivos con diff** | **+7.298** | **-273** | **+7.025** |

### Detalle Archivo por Archivo de Cambios de Lineas:
1. .specify/feature.json: +1 / -1 (E1: 3 lineas -> E2: 3 lineas)
2. ackend/src/api.py: +367 / -136 (E1: 335 lineas -> E2: 566 lineas)
3. ackend/src/database.py: +220 / -24 (E1: 70 lineas -> E2: 266 lineas)
4. ackend/src/main.py: +66 / -3 (E1: 21 lineas -> E2: 84 lineas)
5. ackend/src/models.py: +218 / -14 (E1: 60 lineas -> E2: 264 lineas)
6. ackend/src/scheduler.py: +118 / -0 (Nuevo, E2: 118 lineas)
7. ackend/src/services.py: +946 / -0 (Nuevo, E2: 946 lineas)
8. ackend/tests/conftest.py: +56 / -0 (Nuevo, E2: 56 lineas)
9. ackend/tests/test_ach.py: +400 / -0 (Nuevo, E2: 400 lineas)
10. ackend/tests/test_limits.py: +266 / -0 (Nuevo, E2: 266 lineas)
11. ackend/tests/test_recurring.py: +379 / -0 (Nuevo, E2: 379 lineas)
12. ackend/tests/test_stage2_regression.py: +320 / -0 (Nuevo, E2: 320 lineas)
13. rontend/src/App.css: +301 / -0 (E1: 338 lineas -> E2: 639 lineas)
14. rontend/src/App.test.tsx: +426 / -4 (E1: 469 lineas -> E2: 891 lineas)
15. rontend/src/App.tsx: +1.287 / -87 (E1: 529 lineas -> E2: 1.729 lineas)
16. rontend/src/services.ts: +199 / -4 (E1: 89 lineas -> E2: 284 lineas)
17. rontend/src/types.ts: +88 / -0 (E1: 34 lineas -> E2: 122 lineas)
18. specs/002-shift-bank-stage2/checklists/requirements.md: +36 / -0 (Nuevo, E2: 36 lineas)
19. specs/002-shift-bank-stage2/contracts/api.md: +433 / -0 (Nuevo, E2: 433 lineas)
20. specs/002-shift-bank-stage2/data-model.md: +219 / -0 (Nuevo, E2: 219 lineas)
21. specs/002-shift-bank-stage2/plan.md: +250 / -0 (Nuevo, E2: 250 lineas)
22. specs/002-shift-bank-stage2/quickstart.md: +100 / -0 (Nuevo, E2: 100 lineas)
23. specs/002-shift-bank-stage2/research.md: +121 / -0 (Nuevo, E2: 121 lineas)
24. specs/002-shift-bank-stage2/spec.md: +290 / -0 (Nuevo, E2: 290 lineas)
25. specs/002-shift-bank-stage2/tasks.md: +191 / -0 (Nuevo, E2: 191 lineas)

---
## 4. Estado de SonarQube y SonarScanner: Reporte de Bloqueador Real

Se realizo la verificacion tecnica en el entorno local para determinar si el analisis estatico automatizado podia ejecutarse de inmediato:

1. **Servidor SonarQube:**
   - Estado: **UP** (Activo y accesible en http://localhost:9000).
   - Contenedor Docker: sonarqube (d7c7e82ae845), imagen sonarqube:latest / sdd-sonarqube:frozen.
   - Version del Servidor: 26.9.0.129388 (Coincide exactamente con la version utilizada en Tessl).
   - Verificacion de API: GET http://localhost:9000/api/system/status retorna status: UP.
2. **SonarScanner CLI:**
   - Estado: **DISPONIBLE en Docker**.
   - Imagen Docker: sdd-sonar-scanner:frozen / sonarsource/sonar-scanner-cli:latest.
   - Version del Scanner: SonarScanner CLI 8.1.0.6389 (Coincide exactamente con la version utilizada en Tessl).
3. **Bloqueador Exacto Observado:**
   - Al ejecutar sonar-scanner contra http://host.docker.internal:9000, la inicializacion falla con:
     `	ext
     ERROR Failed to query server version: GET http://host.docker.internal:9000/api/v2/analysis/version failed with HTTP 401 Unauthorized.
     Please check the property sonar.token or the environment variable SONAR_TOKEN.
     `
   - **Causa Raiz:** La instancia local de SonarQube tiene deshabilitado el analisis anonimo y exige autenticacion obligatoria mediante token (SONAR_TOKEN) o credenciales de usuario. Las credenciales por defecto (dmin:admin) fueron cambiadas en la instalacion del estudio, y no existe ningun token configurado en las variables de entorno de esta sesion.
   - **Accion requerida para el investigador:** Suministrar una variable de entorno SONAR_TOKEN valida o ejecutar el escaner con el token local del proyecto para generar E2_SPECKIT_SONARQUBE_INICIAL.json y E2_SPECKIT_SONARQUBE_FINAL.json.
   - **Integridad Experimental:** En estricto cumplimiento de la regla 'Never invent missing baseline measurements or classify automated tests as manual verification', **no se fabricaron metricas de SonarQube** y se documenta formalmente el bloqueador de autenticacion.

---

## 5. Resumen de Gaps Experimentales Remanentes

1. **SonarQube E1 y E2:** Pendiente de ejecucion presencial por el investigador mediante SONAR_TOKEN.
2. **Validacion Manual A01-A21:** Las pruebas unitarias y de integracion automatizadas pasaron al 100% (47 back, 12 front), pero la inspeccion visual en navegador web interactivo descrita en **A21** no ha sido registrada con capturas de pantalla ni bitacora manual humana.

---
**Fin del Registro de Evolucion de Archivos y Diff LOC.**
