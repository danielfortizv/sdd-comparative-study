# E2 · Kiro · Evidencia de análisis estático (carpeta `sonarqube/`)

- **Tarea:** 46 — Recolectar evidencia estandarizada (código, pruebas, análisis estático)
- **Fase:** G — Verificación final y evidencia experimental
- **Contrato:** §7
- **Fecha de recolección:** 2026-11-16
- **Naturaleza:** recolección de evidencia. **No** crea ni modifica código de aplicación,
  pruebas, requisitos, diseño ni registros históricos. **No fabrica resultados ni métricas.**

---

## 1. Estado real del análisis estático en esta implementación (E2 · Kiro)

Se inspeccionó el proyecto `Etapa 2/Kiro` en busca de configuración o salida de análisis estático
estandarizado. El estado **verdadero** es:

| Herramienta / artefacto | Presente en E2·Kiro | Evidencia |
|---|---|---|
| `sonar-project.properties` | **No** | Búsqueda en el proyecto: sin coincidencias (solo existe en `Etapa 3/Tessl` y `Etapa 4/Tessl`). |
| Salida de escaneo SonarQube para E2·Kiro | **No** | No se ejecutó ningún escaneo SonarQube sobre esta implementación de Etapa 2. |
| Linter Python (ruff/flake8/pylint/mypy/bandit/black/pyright) | **No instalado** | `pip list` del `.venv` del backend no reporta ninguno. No hay configuración (`ruff.toml`, `.flake8`, `setup.cfg`, `mypy.ini`, `pyproject.toml`). |
| ESLint (frontend) | **No** | No existe configuración `.eslintrc*` ni dependencia ESLint en `frontend/package.json`. |
| **TypeScript type-check (`tsc --noEmit`)** | **Sí** (único análisis estático realmente ejecutable y ejecutado) | Parte de `npm run build` (`tsc && vite build`); ejecutado fresco en esta tarea. |

> **No se fabrica un informe SonarQube.** La Etapa 2 · Kiro no ejecutó un escaneo SonarQube y no
> existe configuración para ello en el proyecto. Fabricar métricas de SonarQube violaría el
> contrato §7 y la restricción explícita de la tarea ("sin modificar ni fabricar registros
> históricos"). Esta carpeta documenta lo que **sí** está disponible de forma verificable.

### Referencia histórica (NO perteneciente a E2·Kiro)

Existe un escaneo SonarQube **de la Etapa 1 · Kiro** en
`Etapa 1/_experiment_logs/Kiro/sonarqube_scan_001.txt` (proyecto `shift-bank-stage1-kiro`,
`ANALYSIS SUCCESSFUL`, 41 archivos indexados, 5 lenguajes). Se cita únicamente como antecedente;
corresponde a la Etapa 1 y **no se reutiliza ni se altera**.

---

## 2. Análisis estático realmente ejecutado — TypeScript (`tsc --noEmit`)

Comando (desde `Etapa 2/Kiro/frontend`):

```
npx tsc --noEmit
```

| Métrica | Valor real |
|---|---|
| Versión de TypeScript | 5.9.3 |
| Node.js | v24.19.0 |
| Resultado | **Sin errores de tipo** |
| Código de salida | **0** |

El type-check estricto del frontend pasa sin diagnósticos. Es el único análisis estático
estandarizado disponible y ejecutable en esta implementación, y se ejecutó fresco en esta tarea.

---

## 3. Dónde está el resto de la evidencia estandarizada

- **Métricas de código y de pruebas:** `../pruebas/E2_KIRO_EVIDENCIA_ESTANDARIZADA.md`
  (recuento de archivos/líneas por módulo, inventario de pruebas, resultado de la suite).
- **Resultados PASS/FAIL consolidados:** `../pruebas/E2_KIRO_RESULTADOS_PRUEBAS.md` (Tarea 45).
- **Sesión de esta recolección:** `../sesiones/E2_KIRO_SESION_31_TAREA_46.md`.

---

## 4. Preservación / no manipulación

- DB histórica `Etapa 1/Kiro/backend/shift_bank.db`: SHA-256
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8`, 36.864 bytes — recalculado
  en esta tarea e **idéntico** al registrado en todas las sesiones previas. No tocada.
- Esta tarea solo ejecutó comandos de **lectura/análisis** (`pytest`, `tsc`, conteos de archivos,
  `Get-FileHash`) y escribió documentos de evidencia. No se editó `app/`, pruebas, frontend,
  la Etapa 1 ni ningún registro previo.
