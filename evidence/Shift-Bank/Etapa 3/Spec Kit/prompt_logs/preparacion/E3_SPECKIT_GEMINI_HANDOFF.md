# Traspaso a Gemini CLI + GitHub Spec Kit — Shift Bank E3

## Estado de entrega

HITO 0 verificado: **GO PARA GEMINI HITO 1**, pendiente de revisión y autorización humana explícita. No se inició Gemini ni se creó ninguna especificación o implementación E3.

## Base heredada y evidencia

- Trabajar únicamente desde `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Spec Kit`.
- La base es el cierre E2 de Spec Kit, con 74 archivos durables. Los manifiestos confirman 74/74 SHA-256 en E2 y E3.
- La semilla común está en `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\SEED-3.md`, SHA-256 `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`.
- Evidencia técnica: [readiness final](./E3_SPECKIT_HITO0_READINESS_FINAL.md), [manifiesto final](./E3_SPECKIT_RESUME_FINAL_SHA256_20261115_190641.csv), [bitácora Codex](./E3_SPECKIT_PREPARACION_CODEX_LOG_RESUME.md), [versiones](./E3_SPECKIT_ENVIRONMENT_RESUME.txt).
- La copia conserva solamente las especificaciones históricas `001-shift-bank-stage1` y `002-shift-bank-stage2`; no existe `003`.

## Regresión de referencia

- Backend: 47/47 aprobadas; `TEST_DB_PATH` aislada bajo `Etapa 3\Spec Kit\backend\tests`; sin acceso a bases E2.
- Frontend: 12/12 aprobadas con `npm.cmd run test -- --run`.
- Build: `npm.cmd run build` aprobado.
- La instalación y pruebas observaron Node 20.17.0; `@testing-library/jest-dom@7.0.1` declara Node >=22, aunque las pruebas/build pasaron. Tener presente esta advertencia y no cambiar dependencias sin aprobación.

## Límites

Tras autorización del investigador, seguir el flujo nativo de Spec Kit para descubrimiento y aclaraciones. No implementar antes de aprobación de requisitos. No copiar ni consultar implementaciones de Tessl como solución. No alterar los artefactos E1/E2, DBs históricas, `.specify`, `package-lock.json` o dependencias sin una decisión explícita. No presentar telemetría de Codex como métrica de Gemini.

Temas abiertos que deben resolverse con el investigador, no asumirse ni prescribirse:

1. Datos que se consideran sensibles y límites de “end-to-end encryption” cuando el servidor necesita procesar datos.
2. Actores/alteraciones incluidos en el modelo de amenazas de auditoría y política ante fallo de escritura.
3. Condiciones reproducibles del benchmark, datos sintéticos y tolerancias.
4. Destino y alcance del despliegue local, TLS, secretos, persistencia SQLite y scheduler.

No ejecutar Gemini, `/speckit.*`, SonarQube, Locust ni despliegue hasta la aprobación correspondiente. El presente handoff no es una especificación E3.
