# 03 — Contrato de traspaso desde Codex (Hito 0) hacia Gemini CLI + Spec Kit (Hito 1)

## Propósito

Cuando Codex termine, el investigador debe poder iniciar la primera sesión E3 de Gemini desde un árbol aislado, con heredados E2 byte-idénticos y un informe de preparación verificable. **Gemini será el agente de implementación evaluado, no Codex.**

## Entrega esperada de Codex

- Carpeta `Etapa 3/Spec Kit` lista con código, pruebas, `specs/` históricos y configuración `.specify` de E2, sin modificaciones funcionales.
- Carpeta `Etapa 3/_experiment_logs/Spec Kit/` organizada según el protocolo.
- Semilla `Etapa 3/SEED-3.md` idéntica a la entregada (SHA correcto).
- Manifest de E2 y E3 con hashes reales, comparación 1:1, exclusiones documentadas, y cero bytes alterados entre fuente y copia.
- Reporte de versiones, `git status`, rama/commit y trazabilidad a E2.
- Evidencia previa de pytest, frontend tests y build, con exit codes, stdout y stderr; cualquier excepción marcada como tal.
- Declaración precisa de aislamiento: no se tocó E1/E2, otras herramientas, DB/volúmenes ni secretos. Si no se puede demostrar con hash antes/después, no afirmar inmutabilidad absoluta.
- `E3_SPECKIT_HITO0_READINESS.md` con `GO PARA GEMINI HITO 1` o `NO-GO`, causas y acciones pendientes.

## Lo que **NO** debe hacer Codex ni introducir como documentación E3

- No abrir una sesión Gemini ni ejecutar `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze` o `/speckit.implement`.
- No crear o modificar contratos de cifrado, auditoría, Locust o despliegue.
- No escribir `specs/003-...`, `constitution` nueva ni AGENTS/config de proyecto que determine la solución sin aprobación.
- No decidir la definición de E2EE, estrategia de claves, modelo de amenazas, semántica append-only, migración de datos, métricas de carga, perfiles de SLO, host/producto de deployment o esquema Docker. **Solo documentar preguntas abiertas y referencias**.
- No entregar a Gemini la implementación, historial de errores o prompts correctivos de Tessl.
- No ejecutar SonarQube ni fijar Quality Gate; debe hacerse en los hitos establecidos sobre el código E3 producido, guardando los reportes originales por separado.
- No arreglar los 3 bugs existentes reportados en E2 ni alterar la línea base; se mide E3 partiendo del cierre real E2, con sus limitaciones.

## Hitos posteriores — orden y autorizaciones

| Hito | Responsable principal | Actividad | Condición de parada |
|---|---|---|---|
| H0 | Codex | Copia, SHA, entorno, regresión inicial y evidencias | Informe de readiness y aprobación humana |
| H1 | Gemini + Spec Kit | Descubrimiento y aclaraciones una cuestión material por vez | Sin código/specs nuevos; espera de respuesta humana |
| H2 | Gemini + Spec Kit | Especificaciones E3 verificables | Aprobación explícita previa a código |
| H3 | Gemini + Spec Kit | Cifrado y migración | Regressions y revisión |
| H4 | Gemini + Spec Kit | Auditoría y atomicidad | Regressions y revisión |
| H5 | Gemini + Spec Kit | Locust 30 users, 5/s, 60s estables, 60/30/10 | Reportes originales y revisión |
| H6 | Gemini + Spec Kit | Docker, HTTPS, persistencia y smoke tests | Evidencia operacional |
| H7 | Gemini + Spec Kit | SonarQube baseline con cobertura | Reportes guardados antes de remediar |
| H8 | Gemini + Spec Kit | Revisión humana, corrección acotada y rescaneo | No loops ilimitados de optimización |
| H9 | Investigador | Síntesis comparativa D1–D5 y cierre | Contrastar todo con fuentes primarias |

## Información que se necesita antes del primer prompt Gemini

Codex debe registrar **preguntas sin contestarlas** sobre:

1. Qué datos bancarios serán considerados sensibles y qué seguridad ofrece el «end-to-end encryption» cuando el backend descifra para operar.
2. Contra qué actores y alteraciones debe proteger la auditoría inmutable; qué pasa si falla la escritura de auditoría.
3. Cuáles son las condiciones de entorno y el control justo del benchmark de 30 usuarios; definir datos sintéticos y tolerancias.
4. Cuál es el destino exacto y el alcance del despliegue; cómo se protegen secretos, TLS, SQLite y scheduler.

Estos son candidatos a aclaraciones de Hito 1, **no decisiones aprobadas**. Gemini debe usar su proceso nativo y preguntar al investigador antes de modificar especificaciones.

## Nota de independencia sobre la preparación con Codex

Para no contaminar la medición comparativa, los prompts y herramientas ejecutadas por Codex permanecen etiquetados `CODEX_PREPARACION_HITO0`. Cuando Gemini inicie E3 se registrará nuevo `sessionId`, modelo efectivo, mensajes, herramientas, tokens, tiempos y aprobaciones. No sumar Codex con Gemini ni reutilizar capturas E2 como si fueran E3.

## Control previo a compartir resultados

Codex debe decir exactamente: qué se copió, qué se dejó fuera, qué se ejecutó, cuánto se verificó, qué falló, qué archivos generó y si la transición está autorizada. **Una afirmación genérica «todo listo» no basta.** El investigador revisará el reporte y solo después autorizará el primer prompt Gemini E3.
