# Índice de evidencia experimental — Etapa 3 (Kiro)

Este directorio contiene la evidencia cruda del experimento de la Etapa 3 para la
herramienta **Kiro**. Su propósito es permitir la reproducibilidad y la auditoría
de cada hito sin depender de resúmenes posteriores.

## Convención de evidencia

1. **Nombres con timestamp.** Cada artefacto de evidencia se nombra con el prefijo
   `YYYYMMDD-HHMMSS_` seguido de un slug descriptivo
   (p. ej. `20261116-153800_M0-baseline-regresion-heredada.md`). El timestamp refleja
   el momento de captura.
2. **Nunca sobrescribir.** Los artefactos previos no se editan ni se eliminan. Si hay
   que volver a capturar algo, se crea un **nuevo archivo con un timestamp nuevo**.
3. **Stdout/JSON/CSV crudos.** Se preserva la salida cruda de los comandos
   (stdout/stderr, JSON y CSV) sin reformatear ni recortar, dentro de bloques de código
   o como archivos adjuntos en la subcarpeta correspondiente.
4. **Trazabilidad.** Cada sesión registra el entorno, el comando exacto ejecutado y los
   conteos/resultados observados.

## Estructura de subcarpetas

| Carpeta        | Contenido                                                            |
|----------------|---------------------------------------------------------------------|
| `sesiones/`    | Bitácoras por sesión/hito (una por captura, con timestamp).         |
| `pruebas/`     | Evidencia de ejecución de pruebas (backend/frontend): stdout, conteos. |
| `sonarqube/`   | Reportes y salidas de análisis estático SonarQube (PRE/POST).       |
| `carga/`       | Evidencia de pruebas de carga/rendimiento (p. ej. Locust): CSV/JSON. |
| `despliegue/`  | Evidencia de despliegue/arranque de la aplicación.                  |

> Otras carpetas presentes de preparación previa (`decisiones/`, `diffs/`, `locust/`,
> `preparacion/`) se conservan tal cual; no forman parte de las cinco subcarpetas
> requeridas por esta tarea pero no deben eliminarse.

## Documentos de referencia

- `ENTORNO.md` — versiones de OS, Python, Node y npm usadas como contexto.
- `bitacora.md` — bitácora narrativa acumulada del experimento.
