# Shift Bank — Etapa 3 — OpenSpec
## Anexo D1: Telemetría recuperada de Codex CLI (V2)

**Extracción UTC:** 2026-11-17T21:23:52.699298+00:00  
**Alcance:** únicamente sesiones con `session_meta.cwd` correspondiente a `Shift-Bank/Etapa 3/OpenSpec`.
**Fuente primaria:** archivos locales `rollout-*.jsonl` de Codex, no adjuntados por privacidad.  
**Revisión:** anexo posterior a los informes R02; no modifica ni sustituye datos históricos.

### Valores recuperados

| Métrica oficial | Valor | Interpretación |
|---|---:|---|
| Tok In | 70,781,091 | Entrada acumulada, incluye tokens de caché |
| Tok Cache | 68,747,520 | Subconjunto de Tok In |
| Tok Out | 468,712 | Salida acumulada, incluye razonamiento reportado |
| Tok In sin caché (derivado) | 2,033,571 | Tok In − Tok Cache |
| Tokens de razonamiento (subconjunto de salida) | 242,550 | No sumar nuevamente a Tok Out |
| Cred | N/A | No aplica a OpenSpec |
| Costo ($) | N/D | No recuperado ni estimado sin tarifas justificadas |
| Msgs | 95 | 13 usuario + 82 asistente, eventos `response_item.message` |
| Tool Calls | 538 | Llamadas observadas en JSONL |
| Tiempo estricto de procesamiento del modelo | N/D | No acreditado con temporización exclusiva |
| Duraciones de tareas registradas (s) | 15052.67 | Suma de 11 duraciones de tarea; no model-only |
| Tiempo de pared (s) | 92368.492 | Incluye pausas y esperas humanas |

### Cobertura y atribución

Se incluyó **1 sesión**, ID `01a1e5c7-c7a3-7f00-84cc-44a019f714d1`, desde `2026-11-16T19:14:08.175Z` hasta `2026-11-17T20:53:36.667Z`. Fuente: `rollout-2026-11-16T14-13-57-01a1e5c7-c7a3-7f00-84cc-44a019f714d1.jsonl`, SHA-256 `607a7749e75354bb2509e9c56992cce37f5d8823cbec7a39baae986a105697e8`. Se observaron 555 eventos de tokens y 0 reinicios del contador acumulado. Modelo observado: gpt-6-luna.

Hay **8 sesiones candidatas fuera del cwd exacto**, de las que **2** iniciaron desde otras carpetas de Etapa 3 y **6** desde otras carpetas de Shift Bank o superiores. Sus consumos **no están incluidos**; atribuirlos exige revisar su relación con OpenSpec sin arrastrar actividades de otras herramientas.

### Limitaciones y decisión de cierre

- Esta tabla representa **telemetría observada y atribuida**, no el total exhaustivo de todas las interacciones de E3.
- `Msgs` cuenta registros de mensajes, no necesariamente solicitudes de modelo o decisiones humanas únicas.
- `Tiempo (s)` exclusivo de modelo y `Costo ($)` quedan N/D; no se reemplazan por tiempo de pared ni por tiempo de tareas.
- No sumar Tok Cache a Tok In, ni tokens de razonamiento a Tok Out, porque ya están incluidos.
- Mantener las ocho sesiones no atribuidas como candidatas, sin mezclarlas con el experimento E4.
- Congelar este anexo como evidencia de D1 V2. Se puede iniciar E4 en un árbol independiente, manteniendo esta limitación declarada.

### Fuentes y comprobación

| Archivo entregado | SHA-256 |
|---|---|
| `E3_OPENSPEC_CODEX_D1_METADATOS_V2_20261117T212352Z.json` | `4906a1084d3eb58542842af8570a1ddc2aa3fd5866a6e2e708580eb350b84823` |
| `E3_OPENSPEC_CODEX_SESIONES_V2_20261117T212352Z.csv` | `290735e450cc291e5d7b30edf6f616ed594ad9d1d464e77b8c5d350ed291d245` |
| `E3_OPENSPEC_CODEX_OTRAS_SESIONES_V2_20261117T212352Z.csv` | `6d25b6ae99dc7189801c5c27e2155f586d78fe7cd0693b20cc343b706ebb2368` |
